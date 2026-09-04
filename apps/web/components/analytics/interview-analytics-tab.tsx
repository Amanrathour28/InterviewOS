'use client';

import React from 'react';
import { Clock, Play, CheckCircle2, XCircle, AlertOctagon, TrendingUp, Layers } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface InterviewAnalyticsTabProps {
  data: any;
  loading: boolean;
}

export function InterviewAnalyticsTab({ data, loading }: InterviewAnalyticsTabProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-pulse">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 rounded-xl bg-zinc-900/60 border border-zinc-800" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
        No interview telemetry available for the selected filters.
      </div>
    );
  }

  const vol = data.volume || {};
  const dur = data.duration || {};
  const stages = data.stages?.stages || [];
  const timeline = data.timeline?.timeline || [];

  return (
    <div className="space-y-6">
      {/* Volume & Status Grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {[
          { label: 'Scheduled', count: vol.status_counts?.scheduled ?? 0, color: 'text-blue-400', border: 'border-blue-500/20' },
          { label: 'In Progress', count: vol.status_counts?.in_progress ?? 0, color: 'text-amber-400', border: 'border-amber-500/20' },
          { label: 'Completed', count: vol.status_counts?.completed ?? 0, color: 'text-emerald-400', border: 'border-emerald-500/20' },
          { label: 'Cancelled', count: vol.status_counts?.cancelled ?? 0, color: 'text-rose-400', border: 'border-rose-500/20' },
          { label: 'Expired / No Show', count: vol.status_counts?.expired ?? 0, color: 'text-orange-400', border: 'border-orange-500/20' },
          { label: 'Draft', count: vol.status_counts?.draft ?? 0, color: 'text-zinc-400', border: 'border-zinc-700' },
        ].map((item, i) => (
          <Card key={i} className={`border ${item.border} bg-zinc-900/40 backdrop-blur-md`}>
            <CardContent className="p-4 space-y-1">
              <span className="text-[11px] text-zinc-500 font-medium uppercase">{item.label}</span>
              <div className={`text-xl font-bold ${item.color}`}>{item.count}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Duration Analytics & Stage Progression */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Duration Analytics */}
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardHeader className="pb-3 border-b border-zinc-800/60">
            <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
              <Clock className="h-4 w-4 text-indigo-400" />
              Duration & Timing Distribution
            </CardTitle>
            <CardDescription className="text-xs text-zinc-400">Scheduled vs Actual interview length in minutes</CardDescription>
          </CardHeader>
          <CardContent className="p-5 space-y-4 text-xs">
            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/60 space-y-1">
                <span className="text-[10px] text-zinc-500 uppercase">Avg Actual</span>
                <div className="text-lg font-bold text-indigo-400">{dur.actual_duration_stats?.mean ?? 0}m</div>
                <span className="text-[10px] text-zinc-500">Median: {dur.actual_duration_stats?.median ?? 0}m</span>
              </div>
              <div className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/60 space-y-1">
                <span className="text-[10px] text-zinc-500 uppercase">Scheduled Avg</span>
                <div className="text-lg font-bold text-white">{dur.scheduled_duration_stats?.mean ?? 0}m</div>
                <span className="text-[10px] text-zinc-500">Median: {dur.scheduled_duration_stats?.median ?? 0}m</span>
              </div>
              <div className="p-3 rounded-xl bg-zinc-950/60 border border-zinc-800/60 space-y-1">
                <span className="text-[10px] text-zinc-500 uppercase">Overrun Rate</span>
                <div className="text-lg font-bold text-amber-400">{dur.overrun_rate ?? 0}%</div>
                <span className="text-[10px] text-zinc-500">Avg Delta: {dur.average_duration_delta_minutes ?? 0}m</span>
              </div>
            </div>

            {/* Percentiles */}
            <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/40 p-3 space-y-2">
              <div className="text-[11px] font-medium text-zinc-400">Actual Duration Percentiles</div>
              <div className="flex items-center justify-between text-zinc-300">
                <span>P25: <strong className="text-white">{dur.actual_duration_stats?.p25 ?? 0}m</strong></span>
                <span>P50: <strong className="text-indigo-300">{dur.actual_duration_stats?.median ?? 0}m</strong></span>
                <span>P75: <strong className="text-white">{dur.actual_duration_stats?.p75 ?? 0}m</strong></span>
                <span>P90: <strong className="text-amber-300">{dur.actual_duration_stats?.p90 ?? 0}m</strong></span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Stage Progression & Abandonment */}
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardHeader className="pb-3 border-b border-zinc-800/60">
            <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
              <Layers className="h-4 w-4 text-emerald-400" />
              Stage Progression & Abandonment
            </CardTitle>
            <CardDescription className="text-xs text-zinc-400">Stage-by-stage progression through multi-round interviews</CardDescription>
          </CardHeader>
          <CardContent className="p-5 space-y-3">
            {stages.length === 0 ? (
              <div className="flex items-center justify-center py-8 text-zinc-500 text-xs">
                No multi-stage progression data available.
              </div>
            ) : (
              <div className="space-y-3">
                {stages.map((st: any, i: number) => (
                  <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-3 space-y-1.5 text-xs">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold text-white capitalize">{st.stage_name || `Stage ${i + 1}`}</span>
                      <span className="text-zinc-400 font-mono">
                        Pass: <strong className="text-emerald-400">{st.pass_rate ?? 100}%</strong> • Abandon: <strong className="text-rose-400">{st.abandon_rate ?? 0}%</strong>
                      </span>
                    </div>
                    <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-emerald-500"
                        style={{ width: `${Math.min(100, Math.max(0, st.pass_rate ?? 100))}%` }}
                      />
                    </div>
                    <div className="flex items-center justify-between text-[10px] text-zinc-500">
                      <span>Started: {st.started_count ?? 0} candidates</span>
                      <span>Avg Duration: {st.average_duration_minutes ?? 0}m</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Timeline Trend */}
      {timeline.length > 0 && (
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardHeader className="pb-3 border-b border-zinc-800/60">
            <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-purple-400" />
              Interview Volume Timeline
            </CardTitle>
            <CardDescription className="text-xs text-zinc-400">Daily creation and session completion activity</CardDescription>
          </CardHeader>
          <CardContent className="p-5">
            <div className="flex items-end gap-1.5 h-32 pt-4 overflow-x-auto">
              {timeline.map((d: any, idx: number) => {
                const maxVal = Math.max(...timeline.map((t: any) => t.count || 1), 5);
                const heightPct = Math.round(((d.count || 0) / maxVal) * 100);
                return (
                  <div key={idx} className="flex-1 min-w-[20px] flex flex-col items-center gap-1 group">
                    <div className="text-[9px] text-zinc-400 opacity-0 group-hover:opacity-100 transition-opacity font-mono">
                      {d.count}
                    </div>
                    <div className="w-full bg-zinc-800 rounded-t h-20 flex items-end">
                      <div
                        className="w-full bg-gradient-to-t from-indigo-600 to-purple-500 rounded-t group-hover:from-indigo-400 group-hover:to-purple-300 transition-all"
                        style={{ height: `${Math.max(4, heightPct)}%` }}
                      />
                    </div>
                    <div className="text-[9px] text-zinc-500 font-mono truncate max-w-[32px]">
                      {d.date?.slice(5)}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
