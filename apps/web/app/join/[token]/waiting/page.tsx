'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Terminal,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Camera,
  Mic,
  LogOut,
} from 'lucide-react';
import { getCandidateSession, clearCandidateSession } from '@/lib/candidate-session';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' ? '/api/v1' : 'http://127.0.0.1:8000/api/v1');
const POLL_INTERVAL_MS = 5000; // 5-second polling — not aggressive

export default function CandidateWaitingRoomPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const [sessionMissing, setSessionMissing] = useState(false);
  const [candidateName, setCandidateName] = useState('');
  const [statusError, setStatusError] = useState<string | null>(null);
  const [dotCount, setDotCount] = useState(0);

  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Animated dots for "Waiting…"
  useEffect(() => {
    const dotTimer = setInterval(() => {
      setDotCount((c) => (c + 1) % 4);
    }, 600);
    return () => clearInterval(dotTimer);
  }, []);

  // Validate session and start polling
  useEffect(() => {
    if (!token) return;
    const session = getCandidateSession(token);
    if (!session) {
      setSessionMissing(true);
      return;
    }
    setCandidateName(session.candidateName);

    const checkStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/interviews/join/${token}/status`, {
          headers: {
            Authorization: `Bearer ${session.candidateSessionToken}`,
            'Content-Type': 'application/json',
          },
        });

        if (!res.ok) {
          if (res.status === 401 || res.status === 403) {
            // Session expired — redirect to start
            clearCandidateSession(token);
            router.replace(`/join/${token}`);
            return;
          }
          const body = await res.json().catch(() => ({}));
          setStatusError(body.detail || 'Connection issue. Retrying…');
          return;
        }

        setStatusError(null);
        const data = await res.json();

        if (data.interview_started || data.interview_status === 'in_progress') {
          // Interviewer has started — enter the room
          if (pollRef.current) clearInterval(pollRef.current);
          router.push(`/join/${token}/room`);
        } else if (data.interview_status === 'completed' || data.interview_status === 'cancelled') {
          if (pollRef.current) clearInterval(pollRef.current);
          router.push(`/join/${token}/complete`);
        }
      } catch {
        setStatusError('Connection issue. Retrying…');
      }
    };

    // Run immediately then poll
    checkStatus();
    pollRef.current = setInterval(checkStatus, POLL_INTERVAL_MS);

    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [token, router]);

  const handleLeave = () => {
    if (pollRef.current) clearInterval(pollRef.current);
    clearCandidateSession();
    router.push(`/join/${token}`);
  };

  if (sessionMissing) {
    return (
      <div className="min-h-screen bg-[#07080c] text-white flex items-center justify-center p-4">
        <div className="max-w-md w-full rounded-2xl border border-zinc-800 bg-[#0d0e14] p-8 text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
          <h1 className="text-lg font-bold">Session Expired</h1>
          <p className="text-sm text-zinc-400">
            Your session has expired. Please rejoin using your interview link.
          </p>
          <button
            onClick={() => router.push(`/join/${token}`)}
            className="text-sm text-indigo-400 hover:text-indigo-300"
          >
            ← Rejoin interview
          </button>
        </div>
      </div>
    );
  }

  const dots = '.'.repeat(dotCount);

  return (
    <div className="min-h-screen bg-[#07080c] text-white flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/60">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Terminal className="h-4 w-4" />
          </div>
          <span className="font-bold text-sm">
            Interview<span className="text-indigo-400 font-black">OS</span>
          </span>
        </div>
        {candidateName && (
          <span className="text-xs text-zinc-400 font-medium">{candidateName}</span>
        )}
      </header>

      {/* Progress bar */}
      <div className="h-1 bg-zinc-900">
        <div className="h-1 w-full bg-indigo-500 rounded-full" />
      </div>

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6 text-center">
          {/* Pulsing indicator */}
          <div className="relative mx-auto h-20 w-20">
            <div className="absolute inset-0 rounded-full bg-indigo-500/20 animate-ping" />
            <div className="relative flex h-full w-full items-center justify-center rounded-full bg-indigo-500/10 border border-indigo-500/30">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
            </div>
          </div>

          <div className="space-y-2">
            <h1 className="text-xl font-bold text-white">You&apos;re ready!</h1>
            <p className="text-sm text-zinc-400">
              Waiting for the interviewer{dots}
            </p>
          </div>

          {/* Device status */}
          <div className="rounded-xl border border-zinc-800 bg-[#0d0e14] px-6 py-4 space-y-2.5 text-left">
            <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <Camera className="h-3.5 w-3.5" />
              Camera ready
            </div>
            <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              <Mic className="h-3.5 w-3.5" />
              Microphone ready
            </div>
            <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Interview verified
            </div>
          </div>

          <p className="text-xs text-zinc-600">
            The interviewer will start the session shortly. Please keep this tab open.
          </p>

          {statusError && (
            <div className="rounded-lg border border-amber-500/20 bg-amber-950/10 p-3 text-xs text-amber-300">
              {statusError}
            </div>
          )}

          {/* Leave */}
          <button
            id="candidate-leave-btn"
            onClick={handleLeave}
            className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors mx-auto"
          >
            <LogOut className="h-3.5 w-3.5" />
            Leave
          </button>
        </div>
      </main>
    </div>
  );
}
