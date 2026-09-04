'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  Terminal,
  ArrowLeft,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  Users,
  Briefcase,
  Plus,
  Trash2,
  Tag,
  BookOpen,
  Calendar,
  ExternalLink,
  Shield,
  FileText,
  Send,
  RotateCw,
  Globe,
  Hourglass,
  Check,
  Copy,
  Video,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface QuestionItem {
  id: string;
  title: string;
  prompt: string;
  question_type: string;
  difficulty: string;
  category: string;
}

interface RoundQuestionItem {
  id: string;
  question_id: string;
  sequence: number;
  question?: QuestionItem;
}

interface RoundItem {
  id: string;
  name: string;
  description?: string;
  round_type: string;
  sequence: number;
  duration_minutes: number;
  difficulty: string;
  instructions?: string;
  questions: RoundQuestionItem[];
}

interface ParticipantItem {
  id: string;
  user_id: string;
  user_name?: string;
  user_email?: string;
  participant_role: string;
  is_primary: boolean;
}

interface ReadinessInfo {
  is_ready: boolean;
  current_status: string;
  issues: string[];
}

interface ScheduleDetail {
  id: string;
  interview_id: string;
  workspace_id: string;
  scheduled_start_at: string;
  scheduled_end_at: string;
  timezone: string;
  status: string;
  cancellation_reason?: string;
}

interface InterviewDetail {
  id: string;
  workspace_id: string;
  candidate_id: string;
  candidate_name?: string;
  candidate_email?: string;
  job_id?: string;
  job_title?: string;
  title: string;
  description: string;
  interview_type: string;
  status: string;
  difficulty: string;
  duration_minutes: number;
  timezone: string;
  instructions?: string;
  candidate_instructions?: string;
  interviewer_instructions?: string;
  rounds: RoundItem[];
  participants: ParticipantItem[];
  readiness: ReadinessInfo;
  created_at: string;
}

