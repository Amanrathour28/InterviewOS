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
    const decoded = jwt.verify(token, config.jwtSecretKey, {
      algorithms: ['HS256'],
    }) as any;

    if (!decoded || !decoded.session_id || !decoded.user_id) {
      return next(new Error('INVALID_TOKEN_CLAIMS: Required session_id and user_id claims missing'));
    }

    // 3. Attach user context to socket.data
    const user: SocketUser = {
      userId: String(decoded.user_id),
      userName: String(decoded.user_name || decoded.email || 'User'),
      userEmail: String(decoded.user_email || decoded.email || ''),
      sessionId: String(decoded.session_id),
      interviewId: String(decoded.interview_id || ''),
      workspaceId: String(decoded.workspace_id || ''),
      role: String(decoded.role || 'candidate'),
      isInterviewer: Boolean(decoded.is_interviewer),
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
