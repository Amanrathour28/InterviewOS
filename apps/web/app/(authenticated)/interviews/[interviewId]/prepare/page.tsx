'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Play,
  Clock,
  User,
  Briefcase,
  Layers,
  Code2,
  PenTool,
  HelpCircle,
  FileText,
  Users,
  CheckCircle2,
  AlertCircle,
  Shield,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { InterviewBlueprintModal } from '@/components/intelligence/interview-blueprint-modal';
import { QuestionPlanWorkspace } from '@/components/intelligence/question-plan-workspace';

export default function PreInterviewPreparationPage() {
  const params = useParams();
  const router = useRouter();
  const interviewId = params?.interviewId as string;

  const [interview, setInterview] = useState<any>(null);
  const [session, setSession] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'blueprint' | 'question_plan' | 'rounds' | 'candidate'>('overview');
  const [showBlueprintModal, setShowBlueprintModal] = useState(false);

  useEffect(() => {
    async function loadData() {
      try {
        setIsLoading(true);
        const [itwData, sessData] = await Promise.all([
          apiClient<any>(`/interviews/${interviewId}`),
          apiClient<any>(`/interviews/${interviewId}/session`, { method: 'POST' }).catch(() => null),
        ]);
        setInterview(itwData);
        setSession(sessData);
      } catch (err) {
        console.error('Failed to load preparation data:', err);
      } finally {
        setIsLoading(false);
      }
    }
    if (interviewId) {
      loadData();
    }
  }, [interviewId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400 text-xs">
        Loading Pre-Interview Preparation Hub...
      </div>
    );
  }

  if (!interview) {
    return (
      <div className="p-8 text-center text-slate-400 text-sm">
        Interview configuration not found.
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Link
              href={`/interviews/${interviewId}`}
              className="text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <Badge variant="outline" className="border-indigo-500/40 text-indigo-400 text-[10px] uppercase font-mono">
              Pre-Interview Preparation
            </Badge>
          </div>
          <h1 className="text-xl font-bold text-white tracking-tight">{interview.title}</h1>
          <p className="text-xs text-slate-400">
            Review candidate background, rubric questions, coding challenges, and launch the live room.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={() => setShowBlueprintModal(true)}
            className="text-xs border-slate-700 text-indigo-300 hover:bg-indigo-950/30 flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
            <span>Generate Blueprint</span>
          </Button>

          <Button
            onClick={() => router.push(`/interviews/${interviewId}/room`)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-5 h-9 flex items-center gap-2 shadow-lg shadow-indigo-600/20"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Enter Live Room</span>
          </Button>
        </div>
      </div>

      {/* Quick Summary Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <Card className="p-3.5 bg-slate-900/80 border-slate-800 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <User className="w-3 h-3 text-indigo-400" /> Candidate
          </span>
          <div className="text-xs font-semibold text-white">
            {interview.candidate ? `${interview.candidate.first_name} ${interview.candidate.last_name}` : 'Unknown Candidate'}
          </div>
          <div className="text-[10px] text-slate-500 font-mono truncate">
            {interview.candidate?.email}
          </div>
        </Card>

        <Card className="p-3.5 bg-slate-900/80 border-slate-800 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Briefcase className="w-3 h-3 text-cyan-400" /> Target Role
          </span>
          <div className="text-xs font-semibold text-white">
            {interview.job ? interview.job.title : 'Engineering Position'}
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            {interview.interview_type ? interview.interview_type.toUpperCase() : 'TECHNICAL'}
          </div>
        </Card>

        <Card className="p-3.5 bg-slate-900/80 border-slate-800 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Clock className="w-3 h-3 text-amber-400" /> Duration
          </span>
          <div className="text-xs font-semibold text-white">
            {interview.duration_minutes || 60} Minutes
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            {interview.rounds?.length || 0} Configured Rounds
          </div>
        </Card>

        <Card className="p-3.5 bg-slate-900/80 border-slate-800 space-y-1">
          <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider flex items-center gap-1.5">
            <Users className="w-3 h-3 text-emerald-400" /> Interview Panel
          </span>
          <div className="text-xs font-semibold text-white">
            {interview.participants?.length || 1} Interviewer(s)
          </div>
          <div className="text-[10px] text-slate-500 font-mono">
            Lead: You
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-4 text-xs font-medium">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-2.5 transition-colors border-b-2 -mb-px ${
            activeTab === 'overview'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Interview Agenda
        </button>
        <button
          onClick={() => setActiveTab('blueprint')}
          className={`pb-2.5 transition-colors border-b-2 -mb-px flex items-center gap-1.5 ${
            activeTab === 'blueprint'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <Sparkles className="w-3 h-3 text-indigo-400" />
          <span>AI Blueprint</span>
        </button>
        <button
          onClick={() => setActiveTab('question_plan')}
          className={`pb-2.5 transition-colors border-b-2 -mb-px flex items-center gap-1.5 ${
            activeTab === 'question_plan'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          <HelpCircle className="w-3 h-3 text-indigo-400" />
          <span>Question Plan & Matrix</span>
        </button>
        <button
          onClick={() => setActiveTab('rounds')}
          className={`pb-2.5 transition-colors border-b-2 -mb-px ${
            activeTab === 'rounds'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Configured Rounds ({interview.rounds?.length || 0})
        </button>
        <button
          onClick={() => setActiveTab('candidate')}
          className={`pb-2.5 transition-colors border-b-2 -mb-px ${
            activeTab === 'candidate'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Candidate Background
        </button>
      </div>

      {/* Tab Content: Blueprint */}
      {activeTab === 'blueprint' && (
        <div className="space-y-4">
          <Card className="p-6 bg-slate-900/60 border-slate-800 text-center space-y-4">
            <div className="w-12 h-12 rounded-2xl bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto">
              <Sparkles className="w-6 h-6" />
            </div>
            <div className="space-y-1 max-w-md mx-auto">
              <h3 className="text-sm font-bold text-white">Synthesize Interview Blueprint</h3>
              <p className="text-xs text-slate-400">
                Generate an end-to-end multi-round interview blueprint personalized to candidate claims and job requirements.
              </p>
            </div>
            <Button
              onClick={() => setShowBlueprintModal(true)}
              className="text-xs font-semibold"
            >
              Open Blueprint Planner
            </Button>
          </Card>
        </div>
      )}

      {/* Tab Content: Question Plan */}
      {activeTab === 'question_plan' && (
        <QuestionPlanWorkspace interviewId={interviewId} />
      )}

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Interview Checklist & Guidelines
              </h3>
              <div className="space-y-2 text-xs text-slate-300">
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>Introduce yourself and review the interview structure with the candidate.</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>Verify video/audio clarity before beginning the technical assessment.</span>
                </div>
                <div className="flex items-start gap-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                  <span>Use the <strong>Live Activity Timeline</strong> and <strong>Structured Private Notes</strong> to record rubric signals without revealing them to the candidate.</span>
                </div>
              </div>
            </Card>

            {/* Candidate Instructions */}
            <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-2">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Candidate-Facing Instructions
              </h3>
              <p className="text-xs text-slate-300 leading-relaxed">
                {interview.description || 'Welcome to your technical interview. You will collaborate on code and architecture diagrams with your interviewer.'}
              </p>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-3">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Shield className="w-3.5 h-3.5 text-purple-400" /> Confidentiality Guarantee
              </h3>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                All notes, rating rubrics, and internal job benchmarks recorded in this hub remain strictly confidential to your organization and are never exposed to the candidate.
              </p>
            </Card>
          </div>
        </div>
      )}

      {activeTab === 'rounds' && (
        <div className="space-y-3">
          {(!interview.rounds || interview.rounds.length === 0) ? (
            <div className="p-8 text-center text-slate-500 text-xs">
              No interview rounds configured. Standard format will be used.
            </div>
          ) : (
            interview.rounds.map((round: any, idx: number) => (
              <Card key={round.id} className="p-4 bg-slate-900/60 border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-indigo-400 font-bold">
                      Round #{idx + 1}
                    </span>
                    <h4 className="text-xs font-bold text-white">{round.name}</h4>
                  </div>
                  <Badge variant="outline" className="text-[10px] border-slate-700 text-slate-400">
                    {round.duration_minutes} Mins
                  </Badge>
                </div>
                {round.description && (
                  <p className="text-xs text-slate-400">{round.description}</p>
                )}
              </Card>
            ))
          )}
        </div>
      )}

      {activeTab === 'candidate' && (
        <Card className="p-5 bg-slate-900/60 border-slate-800 space-y-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-300 font-bold text-sm">
              {interview.candidate?.first_name?.[0] || 'C'}
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">
                {interview.candidate?.first_name} {interview.candidate?.last_name}
              </h3>
              <p className="text-xs text-slate-400 font-mono">{interview.candidate?.email}</p>
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 text-xs text-slate-300 space-y-2">
            <div>
              <span className="text-slate-500 font-mono text-[10px] uppercase block">Applied For</span>
              <span className="font-semibold text-white">{interview.job?.title || 'Engineering Role'}</span>
            </div>
            <div>
              <span className="text-slate-500 font-mono text-[10px] uppercase block">Candidate Timezone</span>
              <span className="font-mono text-slate-300">{interview.candidate?.timezone || 'UTC'}</span>
            </div>
          </div>
        </Card>
      )}

      {/* Blueprint Generator Modal */}
      {showBlueprintModal && (
        <InterviewBlueprintModal
          isOpen={showBlueprintModal}
          onClose={() => setShowBlueprintModal(false)}
          candidateId={interview.candidate_id || interview.candidate?.id || ''}
          jobId={interview.job_id || interview.job?.id || ''}
          interviewId={interviewId}
          onApplied={() => {
            // refresh interview details
            apiClient<any>(`/interviews/${interviewId}`).then((res) => setInterview(res)).catch(() => {});
          }}
        />
      )}
    </div>
  );
}
