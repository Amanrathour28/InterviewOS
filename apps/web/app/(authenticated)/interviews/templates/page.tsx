'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  LayoutTemplate,
  ArrowLeft,
  Search,
  Plus,
  Clock,
  Layers,
  Sparkles,
  ChevronRight,
  AlertCircle,
  Check,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { apiClient } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface TemplateRound {
  id: string;
  name: string;
  round_type: string;
  sequence: number;
  duration_minutes: number;
  difficulty: string;
}

interface TemplateItem {
  id: string;
  workspace_id?: string;
  name: string;
  description: string;
  interview_type: string;
  difficulty: string;
  total_duration_minutes: number;
  is_system: boolean;
  rounds: TemplateRound[];
}

export default function InterviewTemplatesPage() {
  const { activeWorkspace } = useAuthStore();
  const router = useRouter();

  const [templates, setTemplates] = useState<TemplateItem[]>([]);
  const [search, setSearch] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Instant Template Instantiate Modal
  const [selectedTemplate, setSelectedTemplate] = useState<TemplateItem | null>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState('');
  const [customTitle, setCustomTitle] = useState('');
  const [isInstantiating, setIsInstantiating] = useState(false);
  const [instantiateError, setInstantiateError] = useState<string | null>(null);

  const fetchTemplates = useCallback(async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    setError(null);

    try {
      let url = `/interview-templates?workspace_id=${activeWorkspace.id}&page_size=50`;
      if (search.trim()) url += `&search=${encodeURIComponent(search.trim())}`;
      const res = await apiClient<any>(url);
      setTemplates(res.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load interview templates');
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, search]);

  useEffect(() => {
    fetchTemplates();
  }, [fetchTemplates]);

  const handleOpenUseModal = async (tpl: TemplateItem) => {
    if (!activeWorkspace) return;
    setSelectedTemplate(tpl);
    setCustomTitle(`${tpl.name} - Technical Interview`);
    setInstantiateError(null);

    try {
      const res = await apiClient<any>(`/candidates?workspace_id=${activeWorkspace.id}&page_size=50`);
      setCandidates(res.items || []);
      if (res.items?.length > 0) {
        setSelectedCandidateId(res.items[0].id);
      }
    } catch (err: any) {
      setInstantiateError('Failed to load candidate list');
    }
  };

  const handleInstantiate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTemplate || !activeWorkspace || !selectedCandidateId) return;

    setIsInstantiating(true);
    setInstantiateError(null);

    try {
      const res = await apiClient<any>(`/interviews/from-template/${selectedTemplate.id}`, {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: activeWorkspace.id,
          candidate_id: selectedCandidateId,
          title: customTitle.trim() || selectedTemplate.name,
        }),
      });
      router.push(`/interviews/${res.id}`);
    } catch (err: any) {
      setInstantiateError(err.message || 'Failed to instantiate interview from template');
      setIsInstantiating(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Back button */}
      <div>
        <Link
          href="/interviews"
          className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Interviews
        </Link>
      </div>

      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <LayoutTemplate className="h-6 w-6 text-indigo-400" />
            Interview Templates Gallery
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Standardized loops and pre-configured round sequences for consistent engineering evaluations.
          </p>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search templates by role or keywords..."
          className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-3 text-xs text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none"
        />
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-950/20 text-xs text-rose-400">
          {error}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="py-20 flex flex-col items-center justify-center text-center">
          <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-xs text-zinc-500">Loading templates...</p>
        </div>
      )}

      {/* Templates Grid */}
      {!isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {templates.map((tpl) => (
            <Card
              key={tpl.id}
              className="bg-[#0e0f15] border-zinc-800/80 p-5 flex flex-col justify-between space-y-4 hover:border-zinc-700 transition-all"
            >
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <Badge variant="default" className="text-[10px] uppercase">
                    {tpl.interview_type.replace('_', ' ')}
                  </Badge>
                  {tpl.is_system && (
                    <span className="text-[10px] text-indigo-400 font-semibold uppercase tracking-wider flex items-center gap-1">
                      <Sparkles className="h-3 w-3" /> System
                    </span>
                  )}
                </div>

                <div>
                  <h3 className="text-base font-bold text-white line-clamp-1">{tpl.name}</h3>
                  <p className="text-xs text-zinc-400 line-clamp-2 mt-1 leading-relaxed">
                    {tpl.description || 'Pre-configured hiring loop.'}
                  </p>
                </div>

                {/* Rounds preview */}
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                    Rounds ({tpl.rounds?.length || 0})
                  </span>
                  <div className="space-y-1">
                    {tpl.rounds?.map((r, i) => (
                      <div
                        key={r.id || i}
                        className="p-1.5 rounded bg-zinc-950 border border-zinc-800/60 text-[11px] flex items-center justify-between text-zinc-300"
                      >
                        <span className="truncate max-w-[180px]">{r.name}</span>
                        <span className="text-[10px] text-zinc-500">{r.duration_minutes}m</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pt-3 border-t border-zinc-800 flex items-center justify-between">
                <span className="text-xs text-zinc-500 flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {tpl.total_duration_minutes} mins total
                </span>

                <Button size="sm" onClick={() => handleOpenUseModal(tpl)} className="text-xs font-semibold">
                  Use Template
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Instantiate Modal */}
      {selectedTemplate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <div>
                <h3 className="text-base font-bold text-white">Instantiate Template</h3>
                <p className="text-xs text-zinc-400">{selectedTemplate.name}</p>
              </div>
              <button
                onClick={() => setSelectedTemplate(null)}
                className="text-zinc-500 hover:text-white"
              >
                ✕
              </button>
            </div>

            {instantiateError && (
              <div className="p-2.5 rounded bg-rose-950/20 border border-rose-500/30 text-xs text-rose-400">
                {instantiateError}
              </div>
            )}

            <form onSubmit={handleInstantiate} className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-zinc-300 font-semibold">Interview Title</label>
                <input
                  type="text"
                  required
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-zinc-300 font-semibold">Select Candidate *</label>
                {candidates.length === 0 ? (
                  <p className="text-zinc-500 py-1">No candidates found in workspace.</p>
                ) : (
                  <select
                    value={selectedCandidateId}
                    onChange={(e) => setSelectedCandidateId(e.target.value)}
                    className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                  >
                    {candidates.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.first_name} {c.last_name} ({c.email})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedTemplate(null)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  disabled={isInstantiating || candidates.length === 0}
                  className="text-xs font-semibold"
                >
                  {isInstantiating ? 'Cloning...' : 'Launch from Template'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
