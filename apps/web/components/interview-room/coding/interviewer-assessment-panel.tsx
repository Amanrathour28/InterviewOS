'use client';

import React from 'react';
import { X, Award, CheckCircle2, XCircle, Clock, ShieldCheck, FileCode } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { ProblemDetail, SubmissionItem } from '@/lib/stores/use-coding-store';

interface InterviewerAssessmentPanelProps {
  isOpen: boolean;
  onClose: () => void;
  problem: ProblemDetail | null;
  submissions: SubmissionItem[];
}

export const InterviewerAssessmentPanel: React.FC<InterviewerAssessmentPanelProps> = ({
  isOpen,
  onClose,
  problem,
  submissions,
}) => {
  if (!isOpen) return null;

  const latestSubmission = submissions.length > 0 ? submissions[0] : null;
  const bestScore = submissions.reduce((max, s) => (s.score > max ? s.score : max), 0);
  const isAccepted = submissions.some((s) => s.status.toLowerCase() === 'accepted');

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md bg-slate-950 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Award className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-bold text-white">Assessment Diagnostics</h2>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white rounded">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Candidate Score Summary Card */}
          <Card className="p-4 bg-slate-900/90 border-slate-800 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Candidate Best Score</span>
              <span className="text-base font-bold text-white font-mono">{bestScore}%</span>
            </div>

            <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-xs">
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <span className="text-[10px] text-slate-500 block">Assessment Verdict</span>
                <span className={`font-semibold ${isAccepted ? 'text-emerald-400' : 'text-slate-300'}`}>
                  {isAccepted ? 'Passed' : 'In Progress'}
                </span>
              </div>
              <div className="bg-slate-950 p-2 rounded border border-slate-800/80">
                <span className="text-[10px] text-slate-500 block">Total Submissions</span>
                <span className="font-semibold text-white font-mono">{submissions.length}</span>
              </div>
            </div>
          </Card>

          {/* Active Problem Summary */}
          {problem && (
            <Card className="p-4 bg-slate-900/90 border-slate-800 space-y-2">
              <h3 className="text-xs font-bold text-white">{problem.title}</h3>
              <div className="flex items-center gap-2 text-[11px] text-slate-400">
                <span className="capitalize">{problem.difficulty}</span>
                <span>•</span>
                <span className="capitalize">{problem.category.replace('_', ' ')}</span>
              </div>
              <div className="pt-2 border-t border-slate-800 text-[11px] text-slate-400">
                Total Test Cases in Suite:{' '}
                <strong className="text-slate-200">
                  {problem.current_version?.test_cases?.length || 0}
                </strong>
              </div>
            </Card>
          )}

          {/* Submissions Feed */}
          <div className="space-y-2">
            <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Submission Attempts</h4>
            {submissions.length === 0 ? (
              <p className="text-xs text-slate-500">No submissions submitted yet.</p>
            ) : (
              submissions.map((s) => (
                <div
                  key={s.id}
                  className="p-3 bg-slate-900/80 border border-slate-800 rounded-lg space-y-1.5 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono font-bold text-slate-300">Attempt #{s.submission_number}</span>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {s.status}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-slate-400">
                    <span>
                      Passed: <strong className="text-white">{s.tests_passed}/{s.total_tests}</strong>
                    </span>
                    <span>Runtime: <strong className="text-white">{s.runtime_ms} ms</strong></span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