export default function InterviewDetailPage() {
  const params = useParams();
  const router = useRouter();
  const interviewId = params?.interviewId as string;

  const [interview, setInterview] = useState<InterviewDetail | null>(null);
  const [schedule, setSchedule] = useState<ScheduleDetail | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'rounds' | 'panel' | 'readiness'>('overview');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Live countdown timer state
  const [countdownText, setCountdownText] = useState<string>('');

  // Add Round Modal
  const [showAddRound, setShowAddRound] = useState(false);
  const [roundName, setRoundName] = useState('');
  const [roundType, setRoundType] = useState('coding');
  const [roundDuration, setRoundDuration] = useState(30);

  // Schedule Modal
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [scheduleDate, setScheduleDate] = useState<string>('');
  const [scheduleTime, setScheduleTime] = useState<string>('10:00');
  const [scheduleTimezone, setScheduleTimezone] = useState<string>('UTC');
  const [availableSlots, setAvailableSlots] = useState<any[]>([]);
  const [isLoadingSlots, setIsLoadingSlots] = useState(false);
  const [isSubmittingSchedule, setIsSubmittingSchedule] = useState(false);
  const [scheduleError, setScheduleError] = useState<string | null>(null);

  // Invitation Modal
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRecipientType, setInviteRecipientType] = useState('candidate');
  const [isSendingInvite, setIsSendingInvite] = useState(false);
  const [generatedInviteLink, setGeneratedInviteLink] = useState<string | null>(null);
  const [isCopied, setIsCopied] = useState(false);

  // Set default timezone on client
  useEffect(() => {
    try {
      const viewerTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
      if (viewerTz) setScheduleTimezone(viewerTz);
    } catch {
      setScheduleTimezone('UTC');
    }
  }, []);

  const fetchInterview = useCallback(async () => {
    if (!interviewId) return;
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiClient<InterviewDetail>(`/interviews/${interviewId}`);
      setInterview(data);

      // Attempt to load schedule
      try {
        const sched = await apiClient<ScheduleDetail>(`/interviews/${interviewId}/schedule`);
        setSchedule(sched);
      } catch {
        setSchedule(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load interview session');
    } finally {
      setIsLoading(false);
    }
  }, [interviewId]);

  useEffect(() => {
    fetchInterview();
  }, [fetchInterview]);

  // Update countdown
  useEffect(() => {
    if (!schedule || schedule.status !== 'confirmed') {
      setCountdownText('');
      return;
    }

    const updateTimer = () => {
      const startMs = new Date(schedule.scheduled_start_at).getTime();
      const nowMs = Date.now();
      const diffMs = startMs - nowMs;

      if (diffMs <= 0) {
        setCountdownText('Session in progress or completed');
        return;
      }

      const days = Math.floor(diffMs / (1000 * 60 * 60 * 24));
      const hours = Math.floor((diffMs % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
      const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

      if (days > 0) {
        setCountdownText(`Starts in ${days}d ${hours}h`);
      } else {
        setCountdownText(`Starts in ${hours}h ${minutes}m`);
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 60000);
    return () => clearInterval(interval);
  }, [schedule]);

  const handleStatusTransition = async (targetStatus: string) => {
    try {
      await apiClient(`/interviews/${interviewId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: targetStatus }),
      });
      await fetchInterview();
    } catch (err: any) {
      alert(err.message || `Failed to transition status to ${targetStatus}`);
    }
  };

  const handleFetchSlots = async (selectedD: string) => {
    setScheduleDate(selectedD);
    if (!selectedD) return;
    setIsLoadingSlots(true);
    try {
      const res = await apiClient<any>(
        `/interviews/${interviewId}/available-slots?date=${selectedD}&timezone=${encodeURIComponent(scheduleTimezone)}`
      );
      setAvailableSlots(res.slots || []);
    } catch (err: any) {
      console.error('Failed to load slots', err);
    } finally {
      setIsLoadingSlots(false);
    }
  };

  const handleScheduleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!scheduleDate || !scheduleTime) return;

    setIsSubmittingSchedule(true);
    setScheduleError(null);

    try {
      const combined = `${scheduleDate}T${scheduleTime}:00`;
      await apiClient(`/interviews/${interviewId}/schedule`, {
        method: 'POST',
        body: JSON.stringify({
          scheduled_start_at: combined,
          timezone: scheduleTimezone,
        }),
      });
      setShowScheduleModal(false);
      await fetchInterview();
    } catch (err: any) {
      setScheduleError(err.message || 'Failed to schedule interview');
    } finally {
      setIsSubmittingSchedule(false);
    }
  };

  const handleCancelSchedule = async () => {
    const reason = prompt('Please enter cancellation reason:');
    if (reason === null) return;

    try {
      await apiClient(`/interviews/${interviewId}/schedule`, {
        method: 'DELETE',
        body: JSON.stringify({ cancellation_reason: reason || 'Cancelled by organizer' }),
      });
      await fetchInterview();
    } catch (err: any) {
      alert(err.message || 'Failed to cancel schedule');
    }
  };

  const handleSendInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inviteEmail) return;

    setIsSendingInvite(true);
    try {
      const res = await apiClient<any>(`/interviews/${interviewId}/invitations`, {
        method: 'POST',
        body: JSON.stringify({
          recipient_type: inviteRecipientType,
          email: inviteEmail.trim(),
          recipient_candidate_id: inviteRecipientType === 'candidate' ? interview?.candidate_id : undefined,
        }),
      });
      // In development, display the link
      const origin = typeof window !== 'undefined' ? window.location.origin : 'http://localhost:3000';
      setGeneratedInviteLink(`${origin}/invite/${res.token || 'sent'}`);
    } catch (err: any) {
      alert(err.message || 'Failed to send invitation');
    } finally {
      setIsSendingInvite(false);
    }
  };

  const handleAddRound = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!roundName.trim()) return;

    try {
      await apiClient(`/interviews/${interviewId}/rounds`, {
        method: 'POST',
        body: JSON.stringify({
          name: roundName.trim(),
          round_type: roundType,
          duration_minutes: roundDuration,
          sequence: (interview?.rounds.length || 0) + 1,
        }),
      });
      setShowAddRound(false);
      setRoundName('');
      await fetchInterview();
    } catch (err: any) {
      alert(err.message || 'Failed to add round');
    }
  };

  const handleDeleteRound = async (roundId: string) => {
    if (!confirm('Are you sure you want to remove this round?')) return;
    try {
      await apiClient(`/interviews/${interviewId}/rounds/${roundId}`, { method: 'DELETE' });
      await fetchInterview();
    } catch (err: any) {
      alert(err.message || 'Failed to delete round');
    }
  };

  const handleDeleteInterview = async () => {
    if (!confirm('Are you sure you want to soft delete this interview?')) return;
    try {
      await apiClient(`/interviews/${interviewId}`, { method: 'DELETE' });
      router.push('/interviews');
    } catch (err: any) {
      alert(err.message || 'Failed to delete interview');
    }
  };

  if (isLoading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center text-center">
        <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-xs text-zinc-500">Loading interview details...</p>
      </div>
    );
  }

  if (error || !interview) {
    return (
      <div className="p-8 text-center space-y-4">
        <div className="h-10 w-10 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
          <AlertCircle className="h-5 w-5" />
        </div>
        <h2 className="text-sm font-semibold text-white">Could not load interview</h2>
        <p className="text-xs text-zinc-400">{error || 'Session not found or unauthorized'}</p>
        <Link href="/interviews">
          <Button size="sm" variant="outline" className="text-xs">
            Back to Interviews
          </Button>
        </Link>
      </div>
    );
  }

  const isReady = interview.readiness?.is_ready;
  const isScheduled = interview.status === 'scheduled' && schedule && schedule.status === 'confirmed';

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          href="/interviews"
          className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Interviews
        </Link>
      </div>

      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="default" className="text-[10px] uppercase">
              {interview.interview_type.replace('_', ' ')}
            </Badge>
            <Badge variant="outline" className="text-[10px] capitalize">
              {interview.difficulty} level
            </Badge>
            {isScheduled ? (
              <Badge variant="outline" className="text-cyan-400 border-cyan-400/30 text-[10px]">
                SCHEDULED
              </Badge>
            ) : isReady ? (
              <Badge variant="success" className="text-[10px]">
                READY
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[10px] text-amber-400 border-amber-400/30">
                DRAFT
              </Badge>
            )}
          </div>

          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            {interview.title}
          </h1>

          <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-400">
            {interview.candidate_name && (
              <Link
                href={`/candidates/${interview.candidate_id}`}
                className="flex items-center gap-1 text-zinc-300 hover:text-primary transition-colors"
              >
                <Users className="h-3.5 w-3.5 text-indigo-400" />
                Candidate: <span className="font-semibold text-white">{interview.candidate_name}</span>
              </Link>
            )}
            {interview.job_title && (
              <Link
                href={`/jobs/${interview.job_id}`}
                className="flex items-center gap-1 text-zinc-300 hover:text-primary transition-colors"
              >
                <Briefcase className="h-3.5 w-3.5 text-indigo-400" />
                Job: <span className="font-semibold text-white">{interview.job_title}</span>
              </Link>
            )}
            <span className="flex items-center gap-1">
              <Clock className="h-3.5 w-3.5 text-zinc-500" />
              {interview.duration_minutes} mins
            </span>
          </div>
        </div>

        {/* Action buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {(isScheduled || interview.status === 'ready' || interview.status === 'in_progress') && (
            <Link href={`/interviews/${interviewId}/room`}>
              <Button
                size="sm"
                className="text-xs font-bold gap-1 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-lg shadow-indigo-500/25"
              >
                <Video className="h-3.5 w-3.5" />
                Enter Live Room
              </Button>
            </Link>
          )}

          {interview.status === 'draft' && (
            <Button
              size="sm"
              disabled={!isReady}
              onClick={() => handleStatusTransition('ready')}
              className="text-xs font-semibold shadow-lg shadow-primary/20"
            >
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
              Mark as Ready
            </Button>
          )}

          {interview.status === 'ready' && (
            <>
              <Button
                size="sm"
                onClick={() => {
                  setScheduleDate(new Date().toISOString().split('T')[0]);
                  setShowScheduleModal(true);
                }}
                className="text-xs font-semibold shadow-lg shadow-primary/20"
              >
                <Calendar className="h-3.5 w-3.5 mr-1" />
                Schedule Session
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleStatusTransition('draft')}
                className="text-xs border-zinc-800 text-zinc-300"
              >
                Revert to Draft
              </Button>
            </>
          )}

          {isScheduled && (
            <Button
              size="sm"
              onClick={() => {
                setInviteEmail(interview.candidate_email || '');
                setShowInviteModal(true);
              }}
              className="text-xs font-semibold shadow-lg shadow-primary/20"
            >
              <Send className="h-3.5 w-3.5 mr-1" />
              Send Invitations
            </Button>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={handleDeleteInterview}
            className="text-xs border-zinc-800 text-rose-400 hover:bg-rose-500/10"
          >
            <Trash2 className="h-3.5 w-3.5 mr-1" />
            Delete
          </Button>
        </div>
      </div>

      {/* CONFIRMED SCHEDULE BANNER WITH COUNTDOWN */}
      {isScheduled && (
        <Card className="border-indigo-500/30 bg-[#0d0e18] p-5 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-bold uppercase tracking-wider text-indigo-400">
                  Confirmed Session
                </span>
                {countdownText && (
                  <Badge variant="outline" className="text-[10px] text-zinc-300 border-zinc-700 font-mono">
                    <Hourglass className="h-3 w-3 mr-1 text-indigo-400" />
                    {countdownText}
                  </Badge>
                )}
              </div>

              <div className="flex flex-wrap items-center gap-4 text-xs">
                <div>
                  <span className="text-zinc-500">Scheduled Time: </span>
                  <strong className="text-white">
                    {new Date(schedule.scheduled_start_at).toLocaleString('en-US', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    })}
                  </strong>
                </div>
                <div>
                  <span className="text-zinc-500">Declared Timezone: </span>
                  <strong className="text-zinc-300">{schedule.timezone}</strong>
                </div>
                <div>
                  <span className="text-zinc-500">UTC: </span>
                  <span className="text-zinc-400 font-mono">{new Date(schedule.scheduled_start_at).toUTCString()}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => setShowScheduleModal(true)}
                className="text-xs border-zinc-800 text-amber-400 hover:bg-amber-500/10"
              >
                <RotateCw className="h-3.5 w-3.5 mr-1" />
                Reschedule
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={handleCancelSchedule}
                className="text-xs border-zinc-800 text-rose-400 hover:bg-rose-500/10"
              >
                Cancel Schedule
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Readiness Banner (for unready states) */}
      {!isReady && interview.readiness?.issues?.length > 0 && (
        <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-950/20 space-y-1 text-xs">
          <div className="flex items-center gap-2 font-bold text-amber-300">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>Configuration Issues Preventing Readiness:</span>
          </div>
          <ul className="text-amber-200/90 list-disc list-inside space-y-0.5 text-[11px] pt-1">
            {interview.readiness.issues.map((iss, idx) => (
              <li key={idx}>{iss}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-zinc-800 text-xs font-medium">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 border-b-2 transition-all ${
            activeTab === 'overview'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          Session Overview
        </button>
        <button
          onClick={() => setActiveTab('rounds')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'rounds'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <span>Rounds & Questions</span>
          <span className="px-1.5 py-0.2 rounded text-[10px] bg-zinc-800 text-zinc-300">
            {interview.rounds?.length || 0}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('panel')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'panel'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <span>Interview Panel</span>
          <span className="px-1.5 py-0.2 rounded text-[10px] bg-zinc-800 text-zinc-300">
            {interview.participants?.length || 0}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('readiness')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'readiness'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <span>Readiness Checklist</span>
        </button>
      </div>

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-3">
              <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                Objectives & Scope
              </h3>
              <p className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">
                {interview.description || 'No description provided.'}
              </p>
            </Card>

            {interview.instructions && (
              <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-3">
                <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                  Panel Instructions
                </h3>
                <p className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">
                  {interview.instructions}
                </p>
              </Card>
            )}
          </div>

          <div className="lg:col-span-4 space-y-4">
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-5 space-y-3 text-xs">
              <h3 className="font-bold text-white uppercase tracking-wider text-[11px] text-zinc-400 border-b border-zinc-800/80 pb-2">
                Session Metadata
              </h3>
              <div className="space-y-2 text-zinc-300">
                <div>
                  <span className="text-zinc-500">Duration:</span> <span>{interview.duration_minutes} minutes</span>
                </div>
                <div>
                  <span className="text-zinc-500">Difficulty:</span> <span className="capitalize">{interview.difficulty}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Timezone:</span> <span>{interview.timezone}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Created:</span> <span>{new Date(interview.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 2: ROUNDS & QUESTIONS */}
      {activeTab === 'rounds' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white">Interview Stage Sequence</h3>
            <Button size="sm" onClick={() => setShowAddRound(true)} className="text-xs font-semibold">
              <Plus className="h-3.5 w-3.5 mr-1" />
              Add Round
            </Button>
          </div>

          <div className="space-y-3">
            {interview.rounds?.map((round, idx) => (
              <Card key={round.id} className="bg-[#0e0f15] border-zinc-800 p-5 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-indigo-400">Round {idx + 1}:</span>
                      <h4 className="text-sm font-bold text-white">{round.name}</h4>
                      <Badge variant="default" className="text-[10px] capitalize">
                        {round.round_type.replace('_', ' ')}
                      </Badge>
                      <span className="text-xs text-zinc-500">• {round.duration_minutes} mins</span>
                    </div>
                    {round.description && <p className="text-xs text-zinc-400">{round.description}</p>}
                  </div>

                  <button
                    onClick={() => handleDeleteRound(round.id)}
                    className="text-zinc-500 hover:text-rose-400 text-xs p-1"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                {/* Attached questions */}
                <div className="pt-2 border-t border-zinc-800/60 space-y-2">
                  <span className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                    Assigned Questions ({round.questions?.length || 0})
                  </span>
                  {round.questions?.length === 0 ? (
                    <p className="text-xs text-zinc-500 italic">No questions assigned to this round yet.</p>
                  ) : (
                    <div className="space-y-1.5">
                      {round.questions?.map((qItem) => (
                        <div
                          key={qItem.id}
                          className="p-2.5 rounded-lg bg-zinc-950 border border-zinc-800/80 text-xs flex items-center justify-between"
                        >
                          <span className="font-medium text-zinc-200">
                            {qItem.question?.title || 'Question prompt'}
                          </span>
                          <span className="text-[10px] text-zinc-500 capitalize">
                            {qItem.question?.difficulty || 'medium'}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* TAB 3: PANEL */}
      {activeTab === 'panel' && (
        <div className="space-y-4">
          <h3 className="text-sm font-bold text-white">Assigned Panel Members</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {interview.participants?.map((p) => (
              <Card key={p.id} className="bg-[#0e0f15] border-zinc-800 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="h-9 w-9 rounded-full bg-primary/10 border border-primary/20 text-primary font-bold text-xs flex items-center justify-center uppercase">
                    {p.user_name?.[0] || 'U'}
                  </div>
                  <div>
                    <p className="text-xs font-bold text-white">{p.user_name}</p>
                    <p className="text-[11px] text-zinc-400">{p.user_email}</p>
                  </div>
                </div>

                <Badge variant="default" className="text-[10px] capitalize">
                  {p.participant_role.replace('_', ' ')}
                </Badge>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* TAB 4: READINESS */}
      {activeTab === 'readiness' && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-4 text-xs">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
            Readiness Audit
          </h3>

          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span className="text-zinc-200">Candidate assigned within workspace ({interview.candidate_name})</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span className="text-zinc-200">Duration configured ({interview.duration_minutes} minutes)</span>
            </div>
            <div className="flex items-center gap-2">
              {interview.rounds?.length > 0 ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <AlertCircle className="h-4 w-4 text-rose-400" />
              )}
              <span className="text-zinc-200">At least 1 round configured ({interview.rounds?.length || 0} rounds)</span>
            </div>
            <div className="flex items-center gap-2">
              {isReady ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              ) : (
                <AlertCircle className="h-4 w-4 text-rose-400" />
              )}
              <span className="text-zinc-200">
                Sum of round durations within total interview duration
              </span>
            </div>
          </div>
        </Card>
      )}

      {/* SCHEDULE INTERVIEW MODAL */}
      {showScheduleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <h3 className="text-base font-bold text-white">Schedule Interview Session</h3>
              <button onClick={() => setShowScheduleModal(false)} className="text-zinc-500 hover:text-white">
                ✕
              </button>
            </div>

            {scheduleError && (
              <div className="p-2.5 rounded bg-rose-950/20 border border-rose-500/30 text-xs text-rose-400">
                {scheduleError}
              </div>
            )}

            <form onSubmit={handleScheduleSubmit} className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-zinc-300 font-semibold">Timezone</label>
                <input
                  type="text"
                  required
                  value={scheduleTimezone}
                  onChange={(e) => setScheduleTimezone(e.target.value)}
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none font-mono"
                />
              </div>

              <div className="space-y-1">
                <label className="text-zinc-300 font-semibold">Date</label>
                <input
                  type="date"
                  required
                  value={scheduleDate}
                  onChange={(e) => handleFetchSlots(e.target.value)}
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              {/* Available slots preview */}
              {availableSlots.length > 0 && (
                <div className="space-y-1 pt-1">
                  <label className="text-[10px] font-bold text-zinc-400 uppercase">Available Compatible Slots</label>
                  <div className="grid grid-cols-3 gap-1.5 max-h-32 overflow-y-auto p-1 bg-zinc-950 rounded border border-zinc-800">
                    {availableSlots.map((s, idx) => {
                      const timeString = new Date(s.start_at).toLocaleTimeString('en-US', {
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: false,
                      });
                      return (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setScheduleTime(timeString)}
                          className={`px-2 py-1 rounded text-[11px] font-mono border transition-all ${
                            scheduleTime === timeString
                              ? 'bg-primary border-primary text-white font-bold'
                              : 'border-zinc-800 bg-zinc-900 text-zinc-300 hover:text-white'
                          }`}
                        >
                          {timeString}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="space-y-1">
                <label className="text-zinc-300 font-semibold">Selected Time (HH:MM)</label>
                <input
                  type="time"
                  required
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowScheduleModal(false)} className="text-xs">
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={isSubmittingSchedule} className="text-xs font-semibold">
                  {isSubmittingSchedule ? 'Checking & Saving...' : 'Confirm Schedule'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* INVITATION DISPATCH MODAL */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <h3 className="text-base font-bold text-white">Send Interview Invitation</h3>
              <button onClick={() => setShowInviteModal(false)} className="text-zinc-500 hover:text-white">
                ✕
              </button>
            </div>

            <form onSubmit={handleSendInvite} className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-zinc-300 font-semibold">Recipient Role</label>
                <select
                  value={inviteRecipientType}
                  onChange={(e) => setInviteRecipientType(e.target.value)}
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none capitalize"
                >
                  <option value="candidate">Candidate</option>
                  <option value="interviewer">Interviewer</option>
                  <option value="observer">Observer</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="text-zinc-300 font-semibold">Recipient Email *</label>
                <input
                  type="email"
                  required
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              {generatedInviteLink && (
                <div className="p-3 rounded-lg bg-zinc-950 border border-emerald-500/30 space-y-2">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-semibold">
                    <Check className="h-4 w-4" />
                    Invitation Dispatched!
                  </div>
                  <div className="flex items-center gap-2">
                    <input
                      type="text"
                      readOnly
                      value={generatedInviteLink}
                      className="flex-1 h-7 rounded border border-zinc-800 bg-zinc-900 px-2 text-[10px] text-zinc-300 select-all"
                    />
                    <Button
                      type="button"
                      size="sm"
                      onClick={() => {
                        navigator.clipboard.writeText(generatedInviteLink);
                        setIsCopied(true);
                        setTimeout(() => setIsCopied(false), 2000);
                      }}
                      className="h-7 text-[10px] px-2"
                    >
                      {isCopied ? 'Copied!' : 'Copy Link'}
                    </Button>
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowInviteModal(false)} className="text-xs">
                  Close
                </Button>
                <Button type="submit" size="sm" disabled={isSendingInvite} className="text-xs font-semibold">
                  {isSendingInvite ? 'Sending...' : 'Send Invitation Email'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
