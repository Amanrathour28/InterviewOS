'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Layers,
  Sparkles,
  Clock,
  Shield,
  CheckCircle2,
  AlertCircle,
  Plus,
  Trash2,
  ArrowRight,
  X,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

interface InterviewBlueprintReviewProps {
  blueprint: any;
  interviewId?: string;
  onBlueprintApplied?: () => void;
}

export function InterviewBlueprintReview({ blueprint: initialBlueprint, interviewId, onBlueprintApplied }: InterviewBlueprintReviewProps) {
  const [blueprint, setBlueprint] = useState(initialBlueprint);
  const [isApproving, setIsApproving] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleApprove = async () => {
    try {
      setIsApproving(true);
      setErrorMsg(null);
      const updated = await apiClient<any>(`/intelligence/interviews/blueprints/${blueprint.id}/approve`, {
        method: 'POST',
      });
      setBlueprint(updated);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to approve blueprint');
    } finally {
      setIsApproving(false);
    }
  };

  const handleApply = async () => {
    try {
      setIsApplying(true);
      setErrorMsg(null);
      await apiClient<any>(`/intelligence/interviews/blueprints/${blueprint.id}/apply?interview_id=${interviewId || blueprint.interview_id}`, {
        method: 'POST',
      });
      if (onBlueprintApplied) {
        onBlueprintApplied();
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to apply blueprint');
    } finally {
      setIsApplying(false);
    }
  };

  if (!blueprint) return null;

  return (
    <div className="space-y-6">
      {/* Header & Status */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-900/80 border border-slate-800 rounded-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="border-indigo-500/40 text-indigo-400 text-[10px] uppercase font-mono">
              AI Recommendation · Advisory Draft
            </Badge>
            <Badge
              className={`text-[10px] uppercase px-1.5 py-0 ${
                blueprint.status === 'approved'
                  ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/40'
                  : blueprint.status === 'applied'
                  ? 'bg-violet-950 text-violet-400 border border-violet-800/40'
                  : 'bg-amber-950 text-amber-400 border border-amber-800/40'
              }`}
            >
              {blueprint.status}
            </Badge>
          </div>
          <h3 className="text-base font-bold text-white">{blueprint.title}</h3>
          <p className="text-xs text-slate-400">
            Total Duration: {blueprint.total_duration_minutes} min · Seniority: {blueprint.target_seniority}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {blueprint.status !== 'approved' && blueprint.status !== 'applied' && (
            <Button
              size="sm"
              onClick={handleApprove}
              disabled={isApproving}
              className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs h-8 flex items-center gap-1.5"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {isApproving ? 'Approving...' : 'Approve Blueprint'}
            </Button>
          )}

          {blueprint.status === 'approved' && (
            <Button
              size="sm"
              onClick={handleApply}
              disabled={isApplying}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-8 flex items-center gap-1.5"
            >
              <ArrowRight className="w-3.5 h-3.5" />
              {isApplying ? 'Applying...' : 'Apply to Interview'}
            </Button>
          )}
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 bg-rose-950/40 border border-rose-800/60 rounded-lg text-rose-300 text-xs flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Blueprint Rounds Timeline */}
      <div className="space-y-3">
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
          Recommended Interview Rounds ({blueprint.rounds?.length || 0})
        </h4>

        <div className="space-y-3">
          {blueprint.rounds?.map((round: any, idx: number) => (
            <div
              key={idx}
              className="p-4 bg-slate-950/60 rounded-xl border border-slate-800 space-y-3"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-2.5">
                  <div className="w-6 h-6 rounded-full bg-violet-950/60 border border-violet-700/50 flex items-center justify-center text-xs font-bold text-violet-300">
                    {round.sequence}
                  </div>
                  <div>
                    <div className="text-xs font-bold text-white">{round.name}</div>
                    <div className="text-[10px] text-slate-400 capitalize">
                      {round.round_type} Round · {round.duration_minutes} minutes · {round.difficulty} difficulty
                    </div>
                  </div>
                </div>

                <Badge variant="outline" className="border-slate-800 text-slate-300 text-[10px] px-2 py-0.5">
                  Weight: {round.scoring_weight}x
                </Badge>
              </div>

              {/* Objectives & Competencies */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1 text-xs">
                <div>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Evaluation Objectives
                  </span>
                  <ul className="text-slate-300 space-y-1 list-disc list-inside">
                    {round.objectives?.map((obj: string, oIdx: number) => (
                      <li key={oIdx} className="text-[11px] text-slate-300 leading-tight">
                        {obj}
                      </li>
                    ))}
                  </ul>
                </div>

                <div>
                  <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block mb-1">
                    Tested Competencies
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {round.competencies?.map((comp: string, cIdx: number) => (
                      <Badge key={cIdx} variant="outline" className="border-slate-700 text-slate-300 text-[10px] px-1.5 py-0">
                        {comp}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

interface InterviewBlueprintModalProps {
  isOpen: boolean;
  onClose: () => void;
  candidateId?: string;
  jobId?: string;
  interviewId?: string;
  blueprint?: any;
  onApplied?: () => void;
}

export function InterviewBlueprintModal({
  isOpen,
  onClose,
  candidateId,
  jobId,
  interviewId,
  blueprint: providedBlueprint,
  onApplied,
}: InterviewBlueprintModalProps) {
  const [blueprint, setBlueprint] = useState<any>(providedBlueprint || null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const generateBlueprint = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      const data = await apiClient<any>('/intelligence/interviews/blueprints/generate', {
        method: 'POST',
        body: JSON.stringify({
          candidate_id: candidateId || undefined,
          job_id: jobId || undefined,
          interview_id: interviewId || undefined,
          custom_requirements: ['Standard engineering interview progression'],
        }),
      });
      setBlueprint(data);
    } catch (err: any) {
      setError(err.message || 'Failed to generate interview blueprint');
    } finally {
      setIsLoading(false);
    }
  }, [candidateId, jobId, interviewId]);

  useEffect(() => {
    if (providedBlueprint) {
      setBlueprint(providedBlueprint);
      return;
    }

    if (isOpen && (candidateId || jobId || interviewId)) {
      generateBlueprint();
    }
  }, [isOpen, candidateId, jobId, interviewId, providedBlueprint, generateBlueprint]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="w-full max-w-4xl max-h-[90vh] overflow-y-auto rounded-2xl border border-slate-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-indigo-400" />
            <h3 className="text-base font-bold text-white">Interview Blueprint Planner</h3>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors p-1"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {isLoading ? (
          <div className="p-12 text-center text-xs text-slate-400 space-y-3">
            <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
            <p>Synthesizing candidate profile, job requirements, and multi-round blueprint...</p>
          </div>
        ) : error ? (
          <div className="p-4 bg-rose-950/40 border border-rose-800/60 rounded-lg text-rose-300 text-xs space-y-2">
            <div className="flex items-center gap-2 font-bold">
              <AlertCircle className="w-4 h-4" />
              <span>Error Generating Blueprint</span>
            </div>
            <p>{error}</p>
            <Button size="sm" onClick={generateBlueprint} className="text-xs mt-2">
              Retry
            </Button>
          </div>
        ) : blueprint ? (
          <InterviewBlueprintReview
            blueprint={blueprint}
            interviewId={interviewId}
            onBlueprintApplied={() => {
              if (onApplied) onApplied();
              onClose();
            }}
          />
        ) : (
          <div className="p-8 text-center text-xs text-slate-500">
            No blueprint available. Click below to generate.
            <div className="mt-3">
              <Button size="sm" onClick={generateBlueprint}>
                Generate Blueprint
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
