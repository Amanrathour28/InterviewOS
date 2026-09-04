/**
 * Evaluation Workspace UI — Phase 15.
 * 
 * Provides an evidence-first, explainable evaluation workspace where:
 * 1. Overall scores are mathematically computed and displayed with policy recommendations.
 * 2. Every competency score shows observed facts, inferences, and clickable evidence links.
 * 3. Interviewers can review, override scores with audited rationale, approve, and finalize.
 * 4. Evidence Explorer drawer allows deep inspection of transcripts, coding results, whiteboard states, and resume claims.
 */

'use client';

import React, { useState, useEffect } from 'react';
import { useEvaluationStore } from '@/lib/stores/use-evaluation-store';
import {
  EvaluationCompetencyScoreData,
  EvaluationEvidenceData,
  HiringRecommendationType,
} from '@interviewos/types';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

interface EvaluationWorkspaceProps {
  interviewId: string;
}

export function EvaluationWorkspace({ interviewId }: EvaluationWorkspaceProps) {
  const {
    evaluation,
    evidenceItems,
    isLoading,
    isGenerating,
    error,
    selectedEvidenceId,
    isEvidenceDrawerOpen,
    activeEvidenceFilter,
    fetchEvaluation,
    generateEvaluation,
    fetchEvidence,
    overrideScore,
    approveEvaluation,
    finalizeEvaluation,
    setSelectedEvidenceId,
    setIsEvidenceDrawerOpen,
    setActiveEvidenceFilter,
  } = useEvaluationStore();

  const [overrideModalComp, setOverrideModalComp] = useState<EvaluationCompetencyScoreData | null>(null);
  const [overrideLevel, setOverrideLevel] = useState<number>(3);
  const [overrideReason, setOverrideReason] = useState<string>('');

  useEffect(() => {
    if (interviewId) {
      fetchEvaluation(interviewId);
      fetchEvidence(interviewId);
    }
  }, [interviewId, fetchEvaluation, fetchEvidence]);

  const handleOpenOverride = (comp: EvaluationCompetencyScoreData) => {
    setOverrideModalComp(comp);
    setOverrideLevel(comp.rubric_level);
    setOverrideReason(comp.override_reason || '');
  };

  const handleSaveOverride = async () => {
    if (!overrideModalComp || !overrideReason.trim()) return;
    await overrideScore(
      interviewId,
      overrideModalComp.id,
      overrideLevel,
      overrideReason.trim()
    );
    setOverrideModalComp(null);
  };

  const getRecommendationBadge = (rec: HiringRecommendationType) => {
    switch (rec) {
      case 'strong_hire':
        return <Badge className="bg-emerald-600 text-white font-semibold">Strong Hire</Badge>;
      case 'hire':
        return <Badge className="bg-green-600 text-white font-semibold">Hire</Badge>;
      case 'lean_hire':
        return <Badge className="bg-teal-600 text-white font-semibold">Lean Hire</Badge>;
      case 'lean_no_hire':
        return <Badge className="bg-amber-600 text-white font-semibold">Lean No Hire</Badge>;
      case 'no_hire':
        return <Badge className="bg-rose-600 text-white font-semibold">No Hire</Badge>;
      default:
        return <Badge variant="outline">Insufficient Evidence</Badge>;
    }
  };

  const filteredEvidence = evidenceItems.filter((item) => {
    if (activeEvidenceFilter === 'all') return true;
    return item.source_type === activeEvidenceFilter;
  });

  const selectedEvidence = evidenceItems.find((e) => e.id === selectedEvidenceId);

  return (
    <div className="flex flex-col gap-6 max-w-7xl mx-auto p-6">
      {/* Header Banner */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-4">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight text-white">Interview Evaluation</h1>
            {evaluation?.is_locked && (
              <Badge variant="outline" className="text-amber-400 border-amber-500/30">
                🔒 Finalized & Locked (v{evaluation.version})
              </Badge>
            )}
            {!evaluation?.is_locked && evaluation?.status && (
              <Badge variant="outline" className="capitalize">
                Status: {evaluation.status.replace('_', ' ')}
              </Badge>
            )}
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Evidence-grounded scoring & AI synthesis. Every claim links to verified interview artifacts.
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center gap-3">
          {!evaluation?.is_locked && (
            <>
              <Button
                variant="outline"
                size="sm"
                onClick={() => generateEvaluation(interviewId)}
                disabled={isGenerating}
              >
                {isGenerating ? 'Synthesizing AI Evaluation...' : 'Generate AI Evaluation'}
              </Button>

              {evaluation?.status === 'draft' && (
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => approveEvaluation(interviewId)}
                  disabled={isLoading}
                >
                  Approve Evaluation
                </Button>
              )}

              <Button
                variant="primary"
                size="sm"
                className="bg-emerald-600 hover:bg-emerald-500"
                onClick={() => finalizeEvaluation(interviewId)}
                disabled={isLoading}
              >
                Finalize & Lock
              </Button>
            </>
          )}
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-900/40 border border-red-500/50 rounded-lg text-sm text-red-200">
          {error}
        </div>
      )}

      {/* Top Level Score Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-5 bg-zinc-900/70 border-zinc-800">
          <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Overall Score</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-3xl font-extrabold text-white">{evaluation?.overall_score || 0}</span>
            <span className="text-xs text-zinc-500">/ 100</span>
          </div>
          <p className="text-xs text-zinc-400 mt-1">
            Rubric Level: <strong className="text-zinc-200">{evaluation?.overall_rubric_level || 0} / 5.0</strong>
          </p>
        </Card>

        <Card className="p-5 bg-zinc-900/70 border-zinc-800">
          <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Hiring Policy</span>
          <div className="mt-2">
            {evaluation?.recommendation && getRecommendationBadge(evaluation.recommendation)}
          </div>
          <p className="text-xs text-zinc-500 mt-2">Deterministic threshold formula</p>
        </Card>

        <Card className="p-5 bg-zinc-900/70 border-zinc-800">
          <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Confidence Level</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-3xl font-extrabold text-white">
              {Math.round((evaluation?.confidence || 0) * 100)}%
            </span>
          </div>
          <p className="text-xs text-zinc-500 mt-1">Based on evidence density & consistency</p>
        </Card>

        <Card className="p-5 bg-zinc-900/70 border-zinc-800">
          <span className="text-xs font-medium text-zinc-400 uppercase tracking-wider">Evidence Items</span>
          <div className="flex items-baseline gap-2 mt-2">
            <span className="text-3xl font-extrabold text-white">{evidenceItems.length}</span>
            <span className="text-xs text-zinc-500">artifacts</span>
          </div>
          <button
            type="button"
            className="p-0 h-auto text-xs text-indigo-400 mt-1 hover:underline text-left"
            onClick={() => setIsEvidenceDrawerOpen(true)}
          >
            Explore Evidence Drawer &rarr;
          </button>
        </Card>
      </div>

      {/* Summary Narrative */}
      {evaluation?.summary && (
        <Card className="p-5 bg-zinc-900/50 border-zinc-800">
          <h3 className="text-sm font-semibold text-zinc-200 mb-2">Executive Summary</h3>
          <p className="text-sm text-zinc-300 leading-relaxed">{evaluation.summary}</p>
        </Card>
      )}

      {/* Competency Score Matrix */}
      <div className="flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-white">Competency Evaluation Matrix</h2>
          <span className="text-xs text-zinc-400">Click any evidence tag to inspect raw artifacts</span>
        </div>

        <div className="grid grid-cols-1 gap-4">
          {evaluation?.competency_scores?.map((comp) => (
            <Card key={comp.id} className="p-5 bg-zinc-900/70 border-zinc-800 hover:border-zinc-700 transition">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-semibold text-white">{comp.competency_name}</h3>
                    {comp.is_overridden && (
                      <Badge variant="outline" className="text-xs border-amber-500/40 text-amber-300">
                        Edited by Reviewer (was {comp.original_ai_rubric_level} / 5)
                      </Badge>
                    )}
                  </div>
                  <p className="text-sm text-zinc-300 mt-1">{comp.rationale}</p>
                </div>

                <div className="flex items-center gap-4">
                  <div className="text-right">
                    <div className="text-lg font-bold text-white">{comp.rubric_level} / 5.0</div>
                    <span className="text-xs text-zinc-500">{comp.calculated_score} pts (wt: {comp.weight})</span>
                  </div>

                  {!evaluation.is_locked && (
                    <Button variant="outline" size="sm" onClick={() => handleOpenOverride(comp)}>
                      Override
                    </Button>
                  )}
                </div>
              </div>

              {/* Observed Facts & Inferences */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4 pt-3 border-t border-zinc-800/80 text-xs">
                <div>
                  <span className="font-semibold text-zinc-400">Observed Facts:</span>
                  <ul className="list-disc list-inside mt-1 space-y-1 text-zinc-300">
                    {comp.observed_facts.map((fact, i) => (
                      <li key={i}>{fact}</li>
                    ))}
                  </ul>
                </div>

                <div>
                  <span className="font-semibold text-zinc-400">Supporting Evidence Citations:</span>
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {comp.evidence_ids && comp.evidence_ids.length > 0 ? (
                      comp.evidence_ids.map((eid) => (
                        <button
                          key={eid}
                          onClick={() => setSelectedEvidenceId(eid)}
                          className="px-2 py-0.5 rounded bg-indigo-950/60 hover:bg-indigo-900/80 text-indigo-300 border border-indigo-700/50 text-xs font-mono transition"
                        >
                          ref:{eid.slice(0, 8)}
                        </button>
                      ))
                    ) : (
                      <span className="text-zinc-500 italic">No direct citations linked</span>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>

      {/* Strengths & Development Areas */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-5 bg-zinc-900/50 border-zinc-800">
          <h3 className="text-sm font-semibold text-emerald-400 flex items-center gap-2 mb-3">
            <span>✓</span> Key Strengths
          </h3>
          <ul className="space-y-2.5 text-sm text-zinc-300">
            {evaluation?.strengths?.map((item, idx) => (
              <li key={idx} className="flex items-start justify-between gap-2">
                <span>• {item.claim}</span>
                {item.evidence_ids && item.evidence_ids.length > 0 && (
                  <button
                    onClick={() => setSelectedEvidenceId(item.evidence_ids[0])}
                    className="text-xs text-indigo-400 hover:underline shrink-0"
                  >
                    [cite]
                  </button>
                )}
              </li>
            ))}
          </ul>
        </Card>

        <Card className="p-5 bg-zinc-900/50 border-zinc-800">
          <h3 className="text-sm font-semibold text-amber-400 flex items-center gap-2 mb-3">
            <span>⚠</span> Development Areas
          </h3>
          <ul className="space-y-2.5 text-sm text-zinc-300">
            {evaluation?.development_areas?.map((item, idx) => (
              <li key={idx} className="flex items-start justify-between gap-2">
                <span>• {item.claim}</span>
                {item.evidence_ids && item.evidence_ids.length > 0 && (
                  <button
                    onClick={() => setSelectedEvidenceId(item.evidence_ids[0])}
                    className="text-xs text-indigo-400 hover:underline shrink-0"
                  >
                    [cite]
                  </button>
                )}
              </li>
            ))}
          </ul>
        </Card>
      </div>

      {/* Contradiction Alerts if any */}
      {evaluation?.contradictions && evaluation.contradictions.length > 0 && (
        <Card className="p-5 bg-amber-950/20 border-amber-600/40">
          <h3 className="text-sm font-semibold text-amber-300 mb-3 flex items-center gap-2">
            <span>⚡</span> Detected Contradictions & Evidence Inconsistencies
          </h3>
          <div className="space-y-3 text-xs">
            {evaluation.contradictions.map((contra) => (
              <div key={contra.id} className="p-3 bg-zinc-900/80 rounded border border-amber-800/40">
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="outline" className="text-xs uppercase border-amber-600/50 text-amber-400">
                    {contra.severity} Severity
                  </Badge>
                  <span className="font-semibold text-zinc-200">{contra.type}</span>
                </div>
                <p className="text-zinc-300">{contra.description}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Score Override Dialog */}
      {overrideModalComp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6 max-w-md w-full shadow-2xl">
            <h3 className="text-lg font-bold text-white mb-1">Override Competency Score</h3>
            <p className="text-xs text-zinc-400 mb-4">
              Competency: <span className="text-zinc-200 font-semibold">{overrideModalComp.competency_name}</span>
            </p>

            <div className="space-y-4">
              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Rubric Level (1.0 = Unsatisfactory, 5.0 = Exemplary)
                </label>
                <input
                  type="number"
                  min="1"
                  max="5"
                  step="0.5"
                  value={overrideLevel}
                  onChange={(e) => setOverrideLevel(parseFloat(e.target.value))}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="text-xs font-medium text-zinc-300 block mb-1">
                  Mandatory Reviewer Rationale
                </label>
                <textarea
                  rows={3}
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Explain why the AI-derived score is being adjusted..."
                  className="w-full bg-zinc-950 border border-zinc-800 rounded px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 mt-6">
              <Button variant="outline" size="sm" onClick={() => setOverrideModalComp(null)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleSaveOverride}
                disabled={!overrideReason.trim()}
                className="bg-indigo-600 hover:bg-indigo-500"
              >
                Save Audited Override
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Evidence Explorer Drawer */}
      {isEvidenceDrawerOpen && (
        <div className="fixed inset-y-0 right-0 z-50 w-full max-w-lg bg-zinc-950 border-l border-zinc-800 shadow-2xl flex flex-col p-6 overflow-y-auto">
          <div className="flex items-center justify-between pb-4 border-b border-zinc-800">
            <div>
              <h3 className="text-lg font-bold text-white">Evidence Explorer</h3>
              <p className="text-xs text-zinc-400">Raw verifiable artifacts from the interview session</p>
            </div>
            <button
              onClick={() => setIsEvidenceDrawerOpen(false)}
              className="text-zinc-400 hover:text-white text-lg font-bold p-1"
            >
              ✕
            </button>
          </div>

          {/* Filter Pills */}
          <div className="flex flex-wrap gap-1.5 py-4 border-b border-zinc-800/80">
            {['all', 'transcript', 'code_execution', 'whiteboard', 'resume_claim', 'interviewer_note'].map(
              (f) => (
                <button
                  key={f}
                  onClick={() => setActiveEvidenceFilter(f)}
                  className={`px-2.5 py-1 rounded text-xs capitalize font-medium transition ${
                    activeEvidenceFilter === f
                      ? 'bg-indigo-600 text-white'
                      : 'bg-zinc-900 text-zinc-400 hover:text-white'
                  }`}
                >
                  {f.replace('_', ' ')}
                </button>
              )
            )}
          </div>

          {/* Evidence List */}
          <div className="space-y-3 mt-4 flex-1">
            {selectedEvidence && (
              <div className="p-4 bg-indigo-950/40 border border-indigo-700/60 rounded-lg mb-4">
                <div className="flex items-center justify-between mb-1">
                  <Badge variant="outline" className="text-xs uppercase border-indigo-500/50 text-indigo-300">
                    Selected Citation ({selectedEvidence.source_type})
                  </Badge>
                  <span className="text-xs font-mono text-zinc-400">{selectedEvidence.id.slice(0, 8)}</span>
                </div>
                <p className="text-sm text-zinc-200 mt-2">{selectedEvidence.content}</p>
              </div>
            )}

            {filteredEvidence.map((ev) => (
              <div
                key={ev.id}
                className={`p-3.5 rounded-lg border transition ${
                  selectedEvidenceId === ev.id
                    ? 'bg-zinc-900 border-indigo-500'
                    : 'bg-zinc-900/50 border-zinc-800/80 hover:border-zinc-700'
                }`}
              >
                <div className="flex items-center justify-between mb-1 text-xs">
                  <span className="font-semibold uppercase tracking-wider text-indigo-400">
                    {ev.source_type.replace('_', ' ')}
                  </span>
                  <span className="font-mono text-zinc-500">ref:{ev.id.slice(0, 8)}</span>
                </div>
                <p className="text-xs text-zinc-300 mt-1 line-clamp-4">{ev.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
