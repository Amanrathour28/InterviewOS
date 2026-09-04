'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Terminal,
  Search,
  Plus,
  Filter,
  CheckCircle2,
  AlertCircle,
  Clock,
  Users,
  Layers,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  LayoutTemplate,
  Calendar,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { apiClient } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface InterviewItem {
  id: string;
  workspace_id: string;
  candidate_id: string;
  candidate_name?: string;
  candidate_email?: string;
  job_id?: string;
  job_title?: string;
  title: string;
  description: string;
  interview_type: string;
  status: string;
  difficulty: string;
  duration_minutes: number;
  round_count: number;
  participant_count: number;
  is_ready: boolean;
  created_at: string;
}

export default function InterviewsPage() {
  const { activeWorkspace } = useAuthStore();

  const [interviews, setInterviews] = useState<InterviewItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInterviews = useCallback(async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    setError(null);

    try {
      let url = `/interviews?workspace_id=${activeWorkspace.id}&page=${page}&page_size=12`;
      if (statusFilter !== 'all') {
        url += `&status=${statusFilter}`;
      }
      if (typeFilter !== 'all') {
        url += `&interview_type=${typeFilter}`;
      }
      if (search.trim()) {
        url += `&search=${encodeURIComponent(search.trim())}`;
      }

      const res = await apiClient<any>(url);
      setInterviews(res.items || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 0);
    } catch (err: any) {
      setError(err.message || 'Failed to load interviews');
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, page, statusFilter, typeFilter, search]);

  useEffect(() => {
    fetchInterviews();
  }, [fetchInterviews]);

  const getStatusBadge = (status: string, isReady: boolean) => {
    switch (status) {
      case 'ready':
        return <Badge variant="success">READY</Badge>;
      case 'scheduled':
        return <Badge variant="outline" className="text-cyan-400 border-cyan-400/30">SCHEDULED</Badge>;
      case 'in_progress':
        return <Badge variant="default" className="bg-primary/20 text-primary">LIVE</Badge>;
      case 'completed':
        return <Badge variant="success" className="bg-emerald-500/20 text-emerald-300">COMPLETED</Badge>;
      case 'cancelled':
        return <Badge variant="outline" className="text-zinc-500">CANCELLED</Badge>;
      default:
        return (
          <Badge variant="outline" className="text-amber-400 border-amber-400/30">
            DRAFT
          </Badge>
        );
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'coding':
        return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20';
      case 'system_design':
        return 'text-purple-400 bg-purple-500/10 border-purple-500/20';
      case 'behavioral':
        return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
      case 'technical':
        return 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20';
      default:
        return 'text-zinc-400 bg-zinc-500/10 border-zinc-500/20';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Terminal className="h-6 w-6 text-indigo-400" />
            Interview Configurations
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Workspace: <strong className="text-zinc-200">{activeWorkspace?.name || 'Default'}</strong> •{' '}
            {total} configured interviews
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Link href="/interviews/questions">
            <Button variant="outline" size="sm" className="text-xs border-zinc-800 text-zinc-300 hover:text-white">
              <BookOpen className="h-3.5 w-3.5 mr-1.5 text-zinc-400" />
              Question Library
            </Button>
          </Link>
          <Link href="/interviews/templates">
            <Button variant="outline" size="sm" className="text-xs border-zinc-800 text-zinc-300 hover:text-white">
              <LayoutTemplate className="h-3.5 w-3.5 mr-1.5 text-zinc-400" />
              Templates
            </Button>
          </Link>
          <Link href="/interviews/new">
            <Button size="sm" className="text-xs font-semibold gap-1.5 shadow-lg shadow-primary/20">
              <Plus className="h-3.5 w-3.5" />
              Configure Interview
            </Button>
          </Link>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col md:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by title, candidate, or description..."
            className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-3 text-xs text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none"
          />
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-1 overflow-x-auto w-full md:w-auto pb-1 md:pb-0">
          {['all', 'draft', 'ready', 'scheduled', 'completed'].map((st) => (
            <button
              key={st}
              onClick={() => {
                setStatusFilter(st);
                setPage(1);
              }}
              className={`px-2.5 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider transition-all whitespace-nowrap ${
                statusFilter === st
                  ? 'bg-zinc-800 text-white font-semibold'
                  : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/60'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-rose-500/30 bg-rose-950/20 p-3 text-xs text-rose-400">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="py-20 flex flex-col items-center justify-center text-center">
          <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
          <p className="text-xs text-zinc-500">Loading interview sessions...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && interviews.length === 0 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-12 text-center">
          <div className="h-12 w-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500 mx-auto mb-3">
            <Terminal className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-white mb-1">No interviews found</h3>
          <p className="text-xs text-zinc-400 max-w-sm mx-auto mb-4">
            {search || statusFilter !== 'all'
              ? 'Try adjusting your search query or status filter.'
              : 'Create your first interview session or instantiate one from a template.'}
          </p>
          {!search && statusFilter === 'all' && (
            <Link href="/interviews/new">
              <Button size="sm" className="text-xs">
                <Plus className="h-3.5 w-3.5 mr-1" />
                Configure First Interview
              </Button>
            </Link>
          )}
        </Card>
      )}

      {/* Interviews Grid */}
      {!isLoading && interviews.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {interviews.map((itw) => (
            <Link key={itw.id} href={`/interviews/${itw.id}`}>
              <Card className="bg-[#0e0f15] border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/40 transition-all p-5 h-full flex flex-col justify-between group">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase border font-semibold ${getTypeColor(itw.interview_type)}`}>
                      {itw.interview_type.replace('_', ' ')}
                    </span>
                    {getStatusBadge(itw.status, itw.is_ready)}
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-white group-hover:text-primary transition-colors line-clamp-1">
                      {itw.title}
                    </h3>
                    {itw.job_title && (
                      <span className="text-[11px] text-indigo-400 flex items-center gap-1 mt-0.5">
                        <Briefcase className="h-3 w-3" />
                        {itw.job_title}
                      </span>
                    )}
                  </div>

                  {/* Candidate banner */}
                  <div className="rounded-lg bg-zinc-950/80 border border-zinc-800/80 p-2.5 flex items-center gap-2.5">
                    <div className="h-7 w-7 rounded-full bg-gradient-to-tr from-indigo-600 to-primary text-white font-bold text-[10px] flex items-center justify-center shrink-0">
                      {itw.candidate_name?.[0] || 'C'}
                    </div>
                    <div className="overflow-hidden">
                      <p className="text-xs font-semibold text-zinc-200 truncate">
                        {itw.candidate_name || 'Unassigned Candidate'}
                      </p>
                      <p className="text-[10px] text-zinc-500 truncate">{itw.candidate_email}</p>
                    </div>
                  </div>

                  {/* Metadata line */}
                  <div className="flex flex-wrap items-center gap-3 text-xs text-zinc-400 pt-1">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3.5 w-3.5 text-zinc-500" />
                      {itw.duration_minutes} mins
                    </span>
                    <span className="flex items-center gap-1 capitalize">
                      <Layers className="h-3.5 w-3.5 text-zinc-500" />
                      {itw.round_count} round{itw.round_count !== 1 ? 's' : ''}
                    </span>
                    <span className="flex items-center gap-1">
                      <Users className="h-3.5 w-3.5 text-zinc-500" />
                      {itw.participant_count} panel
                    </span>
                  </div>
                </div>

                {/* Readiness status footer */}
                <div className="mt-4 pt-3 border-t border-zinc-800/80 flex items-center justify-between text-[11px]">
                  {itw.is_ready ? (
                    <span className="flex items-center gap-1 text-emerald-400 font-medium">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Configuration Complete
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-amber-400 font-medium">
                      <AlertCircle className="h-3.5 w-3.5" />
                      Incomplete Config
                    </span>
                  )}
                  <span className="text-zinc-500">
                    {new Date(itw.created_at).toLocaleDateString()}
                  </span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2 border-t border-zinc-800/80 text-xs text-zinc-400">
          <div>
            Showing {(page - 1) * 12 + 1} to {Math.min(page * 12, total)} of {total} interviews
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="h-8 px-2.5 text-xs border-zinc-800 text-zinc-300"
            >
              <ChevronLeft className="h-3.5 w-3.5 mr-1" />
              Previous
            </Button>
            <span className="text-xs text-zinc-400">
              Page {page} of {totalPages}
            </span>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage(page + 1)}
              className="h-8 px-2.5 text-xs border-zinc-800 text-zinc-300"
            >
              Next
              <ChevronRight className="h-3.5 w-3.5 ml-1" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
