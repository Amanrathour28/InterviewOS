'use client';

import React, { useState, useEffect } from 'react';
import { Clock, Pause, AlertCircle } from 'lucide-react';

interface InterviewTimerProps {
  startedAt?: string | null;
  pausedAt?: string | null;
  stageStartedAt?: string | null;
  totalPausedSeconds: number;
  durationMinutes: number;
  isPaused: boolean;
  status: string;
}

export const InterviewTimer: React.FC<InterviewTimerProps> = ({
  startedAt,
  pausedAt,
  stageStartedAt,
  totalPausedSeconds,
  durationMinutes,
  isPaused,
  status,
}) => {
  const [now, setNow] = useState<number>(Date.now());

  useEffect(() => {
    if (status !== 'active') return;
    const interval = setInterval(() => {
      setNow(Date.now());
    }, 1000);
    return () => clearInterval(interval);
  }, [status]);

  if (!startedAt || status === 'waiting') {
    return (
      <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-slate-400 text-xs font-mono">
        <Clock className="w-3.5 h-3.5" />
        <span>{durationMinutes}:00</span>
      </div>
    );
  }

  // Calculate elapsed
  const startTime = new Date(startedAt).getTime();
  const currentTime = isPaused && pausedAt ? new Date(pausedAt).getTime() : now;
  const rawElapsed = Math.max(0, Math.floor((currentTime - startTime) / 1000) - totalPausedSeconds);

  // Remaining
  const totalAllocated = durationMinutes * 60;
  const remaining = Math.max(0, totalAllocated - rawElapsed);

  const remMinutes = Math.floor(remaining / 60);
  const remSeconds = remaining % 60;
  const formattedRemaining = `${String(remMinutes).padStart(2, '0')}:${String(remSeconds).padStart(2, '0')}`;

  // Stage elapsed
  let stageElapsedStr = '00:00';
  if (stageStartedAt) {
    const stageStartTime = new Date(stageStartedAt).getTime();
    const stageRaw = Math.max(0, Math.floor((currentTime - stageStartTime) / 1000));
    const sMin = Math.floor(stageRaw / 60);
    const sSec = stageRaw % 60;
    stageElapsedStr = `${String(sMin).padStart(2, '0')}:${String(sSec).padStart(2, '0')}`;
  }

  const isLowTime = remaining <= 300 && remaining > 0;

  return (
    <div className="flex items-center gap-2 select-none">
      {/* Paused Banner */}
      {isPaused && (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40 animate-pulse">
          <Pause className="w-2.5 h-2.5 fill-current" />
          PAUSED
        </span>
      )}

      {/* Main Countdown Timer */}
      <div
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-mono font-semibold transition-colors border ${
          isLowTime
            ? 'bg-rose-500/20 text-rose-300 border-rose-500/40 animate-pulse'
            : isPaused
            ? 'bg-slate-800 text-amber-300 border-amber-500/30'
            : 'bg-slate-800/90 text-white border-slate-700'
        }`}
      >
        <Clock className="w-3.5 h-3.5 text-indigo-400" />
        <span>{formattedRemaining}</span>
      </div>

      {/* Current Stage Elapsed */}
      <span className="hidden md:inline-block text-[10px] font-mono text-slate-500">
        Stage: {stageElapsedStr}
      </span>
    </div>
  );
};
