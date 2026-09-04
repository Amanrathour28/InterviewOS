'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Terminal,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  AlertCircle,
  Clock,
  Layers,
  Users,
  Briefcase,
  BookOpen,
  Code,
  Cpu,
  UserCheck,
  Plus,
  Trash2,
  HelpCircle,
  Compass,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { apiClient } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface CandidateOption {
  id: string;
  first_name: string;
  last_name: string;
  email: string;
  headline?: string;
}

interface JobOption {
  id: string;
  title: string;
  department?: string;
  required_skills: string[];
}

interface QuestionOption {
  id: string;
  title: string;
  prompt: string;
  question_type: string;
  difficulty: string;
  category: string;
}

interface RoundDraft {
  name: string;
  round_type: string;
  duration_minutes: number;
  difficulty: string;
  instructions: string;
  question_ids: string[];
}

export default function NewInterviewBuilderPage() {
  const { activeWorkspace, user } = useAuthStore();
  const router = useRouter();

  const [currentStep, setCurrentStep] = useState(1);

  // Form state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [interviewType, setInterviewType] = useState('technical');
  const [difficulty, setDifficulty] = useState('senior');
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [timezone, setTimezone] = useState('UTC');

  const [selectedCandidateId, setSelectedCandidateId] = useState('');
  const [selectedJobId, setSelectedJobId] = useState<string | ''>('');

  const [rounds, setRounds] = useState<RoundDraft[]>([
    {
      name: 'Technical Screening & Foundations',
      round_type: 'technical',
      duration_minutes: 30,
      difficulty: 'senior',
      instructions: 'Assess fundamental principles and core algorithms.',
      question_ids: [],
    },
    {
      name: 'System Architecture Deep-Dive',
      round_type: 'system_design',
      duration_minutes: 30,
      difficulty: 'senior',
      instructions: 'Evaluate scalability, database partitioning, and trade-offs.',
      question_ids: [],
    },
  ]);

  const [panelRole, setPanelRole] = useState('lead_interviewer');

  // Options from API
  const [candidates, setCandidates] = useState<CandidateOption[]>([]);
  const [jobs, setJobs] = useState<JobOption[]>([]);
  const [availableQuestions, setAvailableQuestions] = useState<QuestionOption[]>([]);
  const [isLoadingOptions, setIsLoadingOptions] = useState(true);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // Load workspace candidates, jobs, and questions
  useEffect(() => {
    if (!activeWorkspace) return;
    const loadData = async () => {
      setIsLoadingOptions(true);
      try {
        const [candRes, jobsRes, qRes] = await Promise.all([
          apiClient<any>(`/candidates?workspace_id=${activeWorkspace.id}&page_size=50`),
          apiClient<any>(`/jobs?workspace_id=${activeWorkspace.id}&page_size=50`),
          apiClient<any>(`/questions?workspace_id=${activeWorkspace.id}&page_size=50`),
        ]);
        setCandidates(candRes.items || []);
        if (candRes.items?.length > 0) {
          setSelectedCandidateId(candRes.items[0].id);
        }
        setJobs(jobsRes.items || []);
        setAvailableQuestions(qRes.items || []);
      } catch (err: any) {
        console.error('Failed to load builder options', err);
      } finally {
        setIsLoadingOptions(false);
      }
    };
    loadData();
  }, [activeWorkspace]);

  // Round utilities
  const handleAddRound = () => {
    setRounds([
      ...rounds,
      {
        name: `Round ${rounds.length + 1}`,
        round_type: 'coding',
        duration_minutes: 30,
        difficulty: difficulty,
        instructions: '',
        question_ids: [],
      },
    ]);
  };

  const handleRemoveRound = (idx: number) => {
    if (rounds.length <= 1) return;
    setRounds(rounds.filter((_, i) => i !== idx));
  };

  const handleUpdateRound = (idx: number, field: keyof RoundDraft, value: any) => {
    setRounds(
      rounds.map((r, i) => (i === idx ? { ...r, [field]: value } : r))
    );
  };

  const totalRoundMinutes = rounds.reduce((acc, r) => acc + (r.duration_minutes || 0), 0);

  // Validation
  const getValidationIssues = (): string[] => {
    const issues: string[] = [];
    if (!title.trim()) issues.push('Interview title is required.');
    if (!selectedCandidateId) issues.push('A candidate must be selected.');
    if (durationMinutes <= 0) issues.push('Total duration must be greater than 0.');
    if (rounds.length === 0) issues.push('At least one round must be configured.');
    if (totalRoundMinutes > durationMinutes) {
      issues.push(`Sum of round durations (${totalRoundMinutes} mins) exceeds total duration (${durationMinutes} mins).`);
    }
    return issues;
  };

  const issues = getValidationIssues();
  const isConfigurationValid = issues.length === 0;

  // Submit interview
  const handleSubmit = async (markReady = false) => {
    if (!activeWorkspace || !selectedCandidateId || !title.trim()) return;
    setIsSubmitting(true);
    setSubmitError(null);

    try {
      // 1. Create interview
      const itwRes = await apiClient<any>('/interviews', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: activeWorkspace.id,
          candidate_id: selectedCandidateId,
          job_id: selectedJobId || undefined,
          title: title.trim(),
          description: description.trim(),
          interview_type: interviewType,
          difficulty: difficulty,
          duration_minutes: durationMinutes,
          timezone: timezone,
        }),
      });

      const itwId = itwRes.id;

      // 2. Create rounds & assign questions
      for (let i = 0; i < rounds.length; i++) {
        const r = rounds[i];
        const roundRes = await apiClient<any>(`/interviews/${itwId}/rounds`, {
          method: 'POST',
          body: JSON.stringify({
            name: r.name,
            round_type: r.round_type,
            sequence: i + 1,
            duration_minutes: r.duration_minutes,
            difficulty: r.difficulty,
            instructions: r.instructions,
            is_required: true,
          }),
        });

        // Add questions to round
        for (const qId of r.question_ids) {
          await apiClient(`/interviews/${itwId}/rounds/${roundRes.id}/questions`, {
            method: 'POST',
            body: JSON.stringify({ question_id: qId }),
          });
        }
      }

      // 3. Assign creator as lead interviewer
      if (user) {
        await apiClient(`/interviews/${itwId}/participants`, {
          method: 'POST',
          body: JSON.stringify({
            user_id: user.id,
            participant_role: panelRole,
            is_primary: true,
          }),
        });
      }

      // 4. Optionally transition to READY
      if (markReady && isConfigurationValid) {
        await apiClient(`/interviews/${itwId}`, {
          method: 'PATCH',
          body: JSON.stringify({ status: 'ready' }),
        });
      }

      router.push(`/interviews/${itwId}`);
    } catch (err: any) {
      setSubmitError(err.message || 'Failed to create interview configuration');
      setIsSubmitting(false);
    }
  };

  const selectedCandidate = candidates.find((c) => c.id === selectedCandidateId);
  const selectedJob = jobs.find((j) => j.id === selectedJobId);

  const steps = [
    { num: 1, label: 'Basic Info' },
    { num: 2, label: 'Candidate & Job' },
    { num: 3, label: 'Type' },
    { num: 4, label: 'Rounds' },
    { num: 5, label: 'Questions' },
    { num: 6, label: 'Panel' },
    { num: 7, label: 'Review' },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Back button */}
      <div>
        <Link
          href="/interviews"
          className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Cancel & Back to Interviews
        </Link>
      </div>

      {/* Header */}
      <div className="border-b border-zinc-800/80 pb-4">
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Terminal className="h-6 w-6 text-indigo-400" />
          Interview Builder Wizard
        </h1>
        <p className="text-xs text-zinc-400 mt-1">
          Configure rounds, competencies, question sets, and panel members before launching the session.
        </p>
      </div>

      {/* Step Progress Pills */}
      <div className="flex items-center justify-between overflow-x-auto gap-2 pb-2">
        {steps.map((s) => (
          <button
            key={s.num}
            onClick={() => setCurrentStep(s.num)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
              currentStep === s.num
                ? 'bg-primary text-white shadow-md shadow-primary/20'
                : currentStep > s.num
                ? 'bg-zinc-900 border border-zinc-800 text-zinc-300'
                : 'bg-zinc-950 text-zinc-600 border border-zinc-900'
            }`}
          >
            <span className="h-4 w-4 rounded-full bg-black/40 flex items-center justify-center text-[10px]">
              {currentStep > s.num ? '✓' : s.num}
            </span>
            <span>{s.label}</span>
          </button>
        ))}
      </div>

      {/* Error alert */}
      {submitError && (
        <div className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-3 text-xs text-rose-400 flex items-center gap-2">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{submitError}</span>
        </div>
      )}

      {/* STEP 1: BASIC INFORMATION */}
      {currentStep === 1 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
            Step 1: Session Overview & Duration
          </h3>

          <div className="space-y-3 text-xs font-sans">
            <div className="space-y-1">
              <label className="font-semibold text-zinc-300">Interview Title *</label>
              <input
                type="text"
                required
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g. Senior Distributed Systems Loop - Karthik Rao"
                className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
              />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-1">
                <label className="font-semibold text-zinc-300">Total Duration (Minutes) *</label>
                <input
                  type="number"
                  min="15"
                  max="480"
                  step="15"
                  value={durationMinutes}
                  onChange={(e) => setDurationMinutes(parseInt(e.target.value, 10) || 60)}
                  className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-zinc-300">Seniority Level</label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none capitalize"
                >
                  <option value="entry">Entry Level</option>
                  <option value="mid">Mid Level</option>
                  <option value="senior">Senior Engineer</option>
                  <option value="lead">Staff / Lead Engineer</option>
                  <option value="principal">Principal Engineer</option>
                </select>
              </div>

              <div className="space-y-1">
                <label className="font-semibold text-zinc-300">Timezone</label>
                <input
                  type="text"
                  value={timezone}
                  onChange={(e) => setTimezone(e.target.value)}
                  placeholder="UTC or America/Los_Angeles"
                  className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="font-semibold text-zinc-300">Session Description & Objectives</label>
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="High-level objectives for this candidate panel..."
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 p-2.5 text-xs text-white focus:border-primary focus:outline-none"
              />
            </div>
          </div>
        </Card>
      )}

      {/* STEP 2: CANDIDATE & JOB */}
      {currentStep === 2 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
            Step 2: Candidate & Job Requisition Association
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            {/* Candidate selection */}
            <div className="space-y-2">
              <label className="font-semibold text-zinc-300">Select Candidate *</label>
              {candidates.length === 0 ? (
                <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 text-center text-zinc-500">
                  No candidates found in this workspace.{' '}
                  <Link href="/candidates" className="text-primary underline">
                    Add candidate first
                  </Link>
                </div>
              ) : (
                <select
                  value={selectedCandidateId}
                  onChange={(e) => setSelectedCandidateId(e.target.value)}
                  className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                >
                  {candidates.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.first_name} {c.last_name} ({c.email})
                    </option>
                  ))}
                </select>
              )}

              {selectedCandidate && (
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1">
                  <p className="font-semibold text-white">
                    {selectedCandidate.first_name} {selectedCandidate.last_name}
                  </p>
                  <p className="text-[11px] text-zinc-400">{selectedCandidate.headline || selectedCandidate.email}</p>
                </div>
              )}
            </div>

            {/* Job selection */}
            <div className="space-y-2">
              <label className="font-semibold text-zinc-300">Associated Job Requisition (Optional)</label>
              <select
                value={selectedJobId}
                onChange={(e) => setSelectedJobId(e.target.value)}
                className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
              >
                <option value="">None (Independent Technical Screen)</option>
                {jobs.map((j) => (
                  <option key={j.id} value={j.id}>
                    {j.title} {j.department ? `(${j.department})` : ''}
                  </option>
                ))}
              </select>

              {selectedJob && (
                <div className="p-3 rounded-lg bg-zinc-950 border border-zinc-800/80 space-y-1.5">
                  <p className="font-semibold text-white">{selectedJob.title}</p>
                  <div className="flex flex-wrap gap-1">
                    {selectedJob.required_skills?.slice(0, 3).map((s) => (
                      <span key={s} className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-900 text-zinc-300">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      {/* STEP 3: INTERVIEW TYPE */}
      {currentStep === 3 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
            Step 3: Primary Interview Format
          </h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {[
              {
                id: 'technical',
                title: 'Technical Screening',
                desc: 'Assess core engineering concepts, API protocols, and computational fundamentals.',
                icon: Terminal,
              },
              {
                id: 'coding',
                title: 'Live Coding / DSA',
                desc: 'Algorithms, data structures, and practical code implementation.',
                icon: Code,
              },
              {
                id: 'system_design',
                title: 'System Design',
                desc: 'Distributed architectures, caching, DB partitioning, and scalability trade-offs.',
                icon: Cpu,
              },
              {
                id: 'behavioral',
                title: 'Behavioral & Leadership',
                desc: 'Conflict resolution, ownership, cross-functional collaboration, and cultural fit.',
                icon: UserCheck,
              },
              {
                id: 'mixed',
                title: 'Mixed Full Loop',
                desc: 'Comprehensive multi-round technical assessment covering coding and design.',
                icon: Layers,
              },
              {
                id: 'custom',
                title: 'Custom Evaluation',
                desc: 'Configurable domain-specific assessment designed by your engineering team.',
                icon: Compass,
              },
            ].map((t) => (
              <div
                key={t.id}
                onClick={() => setInterviewType(t.id)}
                className={`p-4 rounded-xl border transition-all cursor-pointer space-y-2 ${
                  interviewType === t.id
                    ? 'border-primary bg-primary/10 shadow-md shadow-primary/10'
                    : 'border-zinc-800 bg-zinc-950/80 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <t.icon className={`h-5 w-5 ${interviewType === t.id ? 'text-primary' : 'text-zinc-400'}`} />
                  {interviewType === t.id && <Check className="h-4 w-4 text-primary" />}
                </div>
                <h4 className="text-sm font-bold text-white">{t.title}</h4>
                <p className="text-[11px] text-zinc-400 leading-relaxed">{t.desc}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* STEP 4: ROUND BUILDER */}
      {currentStep === 4 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
                Step 4: Ordered Interview Rounds
              </h3>
              <p className="text-xs text-zinc-400">
                Rounds duration: <strong className={totalRoundMinutes > durationMinutes ? 'text-rose-400' : 'text-emerald-400'}>{totalRoundMinutes} mins</strong> / {durationMinutes} mins total
              </p>
            </div>
            <Button size="sm" onClick={handleAddRound} className="text-xs font-semibold">
              <Plus className="h-3.5 w-3.5 mr-1" />
              Add Round
            </Button>
          </div>

          <div className="space-y-3">
            {rounds.map((round, idx) => (
              <Card key={idx} className="bg-[#0e0f15] border-zinc-800 p-4 space-y-3">
                <div className="flex items-center justify-between border-b border-zinc-800/60 pb-2">
                  <span className="text-xs font-bold text-indigo-400 uppercase tracking-wider">
                    Round {idx + 1}
                  </span>
                  {rounds.length > 1 && (
                    <button
                      onClick={() => handleRemoveRound(idx)}
                      className="text-zinc-500 hover:text-rose-400 text-xs transition-colors"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="space-y-1 sm:col-span-2">
                    <label className="text-zinc-400">Round Title</label>
                    <input
                      type="text"
                      value={round.name}
                      onChange={(e) => handleUpdateRound(idx, 'name', e.target.value)}
                      className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                    />
                  </div>

                  <div className="space-y-1">
                    <label className="text-zinc-400">Duration (mins)</label>
                    <input
                      type="number"
                      min="5"
                      max="180"
                      step="5"
                      value={round.duration_minutes}
                      onChange={(e) => handleUpdateRound(idx, 'duration_minutes', parseInt(e.target.value, 10) || 15)}
                      className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  <div className="space-y-1">
                    <label className="text-zinc-400">Round Type</label>
                    <select
                      value={round.round_type}
                      onChange={(e) => handleUpdateRound(idx, 'round_type', e.target.value)}
                      className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none capitalize"
                    >
                      <option value="technical">Technical</option>
                      <option value="coding">Live Coding</option>
                      <option value="system_design">System Design</option>
                      <option value="behavioral">Behavioral</option>
                      <option value="screening">Screening</option>
                    </select>
                  </div>

                  <div className="space-y-1">
                    <label className="text-zinc-400">Difficulty</label>
                    <select
                      value={round.difficulty}
                      onChange={(e) => handleUpdateRound(idx, 'difficulty', e.target.value)}
                      className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none capitalize"
                    >
                      <option value="entry">Entry</option>
                      <option value="mid">Mid</option>
                      <option value="senior">Senior</option>
                      <option value="lead">Lead</option>
                    </select>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </Card>
      )}

      {/* STEP 5: QUESTIONS PICKER */}
      {currentStep === 5 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
              Step 5: Assign Questions to Rounds
            </h3>
            <Link href="/interviews/questions" target="_blank" className="text-xs text-primary underline">
              Open Question Bank
            </Link>
          </div>

          <div className="space-y-4 text-xs">
            {rounds.map((round, rIdx) => (
              <div key={rIdx} className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-4 space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-white">
                    Round {rIdx + 1}: {round.name} ({round.round_type})
                  </span>
                  <span className="text-zinc-400 text-[11px]">{round.question_ids.length} questions attached</span>
                </div>

                {/* Available questions dropdown */}
                <select
                  onChange={(e) => {
                    if (e.target.value && !round.question_ids.includes(e.target.value)) {
                      handleUpdateRound(rIdx, 'question_ids', [...round.question_ids, e.target.value]);
                    }
                  }}
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-900 px-2 text-xs text-white focus:border-primary focus:outline-none"
                  defaultValue=""
                >
                  <option value="" disabled>
                    + Attach question from Question Bank...
                  </option>
                  {availableQuestions.map((q) => (
                    <option key={q.id} value={q.id}>
                      [{q.question_type.toUpperCase()}] {q.title} ({q.difficulty})
                    </option>
                  ))}
                </select>

                {/* Assigned questions badges */}
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {round.question_ids.map((qId) => {
                    const qObj = availableQuestions.find((q) => q.id === qId);
                    return (
                      <span
                        key={qId}
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-200 text-[11px]"
                      >
                        {qObj?.title || qId}
                        <button
                          onClick={() =>
                            handleUpdateRound(
                              rIdx,
                              'question_ids',
                              round.question_ids.filter((id) => id !== qId)
                            )
                          }
                          className="text-zinc-500 hover:text-rose-400"
                        >
                          ✕
                        </button>
                      </span>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* STEP 6: PANEL MEMBERS */}
      {currentStep === 6 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
            Step 6: Interview Panel Members
          </h3>

          <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-950/80 space-y-3 text-xs">
            <p className="text-zinc-300">
              You will automatically be assigned as a panel member for this session:
            </p>
            <div className="flex items-center justify-between p-3 rounded-lg bg-zinc-900/60 border border-zinc-800">
              <div>
                <p className="font-bold text-white">{user?.first_name} {user?.last_name} (You)</p>
                <p className="text-[11px] text-zinc-400">{user?.email}</p>
              </div>

              <select
                value={panelRole}
                onChange={(e) => setPanelRole(e.target.value)}
                className="h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none capitalize"
              >
                <option value="lead_interviewer">Lead Interviewer</option>
                <option value="interviewer">Interviewer</option>
                <option value="observer">Observer</option>
                <option value="recruiter">Recruiter</option>
              </select>
            </div>
          </div>
        </Card>
      )}

      {/* STEP 7: REVIEW & READINESS */}
      {currentStep === 7 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-4">
          <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
            Step 7: Final Review & Readiness Checklist
          </h3>

          {/* Readiness banner */}
          {isConfigurationValid ? (
            <div className="p-4 rounded-xl border border-emerald-500/30 bg-emerald-950/20 flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
              <div>
                <p className="text-xs font-bold text-white">All Readiness Criteria Met</p>
                <p className="text-[11px] text-emerald-300">
                  This interview is fully configured and eligible to transition to READY status.
                </p>
              </div>
            </div>
          ) : (
            <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-950/20 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-amber-300">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>Configuration Incomplete ({issues.length} blocking issues)</span>
              </div>
              <ul className="text-[11px] text-amber-200/90 list-disc list-inside space-y-0.5">
                {issues.map((iss, i) => (
                  <li key={i}>{iss}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Summary Details */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-3.5 rounded-lg border border-zinc-800 bg-zinc-950/80 space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-zinc-500">Session Overview</span>
              <p className="font-bold text-white text-sm">{title || 'Untitled Session'}</p>
              <p className="text-zinc-400">Duration: {durationMinutes} mins • {difficulty} level</p>
              <p className="text-zinc-400 capitalize">Format: {interviewType.replace('_', ' ')}</p>
            </div>

            <div className="p-3.5 rounded-lg border border-zinc-800 bg-zinc-950/80 space-y-1.5">
              <span className="text-[10px] uppercase font-bold text-zinc-500">Candidate & Requisition</span>
              <p className="font-bold text-white text-sm">
                {selectedCandidate ? `${selectedCandidate.first_name} ${selectedCandidate.last_name}` : 'None'}
              </p>
              <p className="text-zinc-400">Role: {selectedJob ? selectedJob.title : 'General Technical Screen'}</p>
              <p className="text-zinc-400">Rounds: {rounds.length} stages ({totalRoundMinutes} mins)</p>
            </div>
          </div>
        </Card>
      )}

      {/* Navigation Buttons */}
      <div className="flex items-center justify-between pt-4 border-t border-zinc-800/80">
        <Button
          variant="outline"
          size="sm"
          disabled={currentStep === 1}
          onClick={() => setCurrentStep(currentStep - 1)}
          className="text-xs border-zinc-800 text-zinc-300"
        >
          <ArrowLeft className="h-3.5 w-3.5 mr-1" />
          Previous Step
        </Button>

        <div className="flex items-center gap-2">
          {currentStep < 7 ? (
            <Button
              size="sm"
              onClick={() => setCurrentStep(currentStep + 1)}
              className="text-xs font-semibold"
            >
              Next Step
              <ArrowRight className="h-3.5 w-3.5 ml-1" />
            </Button>
          ) : (
            <>
              <Button
                variant="outline"
                size="sm"
                disabled={isSubmitting}
                onClick={() => handleSubmit(false)}
                className="text-xs border-zinc-800 text-zinc-300"
              >
                Save as Draft
              </Button>
              <Button
                size="sm"
                disabled={isSubmitting || !isConfigurationValid}
                onClick={() => handleSubmit(true)}
                className="text-xs font-semibold shadow-lg shadow-primary/20"
              >
                {isSubmitting ? 'Finalizing...' : 'Finalize & Mark Ready'}
              </Button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
