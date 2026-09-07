'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Terminal, User, Mail, Loader2, ArrowLeft, ChevronRight, AlertCircle } from 'lucide-react';
import { setCandidateSession, getCandidateSession } from '@/lib/candidate-session';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' ? '/api/v1' : 'http://127.0.0.1:8000/api/v1');

interface JoinInfo {
  candidate_name: string | null;
  candidate_email: string | null;
  requires_identity: boolean;
  interview_id: string;
  title: string;
}

export default function CandidateIdentityPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const [info, setInfo] = useState<JoinInfo | null>(null);
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchInfo = useCallback(async () => {
    if (!token) return;
    try {
      // Check for existing valid session first
      const existing = getCandidateSession(token);
      if (existing) {
        router.replace(`/join/${token}/device-check`);
        return;
      }

      const res = await fetch(`${API_BASE}/interviews/join/${token}`);
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Interview link is invalid or has expired.');
      }
      const data: JoinInfo = await res.json();
      setInfo(data);
      if (data.candidate_name) setName(data.candidate_name);
      if (data.candidate_email) setEmail(data.candidate_email);
    } catch (err: any) {
      setError(err.message || 'Failed to load interview details.');
    } finally {
      setIsLoading(false);
    }
  }, [token, router]);

  useEffect(() => {
    fetchInfo();
  }, [fetchInfo]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    setIsSubmitting(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/interviews/join/${token}/identity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: name.trim(),
          email: email.trim() || null,
        }),
      });

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to submit identity. Please try again.');
      }

      const data = await res.json();

      // Persist candidate session
      setCandidateSession({
        candidateSessionToken: data.candidate_session_token,
        interviewId: data.interview_id,
        candidateName: data.candidate_name,
        joinToken: token,
        expiresAt: Date.now() + data.expires_in_seconds * 1000,
      });

      router.push(`/join/${token}/device-check`);
    } catch (err: any) {
      setError(err.message || 'Something went wrong. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#07080c] flex items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-indigo-400" />
      </div>
    );
  }

  if (error && !info) {
    return (
      <div className="min-h-screen bg-[#07080c] text-white flex items-center justify-center p-4">
        <div className="max-w-md w-full rounded-2xl border border-zinc-800 bg-[#0d0e14] p-8 text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
          <p className="text-sm text-zinc-400">{error}</p>
          <button
            onClick={() => router.push(`/join/${token}`)}
            className="text-xs text-indigo-400 hover:text-indigo-300"
          >
            ← Back to interview
          </button>
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
          <span className="font-bold text-sm">
            Interview<span className="text-indigo-400 font-black">OS</span>
          </span>
        </div>
        <button
          onClick={() => router.push(`/join/${token}`)}
          className="flex items-center gap-1 text-xs text-zinc-500 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </button>
      </header>

      {/* Progress bar */}
      <div className="h-1 bg-zinc-900">
        <div className="h-1 w-1/3 bg-indigo-500 rounded-full transition-all" />
      </div>

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-md space-y-6">
          <div className="rounded-2xl border border-zinc-800 bg-[#0d0e14] p-8 space-y-6">
            <div className="text-center space-y-1">
              <div className="h-12 w-12 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto mb-3">
                <User className="h-6 w-6 text-indigo-400" />
              </div>
              <h1 className="text-xl font-bold text-white">Before you join</h1>
              <p className="text-xs text-zinc-500">
                Please confirm your details before entering the interview.
              </p>
            </div>

            {error && (
              <div className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-3 text-xs text-rose-300">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Name */}
              <div className="space-y-1.5">
                <label htmlFor="candidate-name" className="text-xs font-semibold text-zinc-300">
                  Your Name <span className="text-rose-400">*</span>
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
                  <input
                    id="candidate-name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g. Rahul Sharma"
                    className="w-full h-11 rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-4 text-sm text-white placeholder:text-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
                    autoFocus
                  />
                </div>
              </div>

              {/* Email */}
              <div className="space-y-1.5">
                <label htmlFor="candidate-email" className="text-xs font-semibold text-zinc-300">
                  Email <span className="text-zinc-600">(optional)</span>
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-zinc-500" />
                  <input
                    id="candidate-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="rahul@example.com"
                    className="w-full h-11 rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-4 text-sm text-white placeholder:text-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
                  />
                </div>
              </div>

              <button
                id="candidate-identity-submit"
                type="submit"
                disabled={isSubmitting || !name.trim()}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3.5 text-sm font-bold text-white transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Confirming…
                  </>
                ) : (
                  <>
                    Continue
                    <ChevronRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </form>
          </div>

          <p className="text-center text-[11px] text-zinc-600">
            InterviewOS · Your information is used only for this interview session
          </p>
        </div>
      </main>
    </div>
  );
}
