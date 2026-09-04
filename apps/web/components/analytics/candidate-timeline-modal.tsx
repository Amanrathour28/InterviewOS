'use client';

import React, { useEffect, useState } from 'react';
import { Clock, X, User, CheckCircle2, XCircle, AlertTriangle, Code2, MessageSquare, Award, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api';

interface CandidateTimelineModalProps {
  workspaceId: string;
  candidateId: string;
  candidateName: string;
  isOpen: boolean;
  onClose: () => void;
}

export function CandidateTimelineModal({
  workspaceId,
  candidateId,
  candidateName,
  isOpen,
  onClose,
}: CandidateTimelineModalProps) {
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<any | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !candidateId) return;

    let mounted = true;
    setLoading(true);
    setError(null);

    apiClient<any>(`/analytics/candidates/${candidateId}/timeline?workspace_id=${workspaceId}`)
      .then((res) => {
        if (mounted) setData(res);
      })
      .catch((err: any) => {
        if (mounted) setError(err.message || 'Failed to load timeline.');
      })
      .finally(() => {
        if (mounted) setLoading(false);
      });

    return () => {
      mounted = false;
    };
  }, [isOpen, candidateId, workspaceId]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-3xl max-h-[85vh] flex flex-col rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl space-y-4 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800/80 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <User className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                {candidateName}
                <span className="text-[11px] font-normal text-zinc-400">Unified Interview Journey</span>
              </h2>
              <p className="text-xs text-zinc-400">Chronological activity across sessions, submissions, and finalized evaluations</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-4 text-xs">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-16 text-zinc-400 space-y-2">
              <RefreshCw className="h-6 w-6 animate-spin text-indigo-400" />
              <p>Loading candidate journey timeline...</p>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center py-12 text-rose-400 text-center">
              {error}
            </div>
          ) : !data || data.total_events === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-zinc-500 text-center">
              <Clock className="h-8 w-8 text-zinc-600 mb-2" />
              <p>No activity records logged for this candidate yet.</p>
            </div>
          ) : (
            <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-[2px] before:bg-zinc-800">
              {data.timeline.map((event: any, idx: number) => {
                const getIcon = () => {
                  if (event.event_type.startsWith('evaluation')) return <Award className="h-3.5 w-3.5 text-emerald-400" />;
                  if (event.event_type.startsWith('code')) return <Code2 className="h-3.5 w-3.5 text-blue-400" />;
                  if (event.event_type.startsWith('session')) return <Clock className="h-3.5 w-3.5 text-amber-400" />;
                  return <MessageSquare className="h-3.5 w-3.5 text-indigo-400" />;
                };

                return (
                  <div key={idx} className="relative group">
                    {/* Bullet */}
                    <div className="absolute -left-[27px] top-1 flex h-6 w-6 items-center justify-center rounded-full bg-zinc-900 border border-zinc-700 group-hover:border-indigo-500 transition-colors">
                      {getIcon()}
                    </div>

                    <div className="rounded-xl border border-zinc-800/80 bg-zinc-900/50 p-3.5 space-y-1.5 hover:border-zinc-700 transition-all">
                      <div className="flex items-center justify-between">
                        <span className="font-semibold text-white capitalize">
                          {event.title || event.event_type.replace(/_/g, ' ')}
                        </span>
                        <span className="text-[11px] text-zinc-500 font-mono">
                          {event.timestamp ? new Date(event.timestamp).toLocaleString() : ''}
                        </span>
                      </div>

                      {event.description && (
                        <p className="text-zinc-300">{event.description}</p>
                      )}

                      {event.data && Object.keys(event.data).length > 0 && (
                        <div className="mt-2 rounded-lg bg-zinc-950/60 p-2 border border-zinc-800/50 text-[11px] text-zinc-400 space-y-1">
                          {Object.entries(event.data).map(([k, v]) => (
                            <div key={k} className="flex items-center justify-between">
                              <span className="text-zinc-500 font-mono capitalize">{k.replace(/_/g, ' ')}:</span>
                              <span className="text-zinc-300 font-medium">{String(v)}</span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-zinc-800/80 pt-3">
          <span className="text-[11px] text-zinc-500">
            Total Logged Events: {data?.total_events || 0}
          </span>
          <Button variant="ghost" size="sm" onClick={onClose} className="text-xs text-zinc-400 hover:text-white">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
