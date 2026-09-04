'use client';

import React from 'react';
import { Clock, CheckCircle2, XCircle, AlertTriangle, FileCode, Check } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { SubmissionItem } from '@/lib/stores/use-coding-store';

interface SubmissionHistoryPanelProps {
  submissions: SubmissionItem[];
  isLoading?: boolean;
}

export const SubmissionHistoryPanel: React.FC<SubmissionHistoryPanelProps> = ({ submissions, isLoading }) => {
  if (isLoading) {
    return (
      <div className="p-4 space-y-2">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-slate-900/60 rounded border border-slate-800 animate-pulse" />
        ))}
      </div>
    );
  }

  if (submissions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center text-slate-500 space-y-1">
        <FileCode className="w-6 h-6 text-slate-600 mb-1" />
        <p className="text-xs font-medium text-slate-400">No Submissions Yet</p>
        <p className="text-[11px] text-slate-500">
          Click &quot;Submit Solution&quot; to evaluate your code against the full assessment test suite.
        </p>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case 'accepted':
        return (
          <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px] flex items-center gap-1 font-mono">
            <CheckCircle2 className="w-3 h-3" /> Accepted
          </Badge>
        );
      case 'wrong_answer':
        return (
          <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/20 text-[10px] flex items-center gap-1 font-mono">
            <XCircle className="w-3 h-3" /> Wrong Answer
          </Badge>
        );
      case 'time_limit_exceeded':
        return (
          <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px] flex items-center gap-1 font-mono">
            <AlertTriangle className="w-3 h-3" /> TLE
          </Badge>
        );
      default:
        return (
          <Badge variant="outline" className="text-[10px] font-mono">
            {status}
          </Badge>
        );
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 space-y-2.5">
      {submissions.map((sub) => (
        <div
          key={sub.id}
          className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg flex items-center justify-between gap-3 text-xs"
        >
          <div className="flex items-center gap-3">
            <span className="font-mono text-[11px] font-bold text-slate-400">
              #{sub.submission_number}
            </span>
            {getStatusBadge(sub.status)}
            <span className="text-[11px] text-slate-300">
              Score: <strong className="text-white">{sub.score}%</strong>
            </span>
            <span className="text-[11px] text-slate-400">
              ({sub.tests_passed}/{sub.total_tests} tests)
            </span>
          </div>

          <div className="flex items-center gap-3 text-[11px] text-slate-500 font-mono">
            <span>{sub.runtime_ms} ms</span>
            <span>{new Date(sub.submitted_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
          </div>
        </div>
      ))}
    </div>
  );
};
