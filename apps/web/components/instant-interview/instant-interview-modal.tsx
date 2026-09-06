'use client';

import React, { useState } from 'react';
import {
  Zap,
  X,
  Copy,
  Check,
  ExternalLink,
  Loader2,
  ChevronRight,
  User,
  Mail,
  Clock,
  Terminal,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { useAuthStore } from '@/lib/auth/auth-store';
import { useRouter } from 'next/navigation';

type InterviewType = 'technical' | 'coding' | 'system_design' | 'behavioral' | 'mixed' | 'screening';

interface InstantInterviewResult {
  interview_id: string;
  token: string;
  join_url: string;
  candidate_id: string;
}

interface InstantInterviewModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const INTERVIEW_TYPES: { value: InterviewType; label: string }[] = [
  { value: 'technical', label: 'Technical Interview' },
  { value: 'coding', label: 'Coding Interview' },
  { value: 'system_design', label: 'System Design Interview' },
  { value: 'behavioral', label: 'Behavioral Interview' },
  { value: 'mixed', label: 'Mixed Interview' },
  { value: 'screening', label: 'Screening Interview' },
];

const DURATIONS = [30, 45, 60, 90, 120];

export function InstantInterviewModal({ isOpen, onClose }: InstantInterviewModalProps) {
  const router = useRouter();
  const { activeWorkspace } = useAuthStore();

  // Form state
  const [interviewType, setInterviewType] = useState<InterviewType>('technical');
  const [duration, setDuration] = useState(60);
  const [candidateName, setCandidateName] = useState('');
  const [candidateEmail, setCandidateEmail] = useState('');

  // Submission state
  const [isCreating, setIsCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [result, setResult] = useState<InstantInterviewResult | null>(null);
  const [copied, setCopied] = useState(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace) {
      setCreateError('No workspace selected. Please select a workspace from the dashboard.');
      return;
    }
    setIsCreating(true);
    setCreateError(null);

    try {
      const data = await apiClient<InstantInterviewResult>('/interviews/instant', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: activeWorkspace.id,
          interview_type: interviewType,
          duration_minutes: duration,
          candidate_name: candidateName.trim() || null,
          candidate_email: candidateEmail.trim() || null,
        }),
      });
      setResult(data);
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create interview. Please try again.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleCopy = async () => {
    if (!result) return;
    try {
      await navigator.clipboard.writeText(result.join_url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch {
      // Clipboard API not available — show the URL for manual copy
      setCopied(false);
    }
  };

  const handleStartInterview = () => {
    if (!result) return;
    onClose();
    router.push(`/interviews/${result.interview_id}/room`);
  };

  const handleClose = () => {
    setResult(null);
    setCreateError(null);
    setCandidateName('');
    setCandidateEmail('');
    setInterviewType('technical');
    setDuration(60);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-[#0d0e14] shadow-2xl overflow-hidden">
        {/* Modal header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/80">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
              <Zap className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-white">
                {result ? 'Interview Ready' : 'Start Instant Interview'}
              </h2>
              <p className="text-[10px] text-zinc-500 mt-0.5">
                {result
                  ? 'Share the link below with your candidate'
                  : 'Create a room and share the link instantly'}
              </p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-zinc-800 transition-colors"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* ── STEP 1: Configuration form ── */}
          {!result && (
            <form onSubmit={handleCreate} className="space-y-4">
              {/* Interview Type */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-300">Interview Type</label>
                <select
                  value={interviewType}
                  onChange={(e) => setInterviewType(e.target.value as InterviewType)}
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-sm text-white focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
                  id="instant-interview-type"
                >
                  {INTERVIEW_TYPES.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </div>

              {/* Duration */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                  <Clock className="h-3 w-3 text-zinc-500" />
                  Duration
                </label>
                <div className="flex gap-2 flex-wrap">
                  {DURATIONS.map((d) => (
                    <button
                      key={d}
                      type="button"
                      onClick={() => setDuration(d)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${
                        duration === d
                          ? 'border-indigo-500 bg-indigo-500/15 text-indigo-300'
                          : 'border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700 hover:text-white'
                      }`}
                    >
                      {d} min
                    </button>
                  ))}
                </div>
              </div>

              {/* Candidate Name (optional) */}
              <div className="space-y-1.5">
                <label htmlFor="instant-candidate-name" className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                  <User className="h-3 w-3 text-zinc-500" />
                  Candidate Name
                  <span className="text-zinc-600 font-normal">(optional)</span>
                </label>
                <input
                  id="instant-candidate-name"
                  type="text"
                  value={candidateName}
                  onChange={(e) => setCandidateName(e.target.value)}
                  placeholder="e.g. Rahul Sharma"
                  maxLength={150}
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-sm text-white placeholder:text-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
              </div>

              {/* Candidate Email (optional) */}
              <div className="space-y-1.5">
                <label htmlFor="instant-candidate-email" className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5">
                  <Mail className="h-3 w-3 text-zinc-500" />
                  Candidate Email
                  <span className="text-zinc-600 font-normal">(optional)</span>
                </label>
                <input
                  id="instant-candidate-email"
                  type="email"
                  value={candidateEmail}
                  onChange={(e) => setCandidateEmail(e.target.value)}
                  placeholder="rahul@example.com"
                  maxLength={255}
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-sm text-white placeholder:text-zinc-600 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
              </div>

              {createError && (
                <div className="rounded-lg border border-rose-500/30 bg-rose-950/20 px-3 py-2 text-xs text-rose-300">
                  {createError}
                </div>
              )}

              {!activeWorkspace && (
                <div className="rounded-lg border border-amber-500/20 bg-amber-950/10 px-3 py-2 text-xs text-amber-300">
                  No workspace selected. Please set up an organization and workspace first.
                </div>
              )}

              <button
                id="instant-interview-create-btn"
                type="submit"
                disabled={isCreating || !activeWorkspace}
                className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 text-sm font-bold text-white transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
              >
                {isCreating ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Creating Interview…
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4" />
                    Create Interview
                  </>
                )}
              </button>
            </form>
          )}

          {/* ── STEP 2: Interview Ready ── */}
          {result && (
            <div className="space-y-5">
              {/* Success indicator */}
              <div className="flex items-center justify-center">
                <div className="h-14 w-14 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
                  <Terminal className="h-7 w-7 text-emerald-400" />
                </div>
              </div>

              <p className="text-center text-sm text-zinc-400 leading-relaxed">
                Your interview room is ready. Copy the link below and share it with your candidate.
              </p>

              {/* Join URL */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                  Candidate Join Link
                </span>
                <div className="flex items-center gap-2">
                  <div className="flex-1 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs font-mono text-indigo-300 truncate select-all">
                    {result.join_url}
                  </div>
                  <button
                    id="instant-interview-copy-btn"
                    onClick={handleCopy}
                    title="Copy link"
                    className={`shrink-0 flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold border transition-all ${
                      copied
                        ? 'border-emerald-500/40 bg-emerald-950/20 text-emerald-400'
                        : 'border-zinc-700 bg-zinc-900 text-zinc-300 hover:border-zinc-600 hover:text-white'
                    }`}
                  >
                    {copied ? (
                      <>
                        <Check className="h-3.5 w-3.5" />
                        Copied!
                      </>
                    ) : (
                      <>
                        <Copy className="h-3.5 w-3.5" />
                        Copy
                      </>
                    )}
                  </button>
                </div>
              </div>

              <div className="text-xs text-zinc-600 text-center">
                Candidates do not need to create an account to join.
              </div>

              {/* Actions */}
              <div className="flex flex-col gap-2">
                <button
                  id="instant-interview-start-btn"
                  onClick={handleStartInterview}
                  className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 px-6 py-3 text-sm font-bold text-white transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
                >
                  <ExternalLink className="h-4 w-4" />
                  Start Interview
                  <ChevronRight className="h-4 w-4" />
                </button>
                <button
                  onClick={handleClose}
                  className="w-full py-2.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
