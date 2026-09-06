/**
 * Candidate session management — Phase 17.
 *
 * Uses sessionStorage (NOT localStorage) so the session disappears when the
 * browser tab/window closes.  The raw token is never placed in a URL parameter.
 */

const SESSION_KEY = 'interviewos_candidate_session';
const NAME_KEY = 'interviewos_candidate_name';
const TOKEN_KEY_PREFIX = 'join_token_';

export interface CandidateSession {
  candidateSessionToken: string;
  interviewId: string;
  candidateName: string;
  /** The opaque join token from the URL — stored so we can poll status */
  joinToken: string;
  expiresAt: number; // epoch ms
}

export function setCandidateSession(session: CandidateSession): void {
  if (typeof window === 'undefined') return;
  sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function getCandidateSession(joinToken: string): CandidateSession | null {
  if (typeof window === 'undefined') return null;
  const raw = sessionStorage.getItem(SESSION_KEY);
  if (!raw) return null;
  try {
    const parsed: CandidateSession = JSON.parse(raw);
    // Validate session matches the correct join token
    if (parsed.joinToken !== joinToken) return null;
    // Validate not expired (compare against current time with 30-second buffer)
    if (parsed.expiresAt < Date.now() + 30_000) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function clearCandidateSession(): void {
  if (typeof window === 'undefined') return;
  sessionStorage.removeItem(SESSION_KEY);
}

export function candidateSessionApiHeaders(
  session: CandidateSession
): Record<string, string> {
  return {
    Authorization: `Bearer ${session.candidateSessionToken}`,
    'Content-Type': 'application/json',
  };
}
