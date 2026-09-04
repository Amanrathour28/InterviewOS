'use client';

import React, { useState } from 'react';
import { History, X, Clock, FileCode, CheckCircle2, ChevronRight, Eye } from 'lucide-react';
import { CodingSnapshot, useCodingStore } from '@/lib/stores/use-coding-store';

interface SnapshotsDrawerProps {
  onRestoreSnapshot?: (snapshot: CodingSnapshot) => void;
}

export const SnapshotsDrawer: React.FC<SnapshotsDrawerProps> = ({ onRestoreSnapshot }) => {
  const { snapshots, isSnapshotsDrawerOpen, setIsSnapshotsDrawerOpen } = useCodingStore();
  const [selectedSnapshot, setSelectedSnapshot] = useState<CodingSnapshot | null>(null);

  if (!isSnapshotsDrawerOpen) return null;

  const formatReason = (reason: string) => {
    switch (reason) {
      case 'session_start':
        return { label: 'Session Start', color: 'bg-indigo-500/20 text-indigo-300' };
      case 'before_execution':
        return { label: 'Pre-Execution', color: 'bg-emerald-500/20 text-emerald-300' };
      case 'submission':
        return { label: 'Submission', color: 'bg-purple-500/20 text-purple-300' };
      case 'periodic':
        return { label: 'Auto-Save', color: 'bg-slate-500/20 text-slate-300' };
      default:
        return { label: 'Manual Save', color: 'bg-amber-500/20 text-amber-300' };
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm animate-fadeIn">
      <div className="w-full max-w-md h-full bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col">
        {/* Drawer Header */}
        <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-800 bg-slate-950/60">
          <div className="flex items-center gap-2">
            <History className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-semibold text-white">Snapshot History</h2>
          </div>
          <button
            onClick={() => setIsSnapshotsDrawerOpen(false)}
            className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Snapshots List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2.5">
          {snapshots.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              No snapshots recorded yet.
            </div>
          ) : (
            snapshots.map((snap) => {
              const { label, color } = formatReason(snap.reason);
              const dateStr = new Date(snap.created_at).toLocaleTimeString([], {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              });

              return (
                <div
                  key={snap.id}
                  onClick={() => setSelectedSnapshot(snap)}
                  className="p-3 bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 rounded-xl cursor-pointer transition-all hover:border-indigo-500/40 group"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${color}`}>
                      {label}
                    </span>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1 font-mono">
                      <Clock className="w-3 h-3 text-slate-500" />
                      {dateStr}
                    </span>
                  </div>

                  <div className="flex items-center justify-between text-xs text-slate-300">
                    <span className="flex items-center gap-1.5 text-slate-400">
                      <FileCode className="w-3.5 h-3.5 text-slate-500" />
                      {snap.files?.length || 1} file(s)
                    </span>
                    <span className="text-indigo-400 opacity-0 group-hover:opacity-100 flex items-center gap-1 text-[11px] transition-opacity">
                      <Eye className="w-3 h-3" /> Preview
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Snapshot Preview Modal */}
        {selectedSnapshot && (
          <div className="fixed inset-0 z-60 flex items-center justify-center bg-black/70 backdrop-blur-md p-6">
            <div className="w-full max-w-2xl bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden">
              <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <History className="w-4 h-4 text-indigo-400" />
                  <h3 className="text-sm font-semibold text-white">
                    Snapshot Preview — {new Date(selectedSnapshot.created_at).toLocaleString()}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedSnapshot(null)}
                  className="text-slate-400 hover:text-white p-1"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 p-4 overflow-y-auto space-y-4">
                {selectedSnapshot.files?.map((f, i) => (
                  <div key={i} className="border border-slate-800 rounded-xl overflow-hidden">
                    <div className="px-3 py-1.5 bg-slate-950/80 border-b border-slate-800 text-xs font-mono text-indigo-300">
                      {f.path || f.name}
                    </div>
                    <pre className="p-3 bg-slate-950 font-mono text-xs text-slate-300 overflow-x-auto whitespace-pre">
                      {f.content}
                    </pre>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-end gap-2 px-5 py-3 border-t border-slate-800 bg-slate-950/40">
                <button
                  onClick={() => setSelectedSnapshot(null)}
                  className="px-3 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition-colors"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
