'use client';

import React, { useEffect } from 'react';
import { Terminal, CheckCircle2, Star } from 'lucide-react';
import { clearCandidateSession } from '@/lib/candidate-session';

export default function CandidateCompletePage() {
  // Clear session on completion
  useEffect(() => {
    clearCandidateSession();
  }, []);

  return (
    <div className="min-h-screen bg-[#07080c] text-white flex flex-col">
      {/* Header */}
      <header className="flex items-center gap-2 px-6 py-4 border-b border-zinc-800/60">
        <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
          <Terminal className="h-4 w-4" />
        </div>
        <span className="font-bold text-sm">
          Interview<span className="text-indigo-400 font-black">OS</span>
        </span>
      </header>

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md text-center space-y-6">
          {/* Success icon */}
          <div className="relative mx-auto h-20 w-20">
            <div className="absolute inset-0 rounded-full bg-emerald-500/10 border border-emerald-500/20" />
            <div className="flex h-full w-full items-center justify-center">
              <CheckCircle2 className="h-10 w-10 text-emerald-400" />
            </div>
          </div>

          <div className="space-y-2">
            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              Interview Complete
            </h1>
            <p className="text-sm text-zinc-400 leading-relaxed">
              Thank you for participating. The interview has ended and your session has been recorded.
            </p>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-[#0d0e14] p-5 space-y-3 text-left">
            <div className="flex items-center gap-2 text-xs text-emerald-400 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5" />
              Interview session completed
            </div>
            <div className="flex items-center gap-2 text-xs text-zinc-400">
              <Star className="h-3.5 w-3.5 text-indigo-400" />
              Your responses have been captured
            </div>
            <div className="flex items-center gap-2 text-xs text-zinc-400">
              <Star className="h-3.5 w-3.5 text-indigo-400" />
              You will be contacted with next steps
            </div>
          </div>

          <p className="text-xs text-zinc-600">
            You may close this tab. InterviewOS · Thank you.
          </p>
        </div>
      </main>
    </div>
  );
}
