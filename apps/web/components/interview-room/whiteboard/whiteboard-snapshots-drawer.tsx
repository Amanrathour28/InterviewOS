'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { Camera, X, RotateCcw, Plus, Clock, CheckCircle2 } from 'lucide-react';
import { useWhiteboardStore } from '@/lib/stores/use-whiteboard-store';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { RealtimeClient } from '@/lib/realtime/realtime-client';

interface WhiteboardSnapshotsDrawerProps {
  whiteboardId: string;
  isInterviewer: boolean;
  realtimeClient: RealtimeClient | null;
  onSnapshotRestored: (doc: any) => void;
}

export const WhiteboardSnapshotsDrawer: React.FC<WhiteboardSnapshotsDrawerProps> = ({
  whiteboardId,
  isInterviewer,
  realtimeClient,
  onSnapshotRestored,
}) => {
  const {
    isSnapshotsDrawerOpen,
    setIsSnapshotsDrawerOpen,
    snapshots,
    setSnapshots,
    addSnapshot,
  } = useWhiteboardStore();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [snapshotLabel, setSnapshotLabel] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [restoringId, setRestoringId] = useState<string | null>(null);

  const fetchSnapshots = useCallback(async () => {
    try {
      const data = await apiClient<any[]>(`/whiteboards/${whiteboardId}/snapshots`);
      setSnapshots(data || []);
    } catch (err) {
      console.error('Failed to fetch whiteboard snapshots:', err);
    }
  }, [whiteboardId, setSnapshots]);

  useEffect(() => {
    if (isSnapshotsDrawerOpen) {
      fetchSnapshots();
    }
  }, [isSnapshotsDrawerOpen, fetchSnapshots]);

  if (!isSnapshotsDrawerOpen) return null;

  const handleCreateSnapshot = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      const snap = await apiClient<any>(`/whiteboards/${whiteboardId}/snapshots`, {
        method: 'POST',
        body: JSON.stringify({
          label: snapshotLabel || 'Milestone Checkpoint',
          source: 'manual',
        }),
      });
      addSnapshot(snap);
      setSnapshotLabel('');
      setIsCreateOpen(false);
    } catch (err) {
      console.error('Failed to create snapshot:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRestore = async (snapId: string) => {
    if (!confirm('Are you sure you want to restore this milestone? Current whiteboard state will be updated.')) {
      return;
    }

    try {
      setRestoringId(snapId);
      const restored = await apiClient<any>(`/whiteboards/${whiteboardId}/snapshots/${snapId}/restore`, {
        method: 'POST',
      });

      onSnapshotRestored(restored.document);

      // Broadcast restore over realtime socket
      realtimeClient?.emit('whiteboard_restore', {
        snapshot_id: snapId,
        document: restored.document,
      });

      setIsSnapshotsDrawerOpen(false);
    } catch (err) {
      console.error('Failed to restore snapshot:', err);
    } finally {
      setRestoringId(null);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-80 lg:w-96 bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Camera className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-bold text-white">Whiteboard Milestones</h3>
        </div>
        <button
          onClick={() => setIsSnapshotsDrawerOpen(false)}
          className="p-1 text-slate-400 hover:text-white rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Action Bar (Interviewer only) */}
      {isInterviewer && (
        <div className="p-3 border-b border-slate-800/80">
          {!isCreateOpen ? (
            <Button
              size="sm"
              onClick={() => setIsCreateOpen(true)}
              className="w-full bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-8 flex items-center justify-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Capture Milestone Checkpoint
            </Button>
          ) : (
            <form onSubmit={handleCreateSnapshot} className="space-y-2">
              <Input
                value={snapshotLabel}
                onChange={(e) => setSnapshotLabel(e.target.value)}
                placeholder="e.g., Added Caching Layer"
                className="bg-slate-900 border-slate-700 text-xs h-8"
                autoFocus
              />
              <div className="flex justify-end gap-1.5">
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  onClick={() => setIsCreateOpen(false)}
                  className="border-slate-700 text-xs h-7"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isSubmitting}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs h-7"
                >
                  {isSubmitting ? 'Saving...' : 'Save Checkpoint'}
                </Button>
              </div>
            </form>
          )}
        </div>
      )}

      {/* Snapshots List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {snapshots.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No milestone checkpoints captured yet.
          </div>
        ) : (
          snapshots.map((s) => (
            <Card
              key={s.id}
              className="p-3 bg-slate-900/80 border-slate-800 hover:border-slate-700 transition-colors space-y-2"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="font-mono text-[10px] font-bold text-indigo-400 block">
                    #{s.snapshot_number} Checkpoint
                  </span>
                  <h4 className="text-xs font-semibold text-white mt-0.5">{s.label}</h4>
                </div>

                <span className="text-[10px] text-slate-500 font-mono">
                  {new Date(s.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              {isInterviewer && (
                <div className="pt-2 border-t border-slate-800/80 flex justify-end">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={restoringId === s.id}
                    onClick={() => handleRestore(s.id)}
                    className="border-slate-700 text-slate-300 hover:text-white text-[11px] h-7 px-2.5 flex items-center gap-1"
                  >
                    <RotateCcw className="w-3 h-3" />
                    {restoringId === s.id ? 'Restoring...' : 'Restore State'}
                  </Button>
                </div>
              )}
            </Card>
          ))
        )}
      </div>
    </div>
  );
};
