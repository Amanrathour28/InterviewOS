'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Terminal, Shield, Clock, AlertCircle, Loader2, ChevronRight } from 'lucide-react';
import { getCandidateSession } from '@/lib/candidate-session';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

interface JoinInfo {
  interview_id: string;
  title: string;
  interview_type: string;
  duration_minutes: number;
  candidate_name: string | null;
  candidate_email: string | null;
  requires_identity: boolean;
  status: string;
}

export default function CandidateLandingPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const [info, setInfo] = useState<JoinInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInfo = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/interviews/join/${token}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'This interview link is invalid or has expired.');
      }
      const data: JoinInfo = await res.json();
      setInfo(data);

      // If candidate already has an active session, skip to device-check
      const existing = getCandidateSession(token);
      if (existing) {
        router.replace(`/join/${token}/device-check`);
      }
    } catch (err: any) {
      setError(err.message || 'This interview link is invalid or has expired.');
    } finally {
      setIsLoading(false);
    }
  }, [token, router]);

  useEffect(() => {
    fetchInfo();
  }, [fetchInfo]);

  const handleContinue = () => {
    if (!info) return;
    if (info.requires_identity) {
      router.push(`/join/${token}/identity`);
    } else {
      router.push(`/join/${token}/device-check`);
    }
  };

  const typeLabel: Record<string, string> = {
    technical: 'Technical Interview',
    coding: 'Coding Interview',
    system_design: 'System Design Interview',
    behavioral: 'Behavioral Interview',
    mixed: 'Mixed Interview',
    screening: 'Screening Interview',
    custom: 'Interview',
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#07080c] text-white flex items-center justify-center">
        <div className="text-center space-y-3">
          <Loader2 className="h-8 w-8 border-indigo-500 animate-spin mx-auto text-indigo-400" />
          <p className="text-xs text-zinc-500 font-mono">Verifying interview link…</p>
        </div>
      </div>
    );
  }

  if (error || !info) {
    return (
      <div className="min-h-screen bg-[#07080c] text-white flex items-center justify-center p-4">
        <div className="max-w-md w-full rounded-2xl border border-zinc-800 bg-[#0d0e14] p-8 text-center space-y-4">
          <div className="h-12 w-12 rounded-full bg-rose-500/10 border border-rose-500/20 flex items-center justify-center mx-auto">
            <AlertCircle className="h-6 w-6 text-rose-400" />
          </div>
          <h1 className="text-lg font-bold text-white">Interview Unavailable</h1>
          <p className="text-sm text-zinc-400 leading-relaxed">
            {error || 'This interview link is invalid or has expired.'}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#07080c] text-white flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/60">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Terminal className="h-4 w-4" />
          </div>
          <span className="font-bold text-sm text-white">
            Interview<span className="text-indigo-400 font-black">OS</span>
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-zinc-500">
          <Shield className="h-3.5 w-3.5 text-emerald-400" />
          Secure Interview
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6">
          {/* Interview card */}
          <div className="rounded-2xl border border-zinc-800 bg-[#0d0e14] p-8 text-center space-y-5">
            {/* Type badge */}
            <div className="inline-flex items-center gap-1.5 rounded-full border border-indigo-500/30 bg-indigo-500/10 px-3 py-1 text-xs font-semibold text-indigo-300">
              {typeLabel[info.interview_type] || 'Interview'}
            </div>

            {/* Title */}
            <div className="space-y-2">
              <h1 className="text-2xl font-extrabold text-white tracking-tight">
                {info.title}
              </h1>
              {info.candidate_name && (
                <p className="text-sm text-zinc-400">
                  Hello, <span className="text-white font-semibold">{info.candidate_name}</span>
                </p>
              )}
            </div>

            {/* Duration */}
            <div className="flex items-center justify-center gap-2 text-sm text-zinc-400">
              <Clock className="h-4 w-4 text-indigo-400" />
              <span>Duration: <strong className="text-white">{info.duration_minutes} minutes</strong></span>
            </div>

            {/* Description */}
            <p className="text-sm text-zinc-500 leading-relaxed">
              You&apos;ve been invited to participate in an online technical interview.
              Please ensure you have a stable internet connection, working camera, and microphone.
            </p>

            {/* Tips */}
            <div className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-4 text-xs text-zinc-400 space-y-1.5 text-left">
              <p className="font-semibold text-zinc-300 mb-2">Before you begin:</p>
              <p>✓ Use a quiet environment</p>
              <p>✓ Allow camera and microphone access</p>
              <p>✓ Use Chrome or Firefox for best experience</p>
            </div>

            {/* CTA */}
            <button
              id="candidate-continue-btn"
              onClick={handleContinue}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-6 py-3.5 text-sm font-bold text-white transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
            >
              Continue
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <p className="text-center text-[11px] text-zinc-600">
            InterviewOS · Secure Technical Interview Platform
          </p>
        </div>
      </main>
    </div>
  );
}
