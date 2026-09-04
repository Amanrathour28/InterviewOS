'use client';

import React from 'react';
import { Award, ShieldAlert, CheckCircle2, Sliders, TrendingUp, AlertTriangle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface CompetencyAnalyticsTabProps {
  data: any;
  loading: boolean;
}

export function CompetencyAnalyticsTab({ data, loading }: CompetencyAnalyticsTabProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-48 rounded-xl bg-zinc-900/60 border border-zinc-800" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
        No competency analytics available for the selected filters.
      </div>
    );
  }

  const comps: any[] = data.competencies || [];

  return (
    <div className="space-y-6">
      {/* Competency Summary Header */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] text-zinc-500 font-medium uppercase">Total Competencies Assessed</span>
            <div className="text-2xl font-bold text-white">{data.distinct_competencies_count ?? comps.length}</div>
            <span className="text-[10px] text-zinc-500">{data.total_competency_evaluations ?? 0} total evaluations</span>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] text-zinc-500 font-medium uppercase">Average Override Rate</span>
            <div className="text-2xl font-bold text-amber-400">
              {comps.length > 0
                ? Math.round(comps.reduce((acc, c) => acc + (c.override_rate || 0), 0) / comps.length)
                : 0}
              %
            </div>
            <span className="text-[10px] text-zinc-500">Human recalibration frequency</span>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] text-zinc-500 font-medium uppercase">Average Evidence Sufficiency</span>
            <div className="text-2xl font-bold text-emerald-400">
              {comps.length > 0
                ? Math.round(comps.reduce((acc, c) => acc + (c.sufficiency_rate || 0), 0) / comps.length)
                : 100}
              %
            </div>
            <span className="text-[10px] text-zinc-500">Criteria with definitive evidence</span>
          </CardContent>
        </Card>
      </div>

      {/* Competencies Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {comps.map((comp: any) => {
          const score = comp.average_score ?? 0;
          const dist = comp.distribution?.bins || {};

          return (
            <Card key={comp.competency_name} className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
              <CardHeader className="pb-3 border-b border-zinc-800/60">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm font-semibold text-white capitalize">
                    {comp.competency_name.replace(/_/g, ' ')}
                  </CardTitle>
                  <Badge variant="outline" className="border-zinc-700 bg-zinc-800/80 text-zinc-300 text-xs">
                    n = {comp.sample_size ?? 0}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="p-5 space-y-4 text-xs">
                {/* Score Summary */}
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-zinc-400">Mean Score</span>
                    <div className="text-xl font-black text-indigo-400">
                      {score} <span className="text-xs text-zinc-500 font-normal">/ 100</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="text-zinc-400">Median / P90</span>
                    <div className="font-semibold text-white font-mono">
                      {comp.median_score ?? 0} / {comp.distribution?.p90 ?? 0}
                    </div>
                  </div>
                </div>

                {/* Score bar */}
                <div className="space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-zinc-400">
                    <span>Performance Rating</span>
                    <span>{score >= 70 ? 'Strong' : score >= 50 ? 'Moderate' : 'Needs Development'}</span>
                  </div>
                  <div className="h-2 w-full rounded-full bg-zinc-800 overflow-hidden">
                    <div
                      className={`h-full rounded-full ${
                        score >= 70 ? 'bg-emerald-500' : score >= 50 ? 'bg-indigo-500' : 'bg-amber-500'
                      }`}
                      style={{ width: `${Math.min(100, Math.max(0, score))}%` }}
                    />
                  </div>
                </div>

                {/* Quality & Override Metrics */}
                <div className="grid grid-cols-2 gap-2 pt-2 border-t border-zinc-800/80">
                  <div className="p-2.5 rounded-lg bg-zinc-950/50 border border-zinc-800/50 space-y-0.5">
                    <span className="text-[10px] text-zinc-500 uppercase">Sufficiency Rate</span>
                    <div className="font-semibold text-emerald-400">{comp.sufficiency_rate ?? 100}%</div>
                    <span className="text-[10px] text-zinc-500">
                      {comp.insufficient_evidence_rate ?? 0}% insufficient
                    </span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-zinc-950/50 border border-zinc-800/50 space-y-0.5">
                    <span className="text-[10px] text-zinc-500 uppercase">Override Rate</span>
                    <div className="font-semibold text-amber-400">{comp.override_rate ?? 0}%</div>
                    <span className="text-[10px] text-zinc-500">{comp.override_count ?? 0} manual overrides</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
