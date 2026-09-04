'use client';

import React from 'react';
import {
  Play,
  Pause,
  Activity,
  FileText,
  LogOut,
  Layers,
  Sparkles,
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface QuickActionsMenuProps {
  isInterviewer: boolean;
  isPaused: boolean;
  status: string;
  onTogglePause: () => void;
  onOpenTimeline: () => void;
  onOpenEndModal: () => void;
}

export const QuickActionsMenu: React.FC<QuickActionsMenuProps> = ({
  isInterviewer,
  isPaused,
  status,
  onTogglePause,
  onOpenTimeline,
  onOpenEndModal,
}) => {
  if (!isInterviewer) return null;

  return (
    <div className="flex items-center gap-1.5 select-none">
      {/* Pause / Resume Button */}
      {status === 'active' || status === 'paused' ? (
        <button
          onClick={onTogglePause}
          className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors border ${
            isPaused
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
              : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700 hover:text-white'
          }`}
          title={isPaused ? 'Resume Interview' : 'Pause Interview'}
        >
          {isPaused ? (
            <>
              <Play className="w-3 h-3 fill-current text-amber-400" />
              <span>Resume</span>
            </>
          ) : (
            <>
              <Pause className="w-3 h-3 text-slate-400" />
              <span>Pause</span>
            </>
          )}
        </button>
      ) : null}

      {/* Activity Timeline Drawer Toggle */}
      <button
        onClick={onOpenTimeline}
        className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-slate-300 bg-slate-800 hover:bg-slate-700 hover:text-white border border-slate-700 transition-colors"
        title="Live Activity Timeline"
      >
        <Activity className="w-3.5 h-3.5 text-indigo-400" />
        <span className="hidden lg:inline">Timeline</span>
      </button>

      {/* End Interview */}
      <button
        onClick={onOpenEndModal}
        className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium text-rose-300 bg-rose-950/40 hover:bg-rose-900/60 border border-rose-800/60 transition-colors"
        title="End Interview"
      >
        <LogOut className="w-3.5 h-3.5 text-rose-400" />
        <span>End</span>
      </button>
    </div>
  );
};
