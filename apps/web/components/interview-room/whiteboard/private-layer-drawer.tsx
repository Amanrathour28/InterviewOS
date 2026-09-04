'use client';

import React, { useState, useEffect } from 'react';
import { X, Lock, Save, ShieldAlert, Sparkles, CheckCircle2 } from 'lucide-react';
import { useWhiteboardStore } from '@/lib/stores/use-whiteboard-store';
import { apiClient } from '@/lib/api';
import { RealtimeClient } from '@/lib/realtime/realtime-client';
import { Button } from '@/components/ui/button';

interface PrivateLayerDrawerProps {
  whiteboardId: string;
  realtimeClient: RealtimeClient | null;
}

export const PrivateLayerDrawer: React.FC<PrivateLayerDrawerProps> = ({
  whiteboardId,
  realtimeClient,
}) => {
  const { isPrivateLayerOpen, setIsPrivateLayerOpen, privateNotes, setPrivateNotes } =
    useWhiteboardStore();

  const [localNotes, setLocalNotes] = useState(privateNotes);
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  useEffect(() => {
    setLocalNotes(privateNotes);
  }, [privateNotes]);

  if (!isPrivateLayerOpen) return null;

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setSavedSuccess(false);

      const payload = { notes: localNotes };
      await apiClient(`/whiteboards/${whiteboardId}`, {
        method: 'PATCH',
        body: JSON.stringify({ private_layer: payload }),
      });

      setPrivateNotes(localNotes);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);

      // Emit private update strictly over socket interviewer channel
      realtimeClient?.getSocket()?.emit('whiteboard_private_patch', {
        changes: payload,
      });
    } catch (err) {
      console.error('Failed to save private layer notes:', err);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-80 lg:w-96 bg-slate-950/95 border-l border-purple-900/50 shadow-2xl backdrop-blur-md flex flex-col animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-3.5 border-b border-purple-900/40 bg-purple-950/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1 rounded bg-purple-900/50 text-purple-300">
            <Lock className="w-3.5 h-3.5" />
          </div>
          <div>
            <h3 className="text-xs font-bold text-purple-200">Interviewer Private Layer</h3>
            <p className="text-[10px] text-purple-400/80">Never visible to candidate</p>
          </div>
        </div>
        <button
          onClick={() => setIsPrivateLayerOpen(false)}
          className="p-1 text-slate-400 hover:text-white rounded"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Security Banner */}
      <div className="p-2.5 bg-purple-950/40 border-b border-purple-900/30 flex items-center gap-2 text-[11px] text-purple-300">
        <ShieldAlert className="w-4 h-4 shrink-0 text-purple-400" />
        <span>End-to-end isolated. Filtered server-side from candidate API & WebSockets.</span>
      </div>

      {/* Editor Body */}
      <div className="flex-1 p-3.5 flex flex-col space-y-3">
        <label className="text-[11px] font-semibold text-slate-300">Architecture Evaluation Notes & Hints</label>
        <textarea
          value={localNotes}
          onChange={(e) => setLocalNotes(e.target.value)}
          placeholder="Private scoring rubric notes, architecture bottleneck observations, planned follow-up questions..."
          className="flex-1 w-full bg-slate-900/90 border border-slate-800 text-xs text-slate-200 font-mono rounded-lg p-3 focus:outline-none focus:ring-1 focus:ring-purple-500 resize-none"
        />
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-purple-900/40 bg-slate-900/40 flex items-center justify-between">
        {savedSuccess ? (
          <span className="text-xs text-emerald-400 flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> Saved Privately
          </span>
        ) : (
          <span className="text-[10px] text-slate-500">Auto-saved to session</span>
        )}

        <Button
          size="sm"
          onClick={handleSave}
          disabled={isSaving}
          className="bg-purple-600 hover:bg-purple-500 text-white text-xs h-7 px-3 flex items-center gap-1.5"
        >
          <Save className="w-3 h-3" />
          {isSaving ? 'Saving...' : 'Save Notes'}
        </Button>
      </div>
    </div>
  );
};
