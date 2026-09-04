'use client';

import React from 'react';
import { UserCheck, ShieldAlert, Award, Scale, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface InterviewerCalibrationTabProps {
  data: any;
  loading: boolean;
}

export function InterviewerCalibrationTab({ data, loading }: InterviewerCalibrationTabProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 animate-pulse">
        {[1, 2].map((i) => (
          <div key={i} className="h-56 rounded-xl bg-zinc-900/60 border border-zinc-800" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
        No interviewer calibration telemetry available.
      </div>
    );
  }

  const interviewers: any[] = data.interviewers || [];

  return (
    <div className="space-y-6">
      {/* Overview stats */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] text-zinc-500 font-medium uppercase">Active Interviewers</span>
            <div className="text-2xl font-bold text-white">{data.total_active_interviewers ?? interviewers.length}</div>
            <span className="text-[10px] text-zinc-500">Panel participants in period</span>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] text-zinc-500 font-medium uppercase">Total Conducted Sessions</span>
            <div className="text-2xl font-bold text-indigo-400">{data.total_interviews_conducted ?? 0}</div>
            <span className="text-[10px] text-zinc-500">Peer and AI co-piloted sessions</span>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-4 space-y-1">
            <span className="text-[11px] text-zinc-500 font-medium uppercase">System-wide Mean Score</span>
            <div className="text-2xl font-bold text-emerald-400">
              {data.workspace_average_score ?? 70} / 100
            </div>
            <span className="text-[10px] text-zinc-500">Benchmark baseline</span>
          </CardContent>
        </Card>
      </div>

      {/* Interviewer Table / Cards */}
      <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
        <CardHeader className="pb-4 border-b border-zinc-800/60">
          <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
            <Scale className="h-4 w-4 text-indigo-400" />
            Interviewer Panel Calibration & Scoring Consistency
          </CardTitle>
          <CardDescription className="text-xs text-zinc-400">
            Variance from peer baseline, positive recommendation rates, and calibration signals
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {interviewers.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 text-zinc-500 text-xs">
              <UserCheck className="h-8 w-8 text-zinc-600 mb-2" />
              <p>No interviewer performance records recorded in this window.</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-zinc-800 bg-zinc-950/70 text-zinc-400 font-medium uppercase tracking-wider text-[10px]">
                  <tr>
                    <th className="py-3 px-4">Interviewer</th>
                    <th className="py-3 px-4 text-center">Interviews Conducted</th>
                    <th className="py-3 px-4 text-center">Mean Candidate Score</th>
                    <th className="py-3 px-4 text-center">Score Delta (vs Avg)</th>
                    <th className="py-3 px-4 text-center">Hire Rec Rate</th>
                    <th className="py-3 px-4 text-center">Calibration Signal</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800/60">
                  {interviewers.map((inv: any) => {
                    const delta = inv.score_delta_from_mean ?? 0;
                    const isHarsh = delta < -10;
                    const isLenient = delta > 10;

                    return (
                      <tr key={inv.interviewer_id} className="hover:bg-zinc-800/30 transition-colors">
                        <td className="py-3.5 px-4">
                          <div className="font-semibold text-white">{inv.interviewer_name || 'Interviewer'}</div>
                          <div className="text-[11px] text-zinc-500">{inv.email || ''}</div>
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono font-bold text-white">
                          {inv.interviews_conducted ?? 0}
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          <span className="font-bold text-indigo-300">{inv.average_score_given ?? 0}</span>
                          <span className="text-[10px] text-zinc-500 ml-0.5">/ 100</span>
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono">
                          <span
                            className={`font-semibold ${
                              delta > 0 ? 'text-emerald-400' : delta < 0 ? 'text-rose-400' : 'text-zinc-400'
                            }`}
                          >
                            {delta > 0 ? `+${delta}` : delta}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 text-center font-mono text-zinc-300">
                          {inv.positive_recommendation_rate ?? 0}%
                        </td>
                        <td className="py-3.5 px-4 text-center">
                          {inv.sample_size < 3 ? (
                            <Badge variant="outline" className="border-zinc-700 bg-zinc-900 text-zinc-400 text-[10px]">
                              Low Sample (n &lt; 3)
                            </Badge>
                          ) : isHarsh ? (
                            <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/20 text-[10px]">
                              Tough Grader (-{Math.abs(delta)})
                            </Badge>
                          ) : isLenient ? (
                            <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px]">
                              Lenient Grader (+{delta})
                            </Badge>
                          ) : (
                            <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px]">
                              Well Calibrated
                            </Badge>
                          )}
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
