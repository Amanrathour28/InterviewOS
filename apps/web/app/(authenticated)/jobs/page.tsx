'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Briefcase,
  Search,
  Plus,
  Filter,
  MapPin,
  Users,
  DollarSign,
  Clock,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  Building2,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { apiClient } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface JobItem {
  id: string;
  workspace_id: string;
  title: string;
  slug: string;
  description: string;
  department?: string;
  location?: string;
  employment_type: string;
  experience_min?: number;
  experience_max?: number;
  status: string;
  priority: string;
  required_skills: string[];
  preferred_skills: string[];
  salary_min?: number;
  salary_max?: number;
  currency: string;
  is_active: boolean;
  created_at: string;
  candidate_count: number;
}

export default function JobsPage() {
  const { activeWorkspace } = useAuthStore();

  const [jobs, setJobs] = useState<JobItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Job Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [title, setTitle] = useState('');
  const [department, setDepartment] = useState('');
  const [location, setLocation] = useState('Remote');
  const [employmentType, setEmploymentType] = useState('full_time');
  const [statusVal, setStatusVal] = useState('open');
  const [priority, setPriority] = useState('medium');
  const [skillsInput, setSkillsInput] = useState('');
  const [salaryMin, setSalaryMin] = useState('');
  const [salaryMax, setSalaryMax] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchJobs = useCallback(async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    setError(null);

    try {
      let url = `/jobs?workspace_id=${activeWorkspace.id}&page=${page}&page_size=12`;
      if (statusFilter !== 'all') {
        url += `&status=${statusFilter}`;
      }
      if (search.trim()) {
        url += `&search=${encodeURIComponent(search.trim())}`;
      }

      const res = await apiClient<any>(url);
      setJobs(res.items || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 0);
    } catch (err: any) {
      setError(err.message || 'Failed to load jobs');
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, page, statusFilter, search]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !title.trim()) return;

    setIsSubmitting(true);
    setCreateError(null);

    const skills = skillsInput
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      await apiClient('/jobs', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: activeWorkspace.id,
          title: title.trim(),
          department: department.trim() || undefined,
          location: location.trim() || undefined,
          employment_type: employmentType,
          status: statusVal,
          priority: priority,
          required_skills: skills,
          salary_min: salaryMin ? parseInt(salaryMin, 10) : undefined,
          salary_max: salaryMax ? parseInt(salaryMax, 10) : undefined,
          currency: 'USD',
          description: description.trim(),
        }),
      });

      // Reset form
      setTitle('');
      setDepartment('');
      setSkillsInput('');
      setSalaryMin('');
      setSalaryMax('');
      setDescription('');
      setShowCreateModal(false);
      await fetchJobs();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create job requisition');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatSalary = (min?: number, max?: number, curr = 'USD') => {
    if (!min && !max) return null;
    if (min && max) {
      return `$${Math.round(min / 1000)}k - $${Math.round(max / 1000)}k ${curr}`;
    }
    if (min) return `From $${Math.round(min / 1000)}k ${curr}`;
    return `Up to $${Math.round(max! / 1000)}k ${curr}`;
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'open':
        return <Badge variant="success">OPEN</Badge>;
      case 'paused':
        return <Badge variant="warning">PAUSED</Badge>;
      case 'closed':
        return <Badge variant="outline">CLOSED</Badge>;
      case 'archived':
        return <Badge variant="outline" className="text-zinc-500">ARCHIVED</Badge>;
      default:
        return <Badge variant="outline">DRAFT</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Briefcase className="h-6 w-6 text-indigo-400" />
            Jobs & Requisitions
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Workspace: <strong className="text-zinc-200">{activeWorkspace?.name || 'Default'}</strong> •{' '}
            {total} total requisitions
          </p>
        </div>

        <Button onClick={() => setShowCreateModal(true)} size="sm" className="text-xs font-semibold gap-1.5 shadow-lg shadow-primary/20">
          <Plus className="h-3.5 w-3.5" />
          Create Requisition
        </Button>
      </div>

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search by role title, department, skills, or location..."
            className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-3 text-xs text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none"
          />
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-1 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {['all', 'open', 'draft', 'paused', 'closed'].map((st) => (
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
          <p className="text-xs text-zinc-500">Loading requisitions...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && jobs.length === 0 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-12 text-center">
          <div className="h-12 w-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500 mx-auto mb-3">
            <Briefcase className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-white mb-1">No job requisitions found</h3>
          <p className="text-xs text-zinc-400 max-w-sm mx-auto mb-4">
            {search || statusFilter !== 'all'
              ? 'Try adjusting your search query or status filter.'
              : 'Create your first technical job requisition to start sourcing and interviewing candidates.'}
          </p>
          {!search && statusFilter === 'all' && (
            <Button onClick={() => setShowCreateModal(true)} size="sm" className="text-xs">
              <Plus className="h-3.5 w-3.5 mr-1" />
              Create First Job
            </Button>
          )}
        </Card>
      )}

      {/* Jobs Grid */}
      {!isLoading && jobs.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {jobs.map((job) => (
            <Link key={job.id} href={`/jobs/${job.id}`}>
              <Card className="bg-[#0e0f15] border-zinc-800/80 hover:border-zinc-700 hover:bg-zinc-900/40 transition-all p-5 h-full flex flex-col justify-between group">
                <div className="space-y-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="text-[11px] font-mono uppercase text-indigo-400">
                        {job.department || 'General Engineering'}
                      </span>
                      <h3 className="text-base font-bold text-white group-hover:text-primary transition-colors line-clamp-1 mt-0.5">
                        {job.title}
                      </h3>
                    </div>
                    {getStatusBadge(job.status)}
                  </div>

                  <div className="flex flex-wrap items-center gap-y-1.5 gap-x-3 text-xs text-zinc-400">
                    {job.location && (
                      <span className="flex items-center gap-1">
                        <MapPin className="h-3 w-3 text-zinc-500" />
                        {job.location}
                      </span>
                    )}
                    <span className="flex items-center gap-1 capitalize">
                      <Clock className="h-3 w-3 text-zinc-500" />
                      {job.employment_type.replace('_', ' ')}
                    </span>
                    {formatSalary(job.salary_min, job.salary_max, job.currency) && (
                      <span className="flex items-center gap-1 text-emerald-400 font-medium">
                        <DollarSign className="h-3 w-3" />
                        {formatSalary(job.salary_min, job.salary_max, job.currency)}
                      </span>
                    )}
                  </div>

                  {job.required_skills && job.required_skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {job.required_skills.slice(0, 4).map((skill) => (
                        <span
                          key={skill}
                          className="px-2 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-800 text-zinc-300"
                        >
                          {skill}
                        </span>
                      ))}
                      {job.required_skills.length > 4 && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-900 text-zinc-500">
                          +{job.required_skills.length - 4}
                        </span>
                      )}
                    </div>
                  )}
                </div>

                <div className="mt-4 pt-3 border-t border-zinc-800/80 flex items-center justify-between text-xs">
                  <div className="flex items-center gap-1.5 text-zinc-400">
                    <Users className="h-3.5 w-3.5 text-indigo-400" />
                    <span className="font-semibold text-white">{job.candidate_count}</span>{' '}
                    <span>applicants</span>
                  </div>
                  <span className="text-[11px] text-zinc-500">
                    {new Date(job.created_at).toLocaleDateString()}
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
            Showing {(page - 1) * 12 + 1} to {Math.min(page * 12, total)} of {total} jobs
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

      {/* Create Job Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-xl rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Briefcase className="h-5 w-5 text-indigo-400" />
                Create Job Requisition
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-zinc-500 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {createError && (
              <div className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-2.5 text-xs text-rose-400">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateJob} className="space-y-4 text-xs font-sans">
              <div className="space-y-1">
                <label className="font-medium text-zinc-300">Job Title *</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Senior Backend Engineer (Go/Kubernetes)"
                  className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Department</label>
                  <input
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    placeholder="e.g. Platform Infrastructure"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Location</label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="e.g. Remote / San Francisco, CA"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Employment Type</label>
                  <select
                    value={employmentType}
                    onChange={(e) => setEmploymentType(e.target.value)}
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                  >
                    <option value="full_time">Full Time</option>
                    <option value="part_time">Part Time</option>
                    <option value="contract">Contract</option>
                    <option value="internship">Internship</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Status</label>
                  <select
                    value={statusVal}
                    onChange={(e) => setStatusVal(e.target.value)}
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                  >
                    <option value="open">Open</option>
                    <option value="draft">Draft</option>
                    <option value="paused">Paused</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Priority</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                  >
                    <option value="low">Low</option>
                    <option value="medium">Medium</option>
                    <option value="high">High</option>
                    <option value="urgent">Urgent</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-medium text-zinc-300">Required Skills (comma-separated)</label>
                <input
                  type="text"
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                  placeholder="Go, Kubernetes, Distributed Systems, PostgreSQL"
                  className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Salary Min (USD)</label>
                  <input
                    type="number"
                    value={salaryMin}
                    onChange={(e) => setSalaryMin(e.target.value)}
                    placeholder="150000"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Salary Max (USD)</label>
                  <input
                    type="number"
                    value={salaryMax}
                    onChange={(e) => setSalaryMax(e.target.value)}
                    placeholder="200000"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-medium text-zinc-300">Role Description</label>
                <textarea
                  rows={4}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Outline core responsibilities, team impact, and required technical proficiencies..."
                  className="w-full rounded-lg border border-zinc-800 bg-zinc-950 p-2.5 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-800/80">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowCreateModal(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isSubmitting} className="text-xs font-semibold">
                  {isSubmitting ? 'Creating...' : 'Create Requisition'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
