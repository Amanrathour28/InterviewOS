'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  HelpCircle,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
  Layers,
  Clock,
  Shield,
  Table,
  ChevronRight,
  TrendingUp,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

interface QuestionPlanWorkspaceProps {
  interviewId: string;
  candidateId?: string;
  workspaceId?: string;
  jobId?: string;
}

export function QuestionPlanWorkspace({ interviewId, candidateId, workspaceId, jobId }: QuestionPlanWorkspaceProps) {
  const [questionPlan, setQuestionPlan] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<'plan' | 'coverage'>('plan');

  const generatePlan = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiClient<any>('/intelligence/interviews/question-plans/generate', {
        method: 'POST',
        body: JSON.stringify({
          interview_id: interviewId,
          workspace_id: workspaceId || undefined,
          candidate_id: candidateId || undefined,
          job_id: jobId || undefined,
        }),
      });
      setQuestionPlan(data);
    } catch (err) {
      console.error('Failed to generate question plan:', err);
    } finally {
      setIsLoading(false);
    }
  }, [interviewId, candidateId, workspaceId, jobId]);

  useEffect(() => {
    if (interviewId) {
      generatePlan();
    }
  }, [interviewId, generatePlan]);

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-400">Building evidence-grounded question plan & coverage matrix...</div>;
  }

  if (!questionPlan) {
    return (
      <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-800 rounded-lg">
        No question plan generated yet.
        <div className="mt-3">
          <Button size="sm" onClick={generatePlan} className="bg-violet-600 hover:bg-violet-500 text-xs">
            Generate Question Plan
          </Button>
        </div>
      </div>
    );
  }

  const covSummary = questionPlan.coverage_summary || {};
  const matrixRows = covSummary.matrix || [];

  return (
    <div className="space-y-6">
      {/* Top Banner & Tab Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-900/80 border border-slate-800 rounded-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="border-violet-500/40 text-violet-400 text-[10px] uppercase font-mono">
              Personalized Plan
            </Badge>
            <span className="text-xs text-slate-400">
              Coverage: {covSummary.covered_count || 0}/{covSummary.total_requirements || 0} Covered ({covSummary.coverage_percentage || 0}%)
            </span>
          </div>
          <h3 className="text-sm font-bold text-white">{questionPlan.title}</h3>
        </div>

        <div className="flex items-center gap-2 bg-slate-950 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveTab('plan')}
            className={`px-3 py-1 text-xs rounded font-medium transition-all ${
              activeTab === 'plan' ? 'bg-violet-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Question Sequence ({questionPlan.items?.length || 0})
          </button>
          <button
            onClick={() => setActiveTab('coverage')}
            className={`px-3 py-1 text-xs rounded font-medium transition-all ${
              activeTab === 'coverage' ? 'bg-violet-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Coverage Matrix Map
          </button>
        </div>
      </div>

      {/* TAB 1: Question Sequence */}
      {activeTab === 'plan' && (
        <div className="space-y-4">
          {questionPlan.items?.map((item: any, idx: number) => (
            <Card key={idx} className="bg-slate-900/60 border-slate-800">
              <CardHeader className="pb-2 flex flex-row items-start justify-between gap-4">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 rounded-full bg-violet-950 border border-violet-700 flex items-center justify-center text-[10px] font-bold text-violet-300">
                      {item.sequence}
                    </span>
                    <CardTitle className="text-xs font-bold text-white">{item.title}</CardTitle>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-slate-400">
                    <span>Competency: <strong className="text-slate-300">{item.competency}</strong></span>
                    <span>·</span>
                    <Badge variant="outline" className="text-[9px] uppercase px-1 py-0 border-slate-700">
                      {item.difficulty}
                    </Badge>
                    <Badge className="bg-violet-950 text-violet-300 border border-violet-800/40 text-[9px] uppercase px-1 py-0">
                      {item.progression_stage}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Prompt */}
                <div className="p-3 bg-slate-950/80 rounded border border-slate-800/60 text-xs text-slate-200 font-mono leading-relaxed">
                  {item.prompt}
                </div>

                {/* Signals & Evidence Tested */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {item.expected_signal && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-semibold text-emerald-400 uppercase tracking-wider block">
                        Expected Signal
                      </span>
                      <p className="text-[11px] text-slate-400 leading-snug">{item.expected_signal}</p>
                    </div>
                  )}

                  {item.candidate_evidence_tested && (
                    <div className="space-y-1">
                      <span className="text-[10px] font-semibold text-indigo-400 uppercase tracking-wider block">
                        Evidence / Claim Tested
                      </span>
                      <p className="text-[11px] text-slate-400 leading-snug">{item.candidate_evidence_tested}</p>
                    </div>
                  )}
                </div>

                {/* Followup probes */}
                {item.suggested_followups && item.suggested_followups.length > 0 && (
                  <div className="pt-1">
                    <span className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider block mb-1">
                      Suggested Follow-Up Probes
                    </span>
                    <ul className="text-[11px] text-slate-400 space-y-0.5 list-disc list-inside">
                      {item.suggested_followups.map((f: string, fIdx: number) => (
                        <li key={fIdx}>{f}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* TAB 2: Coverage Matrix Map */}
      {activeTab === 'coverage' && (
        <Card className="bg-slate-900/60 border-slate-800 overflow-hidden">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
              <Table className="w-3.5 h-3.5 text-violet-400" />
              Requirement Coverage Matrix
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Clear mapping of what competencies are tested, why they are tested, and how candidate evidence was validated.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-950/80 border-b border-slate-800 text-[10px] uppercase font-semibold text-slate-400 tracking-wider">
                  <tr>
                    <th className="p-3">Job Requirement</th>
                    <th className="p-3">Candidate Evidence</th>
                    <th className="p-3">Interview Question Coverage</th>
                    <th className="p-3">Coverage Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {matrixRows.map((row: any, idx: number) => (
                    <tr key={idx} className="hover:bg-slate-950/40 transition-colors">
                      <td className="p-3 font-semibold text-white">
                        {row.job_requirement}
                        <span className="block text-[10px] text-slate-500 font-normal capitalize">
                          {row.requirement_type}
                        </span>
                      </td>
                      <td className="p-3 text-slate-300">
                        <div className="flex items-center gap-1.5">
                          <Badge
                            className={`text-[9px] px-1 py-0 ${
                              row.candidate_evidence_level === 'Strong'
                                ? 'bg-emerald-950 text-emerald-400 border-emerald-800/40'
                                : row.candidate_evidence_level === 'Claim Grounded'
                                ? 'bg-indigo-950 text-indigo-400 border-indigo-800/40'
                                : 'bg-amber-950 text-amber-400 border-amber-800/40'
                            }`}
                          >
                            {row.candidate_evidence_level}
                          </Badge>
                        </div>
                        <span className="block text-[11px] text-slate-400 mt-0.5">{row.evidence_description}</span>
                      </td>
                      <td className="p-3 text-slate-300 text-[11px]">{row.interview_coverage}</td>
                      <td className="p-3">
                        <Badge
                          className={`text-[9px] uppercase px-1.5 py-0 ${
                            row.status === 'Covered'
                              ? 'bg-emerald-950 text-emerald-400 border-emerald-800/40'
                              : row.status === 'Needs Verification'
                              ? 'bg-amber-950 text-amber-400 border-amber-800/40'
                              : 'bg-slate-800 text-slate-400 border-slate-700'
                          }`}
                        >
                          {row.status}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
