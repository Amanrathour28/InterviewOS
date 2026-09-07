/**
 * Candidate session management — Phase 17.
 *
 * Uses sessionStorage (NOT localStorage) so the session disappears when the
 * browser tab/window closes.  The raw token is never placed in a URL parameter.
 */

const SESSION_KEY = 'interviewos_candidate_session';

export interface CandidateSession {
  candidateSessionToken: string;
  interviewId: string;
  candidateName: string;
  /** The opaque join token from the URL — stored so we can poll status */
  joinToken: string;
  expiresAt: number; // epoch ms
}

export type CandidateSessionInspection =
  | { status: 'VALID'; session: CandidateSession }
  | { status: 'MISSING'; session: null }
  | { status: 'EXPIRED'; session: null }
  | { status: 'TOKEN_MISMATCH'; session: null };

export function setCandidateSession(session: CandidateSession): void {
  if (typeof window === 'undefined') return;
  const data = JSON.stringify(session);
  try {
    sessionStorage.setItem(SESSION_KEY, data);
    if (session.joinToken) {
      sessionStorage.setItem(`${SESSION_KEY}_${session.joinToken}`, data);
      localStorage.setItem(`${SESSION_KEY}_${session.joinToken}`, data);
    }
  } catch (err) {
    console.warn('[CandidateSession] Storage error:', err);
  }
}

export function inspectCandidateSession(joinToken: string): CandidateSessionInspection {
  if (typeof window === 'undefined' || !joinToken) {
    return { status: 'MISSING', session: null };
  }

  // 1. Check token-keyed sessionStorage, then default sessionStorage, then localStorage
  let raw: string | null = null;
  try {
    raw =
      sessionStorage.getItem(`${SESSION_KEY}_${joinToken}`) ||
      sessionStorage.getItem(SESSION_KEY);

    if (!raw) {
      raw = localStorage.getItem(`${SESSION_KEY}_${joinToken}`);
      if (raw) {
        // Re-hydrate sessionStorage for subsequent calls
        sessionStorage.setItem(`${SESSION_KEY}_${joinToken}`, raw);
        sessionStorage.setItem(SESSION_KEY, raw);
      }
    }
  } catch (err) {
    console.warn('[CandidateSession] Access error:', err);
  }

  if (!raw) {
    return { status: 'MISSING', session: null };
  }

  try {
    const parsed: CandidateSession = JSON.parse(raw);
    // Validate session matches the correct join token
    if (parsed.joinToken !== joinToken) {
      return { status: 'TOKEN_MISMATCH', session: null };
    }
    // Validate not expired (compare against current time with 30-second buffer)
    if (parsed.expiresAt < Date.now() + 30_000) {
      return { status: 'EXPIRED', session: null };
    }
    return { status: 'VALID', session: parsed };
  } catch {
    return { status: 'MISSING', session: null };
  }
}

export function getCandidateSession(joinToken: string): CandidateSession | null {
  const result = inspectCandidateSession(joinToken);
  return result.status === 'VALID' ? result.session : null;
}

export function clearCandidateSession(joinToken?: string): void {
  if (typeof window === 'undefined') return;
  try {
    sessionStorage.removeItem(SESSION_KEY);
    if (joinToken) {
      sessionStorage.removeItem(`${SESSION_KEY}_${joinToken}`);
      localStorage.removeItem(`${SESSION_KEY}_${joinToken}`);
    }
  } catch {}
}

export function candidateSessionApiHeaders(
  session: CandidateSession
): Record<string, string> {
  return {
    Authorization: `Bearer ${session.candidateSessionToken}`,
    'Content-Type': 'application/json',
  };
}
