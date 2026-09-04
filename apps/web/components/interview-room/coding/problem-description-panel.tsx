'use client';

import React, { useState } from 'react';
import { BookOpen, Copy, Check, ChevronRight, Layers, Sparkles, AlertCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { ProblemDetail } from '@/lib/stores/use-coding-store';

interface ProblemDescriptionPanelProps {
  problem: ProblemDetail | null;
  isLoading?: boolean;
}

export const ProblemDescriptionPanel: React.FC<ProblemDescriptionPanelProps> = ({ problem, isLoading }) => {
  const [copiedExampleIndex, setCopiedExampleIndex] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="p-4 space-y-4 animate-pulse">
        <div className="h-6 w-3/4 bg-slate-800/80 rounded" />
        <div className="h-4 w-1/3 bg-slate-800/50 rounded" />
        <div className="space-y-2 pt-4">
          <div className="h-3 w-full bg-slate-800/40 rounded" />
          <div className="h-3 w-5/6 bg-slate-800/40 rounded" />
        </div>
      </div>
    );
  }

  if (!problem) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-6 text-center text-slate-500 space-y-2">
        <BookOpen className="w-8 h-8 text-slate-600 mb-1" />
        <p className="text-xs font-medium text-slate-400">No Problem Assigned</p>
        <p className="text-[11px] text-slate-500 max-w-[200px]">
          The interviewer can assign a problem from the Problem Library.
        </p>
      </div>
    );
  }

  const ver = problem.current_version;
  const examples = ver?.examples || [];
  const constraints = ver?.constraints || [];

  const handleCopy = (text: string, index: number) => {
    navigator.clipboard.writeText(text);
    setCopiedExampleIndex(index);
    setTimeout(() => setCopiedExampleIndex(null), 2000);
  };

  const getDifficultyBadge = (difficulty: string) => {
    switch (difficulty?.toLowerCase()) {
      case 'easy':
        return <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 font-mono text-[10px]">Easy</Badge>;
      case 'medium':
        return <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20 font-mono text-[10px]">Medium</Badge>;
      case 'hard':
        return <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/20 font-mono text-[10px]">Hard</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px]">{difficulty}</Badge>;
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 space-y-5 text-slate-200 text-xs select-text">
      {/* Problem Header */}
      <div className="space-y-2 border-b border-slate-800 pb-3">
        <div className="flex items-start justify-between gap-2">
          <h2 className="text-base font-bold text-white leading-snug">{problem.title}</h2>
          {getDifficultyBadge(problem.difficulty)}
        </div>
        <div className="flex items-center gap-2 text-[11px] text-slate-400">
          <span className="capitalize">{problem.category.replace('_', ' ')}</span>
          <span>•</span>
          <span>{problem.estimated_duration_minutes || 30} mins</span>
        </div>
      </div>

      {/* Problem Statement */}
      <div className="space-y-2.5">
        <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Description</h3>
        <div className="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed space-y-2">
          {ver?.problem_statement || problem.short_description}
        </div>
      </div>

      {/* Examples */}
      {examples.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Examples</h3>
          {examples.map((ex, idx) => (
            <div key={idx} className="bg-slate-900/90 border border-slate-800/80 rounded-lg p-3 space-y-2">
              <div className="flex items-center justify-between text-[11px] font-semibold text-slate-300">
                <span>Example {idx + 1}</span>
                <button
                  onClick={() => handleCopy(ex.input, idx)}
                  className="text-slate-500 hover:text-slate-300 flex items-center gap-1 text-[10px]"
                >
                  {copiedExampleIndex === idx ? (
                    <>
                      <Check className="w-3 h-3 text-emerald-400" /> Copied
                    </>
                  ) : (
                    <>
                      <Copy className="w-3 h-3" /> Copy Input
                    </>
                  )}
                </button>
              </div>

              <div className="space-y-1.5 font-mono text-[11px]">
                <div className="bg-slate-950 p-2 rounded border border-slate-800/60">
                  <span className="text-slate-500 select-none">Input: </span>
                  <span className="text-slate-200">{ex.input}</span>
                </div>
                <div className="bg-slate-950 p-2 rounded border border-slate-800/60">
                  <span className="text-slate-500 select-none">Output: </span>
                  <span className="text-emerald-400">{ex.output}</span>
                </div>
                {ex.explanation && (
                  <div className="text-[11px] font-sans text-slate-400 pt-1 leading-normal">
                    <span className="font-semibold text-slate-300">Explanation: </span>
                    {ex.explanation}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Constraints */}
      {constraints.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-[11px] font-bold uppercase tracking-wider text-slate-400">Constraints</h3>
          <ul className="list-disc list-inside space-y-1 text-slate-300 font-mono text-[11px] bg-slate-900/60 p-3 rounded-lg border border-slate-800/80">
            {constraints.map((c, idx) => (
              <li key={idx}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
};
