'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  Users,
  Search,
  Plus,
  Filter,
  MapPin,
  Building2,
  Briefcase,
  ExternalLink,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
  FileText,
  Tag,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { apiClient } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface CandidateItem {
  id: string;
  workspace_id: string;
  first_name: string;
  last_name: string;
  email: string;
  phone?: string;
  location?: string;
  headline?: string;
  current_company?: string;
  current_title?: string;
  experience_years?: number;
  status: string;
  source: string;
  tags: { id: string; name: string; color: string }[];
  job_applications: { id: string; job_title?: string; status: string }[];
  document_count: number;
  note_count: number;
  created_at: string;
}

export default function CandidatesPage() {
  const { activeWorkspace } = useAuthStore();

  const [candidates, setCandidates] = useState<CandidateItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Create Candidate Modal state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [firstName, setFirstName] = useState('');
  const [lastName, setLastName] = useState('');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('');
  const [location, setLocation] = useState('');
  const [headline, setHeadline] = useState('');
  const [currentCompany, setCurrentCompany] = useState('');
  const [currentTitle, setCurrentTitle] = useState('');
  const [experienceYears, setExperienceYears] = useState('');
  const [statusVal, setStatusVal] = useState('new');
  const [sourceVal, setSourceVal] = useState('inbound');
  const [tagsInput, setTagsInput] = useState('');
  const [linkedinUrl, setLinkedinUrl] = useState('');
  const [githubUrl, setGithubUrl] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchCandidates = useCallback(async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    setError(null);

    try {
      let url = `/candidates?workspace_id=${activeWorkspace.id}&page=${page}&page_size=15`;
      if (statusFilter !== 'all') {
        url += `&status=${statusFilter}`;
      }
      if (search.trim()) {
        url += `&search=${encodeURIComponent(search.trim())}`;
      }

      const res = await apiClient<any>(url);
      setCandidates(res.items || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 0);
    } catch (err: any) {
      setError(err.message || 'Failed to load candidates');
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, page, statusFilter, search]);

  useEffect(() => {
    fetchCandidates();
  }, [fetchCandidates]);

  const handleCreateCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !firstName.trim() || !lastName.trim() || !email.trim()) return;

    setIsSubmitting(true);
    setCreateError(null);

    const tagNames = tagsInput
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean);

    try {
      await apiClient('/candidates', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: activeWorkspace.id,
          first_name: firstName.trim(),
          last_name: lastName.trim(),
          email: email.trim(),
          phone: phone.trim() || undefined,
          location: location.trim() || undefined,
          headline: headline.trim() || undefined,
          current_company: currentCompany.trim() || undefined,
          current_title: currentTitle.trim() || undefined,
          experience_years: experienceYears ? parseFloat(experienceYears) : undefined,
          status: statusVal,
          source: sourceVal,
          linkedin_url: linkedinUrl.trim() || undefined,
          github_url: githubUrl.trim() || undefined,
          tag_names: tagNames,
        }),
      });

      // Reset form
      setFirstName('');
      setLastName('');
      setEmail('');
      setPhone('');
      setLocation('');
      setHeadline('');
      setCurrentCompany('');
      setCurrentTitle('');
      setExperienceYears('');
      setTagsInput('');
      setLinkedinUrl('');
      setGithubUrl('');
      setShowCreateModal(false);
      await fetchCandidates();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create candidate');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusBadge = (s: string) => {
    switch (s) {
      case 'new':
        return <Badge variant="default" className="text-[10px]">NEW</Badge>;
      case 'screening':
        return <Badge variant="warning" className="text-[10px]">SCREENING</Badge>;
      case 'interviewing':
        return <Badge variant="outline" className="text-[10px] text-cyan-400 border-cyan-400/30">INTERVIEWING</Badge>;
      case 'offer':
        return <Badge variant="success" className="text-[10px]">OFFER</Badge>;
      case 'hired':
        return <Badge variant="success" className="text-[10px] bg-emerald-500/20 text-emerald-300">HIRED</Badge>;
      case 'rejected':
        return <Badge variant="outline" className="text-[10px] text-rose-400">REJECTED</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px]">{s.toUpperCase()}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <Users className="h-6 w-6 text-indigo-400" />
            Candidate Pipeline
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Workspace: <strong className="text-zinc-200">{activeWorkspace?.name || 'Default'}</strong> •{' '}
            {total} candidates total
          </p>
        </div>

        <Button
          onClick={() => setShowCreateModal(true)}
          size="sm"
          className="text-xs font-semibold gap-1.5 shadow-lg shadow-primary/20"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Candidate
        </Button>
      </div>

      {/* Search and Status Filters */}
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
            placeholder="Search candidates by name, company, email, role title, or location..."
            className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-3 text-xs text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none"
          />
        </div>

        {/* Status Pills */}
        <div className="flex items-center gap-1 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {['all', 'new', 'screening', 'interviewing', 'offer', 'hired', 'rejected'].map((st) => (
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
          <p className="text-xs text-zinc-500">Loading candidate directory...</p>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && candidates.length === 0 && (
        <Card className="border-zinc-800 bg-[#0d0e14]/90 p-12 text-center">
          <div className="h-12 w-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500 mx-auto mb-3">
            <Users className="h-6 w-6" />
          </div>
          <h3 className="text-sm font-semibold text-white mb-1">No candidates found</h3>
          <p className="text-xs text-zinc-400 max-w-sm mx-auto mb-4">
            {search || statusFilter !== 'all'
              ? 'Try adjusting your search query or status filter.'
              : 'Add candidates to your workspace to start evaluating resumes, taking notes, and conducting interviews.'}
          </p>
          {!search && statusFilter === 'all' && (
            <Button onClick={() => setShowCreateModal(true)} size="sm" className="text-xs">
              <Plus className="h-3.5 w-3.5 mr-1" />
              Add First Candidate
            </Button>
          )}
        </Card>
      )}

      {/* Candidate Table / List */}
      {!isLoading && candidates.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-zinc-800 bg-[#0d0e14]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-800 bg-zinc-950 text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                <tr>
                  <th className="py-3 px-4">Candidate</th>
                  <th className="py-3 px-4">Current Role & Company</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Tags</th>
                  <th className="py-3 px-4">Applications</th>
                  <th className="py-3 px-4">Added</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-800/60">
                {candidates.map((cand) => (
                  <tr
                    key={cand.id}
                    className="hover:bg-zinc-900/40 transition-colors group cursor-pointer"
                  >
                    {/* Candidate Name & Contact */}
                    <td className="py-3 px-4">
                      <Link href={`/candidates/${cand.id}`} className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-gradient-to-tr from-indigo-500 to-primary text-white font-bold text-xs flex items-center justify-center uppercase shadow-sm shrink-0">
                          {cand.first_name[0]}
                          {cand.last_name[0]}
                        </div>
                        <div>
                          <p className="font-bold text-white group-hover:text-primary transition-colors">
                            {cand.first_name} {cand.last_name}
                          </p>
                          <p className="text-[11px] text-zinc-400">{cand.email}</p>
                        </div>
                      </Link>
                    </td>

                    {/* Current role & company */}
                    <td className="py-3 px-4 text-zinc-300">
                      <p className="font-medium text-white truncate max-w-[180px]">
                        {cand.current_title || 'Software Engineer'}
                      </p>
                      <p className="text-[11px] text-zinc-400 truncate max-w-[180px]">
                        {cand.current_company || cand.location || 'Undisclosed'}
                      </p>
                    </td>

                    {/* Status badge */}
                    <td className="py-3 px-4">{getStatusBadge(cand.status)}</td>

                    {/* Tags */}
                    <td className="py-3 px-4">
                      <div className="flex flex-wrap gap-1 max-w-[200px]">
                        {cand.tags && cand.tags.length > 0 ? (
                          cand.tags.slice(0, 3).map((t) => (
                            <span
                              key={t.id}
                              className="px-1.5 py-0.5 rounded text-[10px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20"
                            >
                              {t.name}
                            </span>
                          ))
                        ) : (
                          <span className="text-[11px] text-zinc-600">—</span>
                        )}
                      </div>
                    </td>

                    {/* Applications count */}
                    <td className="py-3 px-4 text-zinc-300">
                      {cand.job_applications?.length > 0 ? (
                        <span className="inline-flex items-center gap-1 font-semibold text-white">
                          <Briefcase className="h-3 w-3 text-indigo-400" />
                          {cand.job_applications.length} role{cand.job_applications.length > 1 ? 's' : ''}
                        </span>
                      ) : (
                        <span className="text-zinc-500 text-[11px]">Unassigned</span>
                      )}
                    </td>

                    {/* Date added */}
                    <td className="py-3 px-4 text-[11px] text-zinc-500">
                      {new Date(cand.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination Controls */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2 border-t border-zinc-800/80 text-xs text-zinc-400">
          <div>
            Showing {(page - 1) * 15 + 1} to {Math.min(page * 15, total)} of {total} candidates
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

      {/* Create Candidate Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-xl rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Users className="h-5 w-5 text-indigo-400" />
                Add Candidate Profile
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

            <form onSubmit={handleCreateCandidate} className="space-y-4 text-xs font-sans">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">First Name *</label>
                  <input
                    type="text"
                    required
                    value={firstName}
                    onChange={(e) => setFirstName(e.target.value)}
                    placeholder="Jane"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Last Name *</label>
                  <input
                    type="text"
                    required
                    value={lastName}
                    onChange={(e) => setLastName(e.target.value)}
                    placeholder="Doe"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Email Address *</label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="jane.doe@example.com"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Phone Number</label>
                  <input
                    type="tel"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+1 555-0100"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Current Company</label>
                  <input
                    type="text"
                    value={currentCompany}
                    onChange={(e) => setCurrentCompany(e.target.value)}
                    placeholder="e.g. Amazon, Datadog"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Current Title</label>
                  <input
                    type="text"
                    value={currentTitle}
                    onChange={(e) => setCurrentTitle(e.target.value)}
                    placeholder="e.g. Senior Software Engineer"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Experience (Years)</label>
                  <input
                    type="number"
                    step="0.5"
                    value={experienceYears}
                    onChange={(e) => setExperienceYears(e.target.value)}
                    placeholder="6"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Location</label>
                  <input
                    type="text"
                    value={location}
                    onChange={(e) => setLocation(e.target.value)}
                    placeholder="Seattle, WA"
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>

                <div className="space-y-1">
                  <label className="font-medium text-zinc-300">Source</label>
                  <select
                    value={sourceVal}
                    onChange={(e) => setSourceVal(e.target.value)}
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                  >
                    <option value="inbound">Inbound</option>
                    <option value="referral">Referral</option>
                    <option value="linkedin">LinkedIn</option>
                    <option value="agency">Agency</option>
                    <option value="career_page">Career Page</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="font-medium text-zinc-300">Headline / Summary</label>
                <input
                  type="text"
                  value={headline}
                  onChange={(e) => setHeadline(e.target.value)}
                  placeholder="e.g. Distributed systems expert with 6+ years in cloud architectures"
                  className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="font-medium text-zinc-300">Tags (comma-separated)</label>
                <input
                  type="text"
                  value={tagsInput}
                  onChange={(e) => setTagsInput(e.target.value)}
                  placeholder="Backend, Python, High Concurrency, Fast Tracker"
                  className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
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
                  {isSubmitting ? 'Adding...' : 'Add Candidate'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
