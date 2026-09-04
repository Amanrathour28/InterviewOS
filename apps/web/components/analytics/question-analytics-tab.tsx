'use client';

import React from 'react';
import { HelpCircle, FileCheck, Award, Zap, AlertTriangle, Layers } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface QuestionAnalyticsTabProps {
  data: any;
  loading: boolean;
}

export function QuestionAnalyticsTab({ data, loading }: QuestionAnalyticsTabProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-44 rounded-xl bg-zinc-900/60 border border-zinc-800" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
        No question performance analytics available.
      </div>
    );
  }

  const questions: any[] = data.questions || [];
  const adaptive = data.adaptive_metrics || {};

  return (
    <div className="space-y-6">
      {/* Header Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] text-zinc-500 font-medium uppercase">Total Questions Utilized</span>
            <div className="text-2xl font-bold text-white">{data.total_questions_analyzed ?? questions.length}</div>
            <span className="text-[10px] text-zinc-500">Curated & dynamically generated</span>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] text-zinc-500 font-medium uppercase">Adaptive Depth Adjustment</span>
            <div className="text-2xl font-bold text-indigo-400">
              {adaptive.dynamic_followup_frequency ?? 0}%
            </div>
            <span className="text-[10px] text-zinc-500">Sessions using dynamic followups</span>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] text-zinc-500 font-medium uppercase">Average Evidence Yield</span>
            <div className="text-2xl font-bold text-emerald-400">
              {data.average_evidence_yield ?? 2.8} items
            </div>
            <span className="text-[10px] text-zinc-500">Observations per question asked</span>
          </CardContent>
        </Card>
      </div>

      {/* Questions Ranking Table */}
      <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
        <CardHeader className="pb-4 border-b border-zinc-800/60">
          <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
            <HelpCircle className="h-4 w-4 text-indigo-400" />
            Question Effectiveness & Evidence Yield
          </CardTitle>
          <CardDescription className="text-xs text-zinc-400">
            Discriminative power, average candidate performance, and evidence production
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {questions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-zinc-500 text-xs">
              <HelpCircle className="h-8 w-8 text-zinc-600 mb-2" />
              <p>No question telemetry logged for this period.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-zinc-800 bg-zinc-950/70 text-zinc-400 font-medium uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Question Prompt / Title</th>
                    <th className="py-3 px-4">Competency</th>
                    <th className="py-3 px-4 text-center">Times Asked</th>
                    <th className="py-3 px-4 text-center">Avg Candidate Score</th>
                    <th className="py-3 px-4 text-center">Evidence Yield</th>
                    <th className="py-3 px-4 text-center">Discriminative Power</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {questions.map((q: any, i: number) => {
                    const yieldScore = q.evidence_yield_per_use ?? 0;
                    const disc = q.discriminative_power || (q.std_dev > 15 ? 'High' : q.std_dev > 8 ? 'Moderate' : 'Low');

                    return (
                      <tr key={i} className="hover:bg-zinc-800/30 transition-colors">
                        <td className="py-3.5 px-4 max-w-sm">
                          <div className="font-semibold text-white truncate">{q.question_text || q.title || `Question ${i + 1}`}</div>
                          <div className="text-[11px] text-zinc-500 capitalize">{q.category || 'Technical Assessment'}</div>
                        </td>
                        <td className="py-3.5 px-4">
                          <Badge variant="outline" className="border-zinc-700 bg-zinc-900 text-zinc-300 text-[10px] capitalize">
                            {q.competency_name || 'General'}
                          </Badge>
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono font-semibold text-white">
                          {q.usage_count ?? q.times_asked ?? 0}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <span className="font-bold text-indigo-300">{q.average_score ?? 0}</span>
                          <span className="text-[10px] text-zinc-500 ml-0.5">/ 100</span>
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono text-emerald-400 font-semibold">
                          {yieldScore} items
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <Badge
                            className={`text-[10px] ${
                              disc === 'High'
                                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                                : disc === 'Moderate'
                                ? 'bg-indigo-500/10 text-indigo-400 border-indigo-500/20'
                                : 'bg-zinc-800 text-zinc-400 border-zinc-700'
                            }`}
                          >
                            {disc}
                          </Badge>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
