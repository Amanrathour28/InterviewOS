'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Target,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  TrendingUp,
  Sparkles,
  Shield,
  Layers,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

interface CandidateJobMatchCardProps {
  jobId: string;
  candidateId: string;
}

export function CandidateJobMatchCard({ jobId, candidateId }: CandidateJobMatchCardProps) {
  const [match, setMatch] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadMatch = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiClient<any>(`/intelligence/jobs/${jobId}/candidates/${candidateId}/match`);
      setMatch(data);
    } catch (err) {
      console.error('Failed to load candidate match:', err);
    } finally {
      setIsLoading(false);
    }
  }, [jobId, candidateId]);

  useEffect(() => {
    if (jobId && candidateId) {
      loadMatch();
    }
  }, [jobId, candidateId, loadMatch]);

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-400">Computing deterministic match scores...</div>;
  }

  if (!match) {
    return (
      <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-800 rounded-lg">
        Match evaluation not generated yet.
        <div className="mt-3">
          <Button size="sm" onClick={loadMatch} className="bg-violet-600 hover:bg-violet-500 text-xs">
            Run Match Evaluation
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overall Score Banner */}
      <Card className="bg-slate-900/80 border-slate-800 overflow-hidden">
        <div className="p-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="space-y-1 text-center md:text-left">
            <div className="flex items-center justify-center md:justify-start gap-2">
              <Badge variant="outline" className="border-violet-500/40 text-violet-400 text-[10px] uppercase font-mono">
                Deterministic Fit Score
              </Badge>
            </div>
            <h3 className="text-xl font-bold text-white tracking-tight">Candidate ↔ Job Match Evaluation</h3>
            <p className="text-xs text-slate-400 max-w-xl">
              {match.explanation || 'Mathematical evaluation across required skills, experience, project relevance, and seniority.'}
            </p>
          </div>

          <div className="flex flex-col items-center justify-center p-4 bg-slate-950/80 rounded-xl border border-slate-800 min-w-[140px]">
            <div className="text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-indigo-300 font-mono">
              {match.overall_score.toFixed(0)}%
            </div>
            <div className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mt-1">Overall Match</div>
          </div>
        </div>

        {/* 6 Deterministic Component Breakdown Bars */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 p-4 bg-slate-950/40 border-t border-slate-800/80">
          <div className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">Required Skills</span>
              <span className="font-semibold text-white">{match.required_skill_coverage.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div className="bg-emerald-500 h-full rounded-full" style={{ width: `${match.required_skill_coverage}%` }} />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">Preferred Skills</span>
              <span className="font-semibold text-white">{match.preferred_skill_coverage.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div className="bg-indigo-500 h-full rounded-full" style={{ width: `${match.preferred_skill_coverage}%` }} />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">Experience Fit</span>
              <span className="font-semibold text-white">{match.experience_fit.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div className="bg-violet-500 h-full rounded-full" style={{ width: `${match.experience_fit}%` }} />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">Project Fit</span>
              <span className="font-semibold text-white">{match.project_relevance.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div className="bg-cyan-500 h-full rounded-full" style={{ width: `${match.project_relevance}%` }} />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">Seniority Fit</span>
              <span className="font-semibold text-white">{match.seniority_fit.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div className="bg-amber-500 h-full rounded-full" style={{ width: `${match.seniority_fit}%` }} />
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[11px]">
              <span className="text-slate-400">Domain Fit</span>
              <span className="font-semibold text-white">{match.domain_fit.toFixed(0)}%</span>
            </div>
            <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
              <div className="bg-teal-500 h-full rounded-full" style={{ width: `${match.domain_fit}%` }} />
            </div>
          </div>
        </div>
      </Card>

      {/* Strengths & Gaps */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strengths */}
        <Card className="bg-slate-900/60 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-semibold text-emerald-400 uppercase tracking-wider flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              Verified Strengths ({match.strengths?.length || 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {match.strengths?.map((s: any, idx: number) => (
              <div key={idx} className="p-2.5 bg-slate-950/60 rounded border border-slate-800/80 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white">{s.skill}</span>
                  <Badge className="bg-emerald-950 text-emerald-400 border border-emerald-800/40 text-[9px] px-1.5 py-0">
                    {s.importance || 'Strong'}
                  </Badge>
                </div>
                <p className="text-[11px] text-slate-400">{s.evidence}</p>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Gaps & Verification Probes */}
        <Card className="bg-slate-900/60 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-semibold text-amber-400 uppercase tracking-wider flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              Potential Gaps & Verification Focus ({match.gaps?.length || 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2.5">
            {match.gaps?.map((g: any, idx: number) => (
              <div key={idx} className="p-2.5 bg-slate-950/60 rounded border border-slate-800/80 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-200">{g.skill}</span>
                  <Badge className="bg-amber-950 text-amber-400 border border-amber-800/40 text-[9px] px-1.5 py-0">
                    Gap
                  </Badge>
                </div>
                <p className="text-[11px] text-slate-400">{g.reason}</p>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
