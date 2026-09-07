'use client';

import React from 'react';
import { Check, ChevronRight, Sparkles } from 'lucide-react';

export interface StageItem {
  id: string;
  label: string;
  shortLabel: string;
}

export const INTERVIEW_STAGES: StageItem[] = [
  { id: 'introduction', label: 'Introduction', shortLabel: 'Intro' },
  { id: 'behavioral', label: 'Behavioral & Experience', shortLabel: 'Behavioral' },
  { id: 'technical', label: 'Core Technical', shortLabel: 'Technical' },
  { id: 'coding', label: 'Live Coding', shortLabel: 'Coding' },
  { id: 'system_design', label: 'System Design', shortLabel: 'Architecture' },
  { id: 'closing', label: 'Q&A & Closing', shortLabel: 'Closing' },
];

interface StageStepperProps {
  currentStage: string;
  isInterviewer: boolean;
  onSelectStage?: (stageId: string) => void;
}

export const StageStepper: React.FC<StageStepperProps> = ({
  currentStage,
  isInterviewer,
  onSelectStage,
}) => {
  const currentIndex = INTERVIEW_STAGES.findIndex((s) => s.id === currentStage);

  return (
    <div className="flex items-center gap-1 overflow-x-auto py-1 px-2 select-none no-scrollbar">
      {INTERVIEW_STAGES.map((stage, idx) => {
        const isCurrent = stage.id === currentStage;
        const isPast = currentIndex > -1 && idx < currentIndex;
        const isClickable = isInterviewer && !isCurrent;

        return (
          <React.Fragment key={stage.id}>
            <button
              onClick={() => isClickable && onSelectStage?.(stage.id)}
              disabled={!isClickable}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-all ${
                isCurrent
                  ? 'bg-indigo-600 text-white shadow-sm ring-1 ring-indigo-400/50'
                  : isPast
                  ? 'bg-slate-800/80 text-slate-300 hover:bg-slate-700'
                  : 'bg-slate-900/40 text-slate-500 hover:text-slate-400'
              } ${isClickable ? 'cursor-pointer' : 'cursor-default'}`}
            >
              {isPast ? (
                <Check className="w-3 h-3 text-emerald-400" />
              ) : (
                <span
                  className={`w-3.5 h-3.5 rounded-full text-[9px] flex items-center justify-center font-mono ${
                    isCurrent ? 'bg-white text-indigo-700 font-bold' : 'bg-slate-800 text-slate-400'
                  }`}
                >
                  {idx + 1}
                </span>
              )}
              <span className="hidden xl:inline">{stage.label}</span>
              <span className={`hidden md:inline xl:hidden ${isCurrent ? '!inline font-bold' : ''}`}>
                {stage.shortLabel}
              </span>
            </button>

            {idx < INTERVIEW_STAGES.length - 1 && (
              <ChevronRight className="w-3 h-3 text-slate-600 shrink-0" />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
