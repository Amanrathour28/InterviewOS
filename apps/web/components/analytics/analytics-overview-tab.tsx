'use client';

import React from 'react';
import {
  Users,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
  Award,
  ShieldCheck,
  AlertTriangle,
  FileCheck2,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface OverviewTabProps {
  data: any;
  loading: boolean;
}

export function AnalyticsOverviewTab({ data, loading }: OverviewTabProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 rounded-xl bg-zinc-900/60 border border-zinc-800" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
        No analytics data available for the selected filters.
      </div>
    );
  }

  const vol = data.interview_volume || {};
  const scores = data.score_summary || {};
  const recs = data.recommendation_distribution || {};
  const ev = data.evidence_quality_summary || {};

  const distributionBins = scores.bins || scores.distribution_buckets || {};
  const binPercentages = scores.bin_percentages || {};

  return (
    <div className="space-y-6">
      {/* KPI Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Interviews */}
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider">Total Interviews</span>
              <div className="text-2xl font-black text-white">{vol.total_interviews ?? vol.total ?? 0}</div>
              <div className="text-[11px] text-zinc-500">
                {vol.completed_sessions ?? 0} sessions completed
              </div>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Users className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        {/* Completion Rate */}
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider">Completion Rate</span>
              <div className="text-2xl font-black text-emerald-400">{vol.completion_rate ?? 0}%</div>
              <div className="text-[11px] text-zinc-500">
                {vol.cancellation_rate ?? 0}% cancellation • {vol.no_show_rate ?? 0}% no-show
              </div>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <CheckCircle2 className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        {/* Mean Evaluation Score */}
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider">Average Score</span>
              <div className="text-2xl font-black text-indigo-400">{scores.mean ?? 0} / 100</div>
              <div className="text-[11px] text-zinc-500">
                Median: {scores.median ?? 0} • P90: {scores.p90 ?? 0}
              </div>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Award className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        {/* Positive Rec Rate */}
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider">Hire Rate</span>
              <div className="text-2xl font-black text-purple-400">{recs.hire_rate ?? recs.positive_recommendation_rate ?? 0}%</div>
              <div className="text-[11px] text-zinc-500">
                {recs.counts?.strong_hire ?? 0} strong • {recs.counts?.hire ?? 0} hire
              </div>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-purple-500/10 border border-purple-500/20 text-purple-400">
              <TrendingUp className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Two Column Section: Score Distribution + Recommendation Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Score Distribution */}
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardHeader className="pb-3 border-b border-zinc-800/60">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold text-white">Score Distribution</CardTitle>
                <CardDescription className="text-xs text-zinc-400">Deterministic percentile and range breakdown</CardDescription>
              </div>
              <Badge variant="outline" className="border-zinc-700 bg-zinc-800/60 text-zinc-300 text-xs">
                n = {scores.sample_size ?? 0}
              </Badge>
            </div>
          </CardHeader>
          <CardContent className="p-5 space-y-4">
            <div className="space-y-2.5">
              {[
                { label: '85 - 100 (Exemplary)', key: '85_100', color: 'bg-emerald-500' },
                { label: '70 - 84 (Strong)', key: '70_85', color: 'bg-indigo-500' },
                { label: '55 - 69 (Competent)', key: '55_70', color: 'bg-blue-500' },
                { label: '40 - 54 (Developing)', key: '40_55', color: 'bg-amber-500' },
                { label: '20 - 39 (Limited)', key: '20_40', color: 'bg-orange-500' },
                { label: '0 - 19 (Insufficient)', key: '0_20', color: 'bg-rose-500' },
              ].map((bin) => {
                const count = distributionBins[bin.key] || 0;
                const pct = binPercentages[bin.key] || 0;
                return (
                  <div key={bin.key} className="space-y-1">
                    <div className="flex items-center justify-between text-xs">
                      <span className="text-zinc-300 font-medium">{bin.label}</span>
                      <span className="text-zinc-400 font-mono">
                        {count} ({pct}%)
                      </span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-zinc-800 overflow-hidden">
                      <div
                        className={`h-full rounded-full ${bin.color} transition-all duration-500`}
                        style={{ width: `${Math.min(100, Math.max(0, pct))}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Percentile Stats Summary */}
            <div className="grid grid-cols-4 gap-2 pt-2 border-t border-zinc-800/80 text-center text-xs">
              <div className="p-2 rounded-lg bg-zinc-950/60 border border-zinc-800/60">
                <span className="text-zinc-500 block text-[10px] uppercase">Min</span>
                <span className="font-bold text-white">{scores.min ?? 0}</span>
              </div>
              <div className="p-2 rounded-lg bg-zinc-950/60 border border-zinc-800/60">
                <span className="text-zinc-500 block text-[10px] uppercase">P25</span>
                <span className="font-bold text-zinc-300">{scores.p25 ?? 0}</span>
              </div>
              <div className="p-2 rounded-lg bg-zinc-950/60 border border-zinc-800/60">
                <span className="text-zinc-500 block text-[10px] uppercase">Median</span>
                <span className="font-bold text-indigo-300">{scores.median ?? 0}</span>
              </div>
              <div className="p-2 rounded-lg bg-zinc-950/60 border border-zinc-800/60">
                <span className="text-zinc-500 block text-[10px] uppercase">P75</span>
                <span className="font-bold text-zinc-300">{scores.p75 ?? 0}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Recommendation Breakdown & Evidence Quality */}
        <div className="space-y-6">
          {/* Recommendation Breakdown */}
          <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
            <CardHeader className="pb-3 border-b border-zinc-800/60">
              <CardTitle className="text-sm font-semibold text-white">Recommendation Breakdown</CardTitle>
              <CardDescription className="text-xs text-zinc-400">Authoritative evaluation outcomes</CardDescription>
            </CardHeader>
            <CardContent className="p-5 space-y-3">
              {[
                { label: 'Strong Hire', key: 'strong_hire', color: 'bg-emerald-500', text: 'text-emerald-400' },
                { label: 'Hire', key: 'hire', color: 'bg-indigo-500', text: 'text-indigo-400' },
                { label: 'Lean Hire', key: 'lean_hire', color: 'bg-blue-500', text: 'text-blue-400' },
                { label: 'Lean No Hire', key: 'lean_no_hire', color: 'bg-amber-500', text: 'text-amber-400' },
                { label: 'No Hire', key: 'no_hire', color: 'bg-rose-500', text: 'text-rose-400' },
                { label: 'Insufficient Evidence', key: 'insufficient_evidence', color: 'bg-zinc-600', text: 'text-zinc-400' },
              ].map((rec) => {
                const count = recs.counts?.[rec.key] || 0;
                const pct = recs.percentages?.[rec.key] || recs.rates?.[rec.key] || 0;
                return (
                  <div key={rec.key} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <div className={`h-2.5 w-2.5 rounded-full ${rec.color}`} />
                      <span className="text-zinc-300 font-medium">{rec.label}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`font-semibold ${rec.text}`}>{count}</span>
                      <span className="text-zinc-500 font-mono w-10 text-right">{pct}%</span>
                    </div>
                  </div>
                );
              })}
            </CardContent>
          </Card>

          {/* Evidence Quality Mini-Summary */}
          <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
            <CardHeader className="pb-3 border-b border-zinc-800/60">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
                  <ShieldCheck className="h-4 w-4 text-emerald-400" />
                  Evidence Grounding & Integrity
                </CardTitle>
                <span className="text-[11px] text-zinc-500">Telemetry</span>
              </div>
            </CardHeader>
            <CardContent className="p-5 grid grid-cols-3 gap-3 text-center text-xs">
              <div className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/60 space-y-1">
                <span className="text-[10px] text-zinc-500 uppercase font-medium">Avg Evidence</span>
                <div className="text-lg font-bold text-white">{ev.average_evidence_count_per_eval ?? 0}</div>
                <span className="text-[10px] text-zinc-500">items / evaluation</span>
              </div>
              <div className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/60 space-y-1">
                <span className="text-[10px] text-zinc-500 uppercase font-medium">Grounding</span>
                <div className="text-lg font-bold text-emerald-400">
                  {Math.round((ev.grounded_percentage ?? 100))}%
                </div>
                <span className="text-[10px] text-zinc-500">supported claims</span>
              </div>
              <div className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/60 space-y-1">
                <span className="text-[10px] text-zinc-500 uppercase font-medium">Contradictions</span>
                <div className="text-lg font-bold text-amber-400">{ev.total_contradictions_detected ?? 0}</div>
                <span className="text-[10px] text-zinc-500">flagged & surfaced</span>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
