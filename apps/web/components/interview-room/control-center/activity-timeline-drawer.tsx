'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  X,
  Clock,
  Activity,
  Code2,
  PenTool,
  MessageSquare,
  Users,
  Layers,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface ActivityTimelineDrawerProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
}

export const ActivityTimelineDrawer: React.FC<ActivityTimelineDrawerProps> = ({
  sessionId,
  isOpen,
  onClose,
}) => {
  const [timeline, setTimeline] = useState<any[]>([]);
  const [category, setCategory] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);

  const fetchTimeline = useCallback(async () => {
    try {
      setIsLoading(true);
      const url = category === 'all'
        ? `/sessions/${sessionId}/timeline`
        : `/sessions/${sessionId}/timeline?category=${category}`;
      const data = await apiClient<any[]>(url);
      setTimeline(data || []);
    } catch (err) {
      console.error('Failed to load timeline:', err);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, category]);

  useEffect(() => {
    if (isOpen) {
      fetchTimeline();
    }
  }, [isOpen, fetchTimeline]);

  if (!isOpen) return null;

  const categories = [
    { id: 'all', label: 'All' },
    { id: 'stages', label: 'Stages' },
    { id: 'coding', label: 'Coding' },
    { id: 'whiteboard', label: 'Whiteboard' },
    { id: 'chat', label: 'Chat' },
    { id: 'participants', label: 'People' },
  ];

  const getCategoryIcon = (cat: string) => {
    switch (cat) {
      case 'stages':
        return <Layers className="w-3.5 h-3.5 text-indigo-400" />;
      case 'coding':
        return <Code2 className="w-3.5 h-3.5 text-cyan-400" />;
      case 'whiteboard':
        return <PenTool className="w-3.5 h-3.5 text-purple-400" />;
      case 'chat':
        return <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />;
      case 'participants':
        return <Users className="w-3.5 h-3.5 text-amber-400" />;
      default:
        return <Activity className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-80 lg:w-96 bg-slate-950 border-l border-slate-800 shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
      {/* Header */}
      <div className="p-3.5 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          <h3 className="text-xs font-bold text-white">Live Activity Timeline</h3>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={fetchTimeline}
            className="p-1 text-slate-400 hover:text-white rounded"
            title="Refresh"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white rounded">
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Category Pills */}
      <div className="p-2 border-b border-slate-800/80 flex items-center gap-1 overflow-x-auto no-scrollbar">
        {categories.map((c) => (
          <button
            key={c.id}
            onClick={() => setCategory(c.id)}
            className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition-colors shrink-0 ${
              category === c.id
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200'
            }`}
          >
            {c.label}
          </button>
        ))}
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {timeline.length === 0 ? (
          <div className="text-center py-12 text-slate-500 text-xs">
            No activity events recorded for this filter.
          </div>
        ) : (
          timeline.map((item) => (
            <Card
              key={item.id}
              className="p-3 bg-slate-900/80 border-slate-800 hover:border-slate-700 transition-colors space-y-1.5 text-xs"
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex items-center gap-1.5">
                  {getCategoryIcon(item.category)}
                  <span className="font-semibold text-white text-xs">{item.title}</span>
                </div>
                <span className="text-[10px] font-mono text-slate-500 shrink-0">
                  {new Date(item.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
              </div>

              <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800/60 font-mono">
                <span>By: {item.actor_name}</span>
                <span>#{item.sequence}</span>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  );
};
