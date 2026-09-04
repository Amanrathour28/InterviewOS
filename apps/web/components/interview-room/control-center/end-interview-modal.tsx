'use client';

import React, { useState } from 'react';
import { AlertCircle, CheckCircle2, X, ShieldAlert, LogOut } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface EndInterviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirmEnd: () => void;
  isSubmitting?: boolean;
}

export const EndInterviewModal: React.FC<EndInterviewModalProps> = ({
  isOpen,
  onClose,
  onConfirmEnd,
  isSubmitting,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 animate-in fade-in duration-200">
      <div className="bg-slate-950 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/30">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white">End Interview Session?</h3>
              <p className="text-xs text-slate-400">This action will conclude the live interview for all participants.</p>
            </div>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Verification Checklist */}
        <div className="p-3.5 bg-slate-900/80 border border-slate-800 rounded-xl space-y-2 text-xs text-slate-300">
          <div className="text-[11px] font-mono text-slate-400 uppercase tracking-wider font-semibold">
            Automated Archival Pre-checks:
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Candidate Monaco code and submissions are preserved</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Whiteboard diagrams and milestone snapshots are finalized</span>
          </div>
          <div className="flex items-center gap-2 text-slate-300">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span>Interviewer private notes and timeline events are secured</span>
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={onClose}
            disabled={isSubmitting}
            className="border-slate-800 text-slate-300 hover:text-white text-xs h-9 px-4"
          >
            Cancel
          </Button>
          <Button
            type="button"
            onClick={onConfirmEnd}
            disabled={isSubmitting}
            className="bg-rose-600 hover:bg-rose-500 text-white text-xs h-9 px-4 flex items-center gap-1.5 shadow-lg shadow-rose-600/20"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>{isSubmitting ? 'Concluding...' : 'Confirm & End Interview'}</span>
          </Button>
        </div>
      </div>
    </div>
  );
};
