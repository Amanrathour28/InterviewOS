'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { BookOpen, Search, X, Check, Plus, Clock } from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { RealtimeClient } from '@/lib/realtime/realtime-client';

interface InterviewerProblemDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  realtimeClient: RealtimeClient | null;
  onProblemAssigned: () => void;
}

export const InterviewerProblemDrawer: React.FC<InterviewerProblemDrawerProps> = ({
  isOpen,
  onClose,
  sessionId,
  realtimeClient,
  onProblemAssigned,
}) => {
  const [problems, setProblems] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [selectedDifficulty, setSelectedDifficulty] = useState('all');
  const [isLoading, setIsLoading] = useState(false);
  const [assigningId, setAssigningId] = useState<string | null>(null);

  const fetchProblems = useCallback(async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (selectedDifficulty !== 'all') params.append('difficulty', selectedDifficulty);

      const data = await apiClient<any>(`/coding/problems?${params.toString()}`);
      setProblems(data.items || []);
    } catch (err) {
      console.error('Failed to fetch library problems:', err);
    } finally {
      setIsLoading(false);
    }
  }, [search, selectedDifficulty]);

  useEffect(() => {
    if (isOpen) {
      fetchProblems();
    }
  }, [isOpen, fetchProblems]);

  const handleAssignProblem = async (problemId: string) => {
    try {
      setAssigningId(problemId);
      await apiClient(`/coding/sessions/${sessionId}/problems/assign`, {
        method: 'POST',
        body: JSON.stringify({ problem_id: problemId }),
      });

      realtimeClient?.dispatchEvent('CODING_PROBLEM_ASSIGNED', {
        problem_id: problemId,
        session_id: sessionId,
      });

      onProblemAssigned();
      onClose();
    } catch (err) {
      console.error('Failed to assign problem:', err);
    } finally {
      setAssigningId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-md bg-slate-950 border-l border-slate-800 h-full flex flex-col shadow-2xl animate-in slide-in-from-right duration-200">
        {/* Header */}
        <div className="p-4 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <BookOpen className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-bold text-white">Assign Problem to Candidate</h2>
          </div>
          <button onClick={onClose} className="p-1 text-slate-400 hover:text-white rounded">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Search & Filters */}
        <div className="p-3 border-b border-slate-800/80 space-y-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search problems..."
              className="pl-8 bg-slate-900 border-slate-800 text-xs h-8"
            />
          </div>

          <div className="flex gap-1 text-[10px]">
            {['all', 'easy', 'medium', 'hard'].map((d) => (
              <button
                key={d}
                onClick={() => setSelectedDifficulty(d)}
                className={`px-2 py-1 rounded capitalize font-medium ${
                  selectedDifficulty === d
                    ? 'bg-indigo-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200'
                }`}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        {/* Problem List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
          {isLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-20 bg-slate-900/60 rounded-lg animate-pulse" />
              ))}
            </div>
          ) : problems.length === 0 ? (
            <div className="text-center py-12 text-slate-500 text-xs">
              No matching problems found in library.
            </div>
          ) : (
            problems.map((p) => (
              <Card
                key={p.id}
                className="p-3 bg-slate-900/80 border-slate-800 hover:border-slate-700 transition-colors space-y-2"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-xs font-bold text-white">{p.title}</h3>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <span className="text-[10px] text-slate-400 capitalize">{p.category.replace('_', ' ')}</span>
                      <span className="text-slate-600">•</span>
                      <span className="text-[10px] text-slate-400">{p.estimated_duration_minutes || 30}m</span>
                    </div>
                  </div>
                  <Badge
                    variant="outline"
                    className={`text-[9px] font-mono capitalize ${
                      p.difficulty === 'easy'
                        ? 'text-emerald-400 border-emerald-500/20'
                        : p.difficulty === 'hard'
                        ? 'text-rose-400 border-rose-500/20'
                        : 'text-amber-400 border-amber-500/20'
                    }`}
                  >
                    {p.difficulty}
                  </Badge>
                </div>

                <p className="text-[11px] text-slate-400 line-clamp-2">{p.short_description}</p>

                <div className="pt-2 border-t border-slate-800/80 flex justify-end">
                  <Button
                    size="sm"
                    disabled={assigningId === p.id}
                    onClick={() => handleAssignProblem(p.id)}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white text-[11px] h-7 px-3"
                  >
                    {assigningId === p.id ? 'Assigning...' : 'Assign Problem'}
                  </Button>
                </div>
              </Card>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
