'use client';

import React, { useState } from 'react';
import { Users, Award, ShieldCheck, AlertTriangle, CheckCircle2, XCircle, Clock, Eye, Filter, ArrowUpDown } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { CandidateTimelineModal } from './candidate-timeline-modal';

interface CandidateDecisionTabProps {
  workspaceId: string;
  data: any;
  loading: boolean;
}

export function CandidateDecisionTab({ workspaceId, data, loading }: CandidateDecisionTabProps) {
  const [selectedCandidate, setSelectedCandidate] = useState<{ id: string; name: string } | null>(null);
  const [sortBy, setSortBy] = useState<'score' | 'confidence' | 'name'>('score');
  const [sortDesc, setSortDesc] = useState(true);

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-64 rounded-xl bg-zinc-900/60 border border-zinc-800" />
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
        No candidate decision matrix available for the selected filters.
      </div>
    );
  }

  const rawCandidates: any[] = data.candidates || [];
  const funnel = data.funnel || {};

  const candidates = [...rawCandidates].sort((a, b) => {
    if (sortBy === 'score') {
      const sA = a.overall_score ?? 0;
      const sB = b.overall_score ?? 0;
      return sortDesc ? sB - sA : sA - sB;
    }
    if (sortBy === 'confidence') {
      const cA = a.confidence ?? 0;
      const cB = b.confidence ?? 0;
      return sortDesc ? cB - cA : cA - cB;
    }
    const nA = a.candidate_name || '';
    const nB = b.candidate_name || '';
    return sortDesc ? nB.localeCompare(nA) : nA.localeCompare(nB);
  });

  const getRecBadge = (rec: string) => {
    const key = (rec || '').toLowerCase();
    if (key === 'strong_hire') {
      return <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">Strong Hire</Badge>;
    }
    if (key === 'hire') {
      return <Badge className="bg-indigo-500/10 text-indigo-400 border-indigo-500/20">Hire</Badge>;
    }
    if (key === 'lean_hire') {
      return <Badge className="bg-blue-500/10 text-blue-400 border-blue-500/20">Lean Hire</Badge>;
    }
    if (key === 'lean_no_hire') {
      return <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20">Lean No Hire</Badge>;
    }
    if (key === 'no_hire') {
      return <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/20">No Hire</Badge>;
    }
    return <Badge className="bg-zinc-800 text-zinc-400 border-zinc-700">Insufficient Evidence</Badge>;
  };

  return (
    <div className="space-y-6">
      {/* Hiring Funnel KPI Cards */}
      {funnel.stages && funnel.stages.length > 0 && (
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardHeader className="pb-3 border-b border-zinc-800/60">
            <CardTitle className="text-sm font-semibold text-white">End-to-End Hiring Funnel</CardTitle>
            <CardDescription className="text-xs text-zinc-400">Candidate flow from application to authoritative evaluation</CardDescription>
          </CardHeader>
          <CardContent className="p-5">
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
              {funnel.stages.map((st: any, i: number) => (
                <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3.5 space-y-1 text-center">
                  <span className="text-[10px] text-zinc-500 font-medium uppercase truncate block">{st.stage_name}</span>
                  <div className="text-lg font-bold text-white">{st.candidate_count}</div>
                  <div className="text-[10px] text-indigo-400 font-mono">
                    {st.conversion_rate !== undefined ? `${st.conversion_rate}% conv` : 'Stage 1'}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Decision Matrix Table */}
      <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
        <CardHeader className="pb-4 border-b border-zinc-800/60 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-semibold text-white">Candidate Decision Matrix</CardTitle>
            <CardDescription className="text-xs text-zinc-400">
              Normalized ranking, rubric levels, confidence metrics, and evidence sufficiency
            </CardDescription>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (sortBy === 'score') setSortDesc(!sortDesc);
                else {
                  setSortBy('score');
                  setSortDesc(true);
                }
              }}
              className={`border-zinc-700 h-8 gap-1 ${sortBy === 'score' ? 'text-indigo-400 border-indigo-500/50' : 'text-zinc-400'}`}
            >
              <ArrowUpDown className="h-3.5 w-3.5" />
              Score
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                if (sortBy === 'confidence') setSortDesc(!sortDesc);
                else {
                  setSortBy('confidence');
                  setSortDesc(true);
                }
              }}
              className={`border-zinc-700 h-8 gap-1 ${sortBy === 'confidence' ? 'text-indigo-400 border-indigo-500/50' : 'text-zinc-400'}`}
            >
              <ArrowUpDown className="h-3.5 w-3.5" />
              Confidence
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {candidates.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-zinc-500 text-xs">
              <Users className="h-8 w-8 text-zinc-600 mb-2" />
              <p>No finalized candidate evaluations found for this criteria.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-zinc-800 bg-zinc-950/70 text-zinc-400 font-medium uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Candidate</th>
                    <th className="py-3 px-4">Recommendation</th>
                    <th className="py-3 px-4 text-center">Deterministic Score</th>
                    <th className="py-3 px-4 text-center">Rubric Level</th>
                    <th className="py-3 px-4 text-center">Evidence Grounding</th>
                    <th className="py-3 px-4 text-center">Confidence</th>
                    <th className="py-3 px-4 text-center">Contradictions</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {candidates.map((c: any) => (
                    <tr key={c.evaluation_id} className="hover:bg-zinc-800/30 transition-colors">
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-white">{c.candidate_name || 'Anonymous Candidate'}</div>
                        <div className="text-[11px] text-zinc-500">{c.job_title || 'General Pipeline'}</div>
                      </td>
                      <td className="py-3.5 px-4">{getRecBadge(c.recommendation)}</td>
                      <td className="py-3.5 px-4 text-center">
                        <span className="font-bold text-white text-sm">
                          {c.overall_score !== null ? c.overall_score : '—'}
                        </span>
                        <span className="text-[10px] text-zinc-500 ml-0.5">/ 100</span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <Badge variant="outline" className="border-zinc-700 bg-zinc-900 text-zinc-300 text-[10px] capitalize">
                          {c.overall_rubric_level || 'standard'}
                        </Badge>
                      </td>
                      <td className="py-3.5 px-4 text-center font-mono text-zinc-300">
                        {c.evidence_count ?? 0} items
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        <span className="font-semibold text-indigo-400 font-mono">
                          {c.confidence ? `${Math.round(c.confidence * 100)}%` : '—'}
                        </span>
                      </td>
                      <td className="py-3.5 px-4 text-center">
                        {c.contradiction_count > 0 ? (
                          <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px]">
                            {c.contradiction_count} flagged
                          </Badge>
                        ) : (
                          <span className="text-emerald-400 font-mono">0</span>
                        )}
                      </td>
                      <td className="py-3.5 px-4 text-right">
                        {c.candidate_id ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              setSelectedCandidate({
                                id: c.candidate_id,
                                name: c.candidate_name || 'Candidate',
                              })
                            }
                            className="text-xs h-7 text-indigo-400 hover:text-indigo-300 hover:bg-indigo-500/10 gap-1"
                          >
                            <Eye className="h-3.5 w-3.5" />
                            Timeline
                          </Button>
                        ) : (
                          <span className="text-zinc-600">—</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Candidate Unified Timeline Modal */}
      {selectedCandidate && (
        <CandidateTimelineModal
          workspaceId={workspaceId}
          candidateId={selectedCandidate.id}
          candidateName={selectedCandidate.name}
          isOpen={Boolean(selectedCandidate)}
          onClose={() => setSelectedCandidate(null)}
        />
      )}
    </div>
  );
}
