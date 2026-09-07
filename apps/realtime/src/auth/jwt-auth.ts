import { Socket } from 'socket.io';
import jwt from 'jsonwebtoken';
import { config } from '../config/index.js';
import { SocketUser } from '../types/index.js';

export function authenticateSocket(socket: Socket, next: (err?: Error) => void) {
  try {
    // 1. Extract token from auth payload or authorization header
    const token =
      socket.handshake.auth?.token ||
      (socket.handshake.headers?.authorization?.startsWith('Bearer ')
        ? socket.handshake.headers.authorization.slice(7)
        : null);

    if (!token) {
      return next(new Error('AUTHENTICATION_REQUIRED: Missing access token in handshake auth'));
    }

    // 2. Verify JWT with secret key
    const rawSecret = process.env.JWT_SECRET_KEY || process.env.SECRET_KEY || config.jwtSecretKey;
    const candidateSecrets = Array.from(
      new Set([
        config.jwtSecretKey,
        config.jwtSecretKey.trim(),
        rawSecret,
        rawSecret.trim(),
        `${rawSecret.trim()}\n`,
        `${rawSecret.trim()}\r\n`,
      ])
    ).filter(Boolean);

    let decoded: any = null;
    let verifyError: any = null;
    for (const sec of candidateSecrets) {
      try {
        decoded = jwt.verify(token, sec, { algorithms: ['HS256'] });
        break;
      } catch (err: any) {
        verifyError = err;
      }
    }

    if (!decoded) {
      throw verifyError || new Error('Verification failed');
    }

    if (!decoded || !decoded.session_id || !decoded.user_id) {
      return next(new Error('INVALID_TOKEN_CLAIMS: Required session_id and user_id claims missing'));
    }

    // Role & authorization boundaries
    let isInterviewer = Boolean(decoded.is_interviewer);
    let role = String(decoded.role || (isInterviewer ? 'interviewer' : 'candidate'));

    // Candidate token safety check: candidate tokens MUST NOT claim interviewer status
    if (decoded.type === 'candidate_session') {
      if (decoded.scope !== 'candidate' || isInterviewer || role !== 'candidate') {
        return next(new Error('FORBIDDEN: Candidate token cannot claim interviewer role'));
      }
      isInterviewer = false;
      role = 'candidate';
    }

    // 3. Attach user context to socket.data
    const user: SocketUser = {
      userId: String(decoded.user_id),
      userName: String(decoded.user_name || decoded.email || 'User'),
      userEmail: String(decoded.user_email || decoded.email || ''),
      sessionId: String(decoded.session_id),
      interviewId: String(decoded.interview_id || ''),
      workspaceId: String(decoded.workspace_id || ''),
      role,
      isInterviewer,
    };

    socket.data.user = user;
    next();
  } catch (err: any) {
    if (err.name === 'TokenExpiredError') {
      return next(new Error('TOKEN_EXPIRED: Access token has expired'));
    }
    return next(new Error(`INVALID_TOKEN: ${err.message}`));
  }
}
