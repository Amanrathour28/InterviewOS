'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  Briefcase,
  ArrowLeft,
  MapPin,
  Clock,
  DollarSign,
  Users,
  CheckCircle2,
  AlertCircle,
  Archive,
  Plus,
  Tag,
  Calendar,
  Layers,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { JobIntelligenceTab } from '@/components/intelligence/job-intelligence-tab';

interface JobDetail {
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
  responsibilities: string[];
  requirements: string[];
  salary_min?: number;
  salary_max?: number;
  currency: string;
  created_at: string;
  candidate_count: number;
}

interface ApplicationItem {
  id: string;
  job_id: string;
  candidate_id: string;
  status: string;
  source?: string;
  applied_at: string;
  last_activity_at: string;
  candidate?: {
    id: string;
    first_name: string;
    last_name: string;
    email: string;
    headline?: string;
    current_company?: string;
  };
}

const formatSalary = (min?: number, max?: number, curr = 'USD') => {
  if (!min && !max) return null;
  if (min && max) {
    return `$${Math.round(min / 1000)}k - $${Math.round(max / 1000)}k ${curr}`;
  }
  if (min) return `From $${Math.round(min / 1000)}k ${curr}`;
  return `Up to $${Math.round(max! / 1000)}k ${curr}`;
};

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params?.jobId as string;

  const [job, setJob] = useState<JobDetail | null>(null);
  const [applications, setApplications] = useState<ApplicationItem[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'pipeline' | 'intelligence'>('overview');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Add Candidate to Job Modal
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [availableCandidates, setAvailableCandidates] = useState<any[]>([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState('');
  const [isAssigning, setIsAssigning] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  const fetchJobData = useCallback(async () => {
    if (!jobId) return;
    setIsLoading(true);
    setError(null);

    try {
      const [jobData, appsData] = await Promise.all([
        apiClient<JobDetail>(`/jobs/${jobId}`),
        apiClient<ApplicationItem[]>(`/jobs/${jobId}/candidates`),
      ]);
      setJob(jobData);
      setApplications(appsData || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load job details');
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchJobData();
  }, [fetchJobData]);

  const handleArchiveJob = async () => {
    if (!confirm('Are you sure you want to archive this job requisition?')) return;
    try {
      await apiClient(`/jobs/${jobId}`, { method: 'DELETE' });
      router.push('/jobs');
    } catch (err: any) {
      alert(err.message || 'Failed to archive job');
    }
  };

  const handleUpdatePipelineStatus = async (candidateId: string, newStatus: string) => {
    try {
      await apiClient(`/jobs/${jobId}/candidates/${candidateId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
      await fetchJobData();
    } catch (err: any) {
      alert(err.message || 'Failed to update pipeline stage');
    }
  };

  const handleRemoveFromJob = async (candidateId: string) => {
    if (!confirm('Remove this candidate from the job pipeline?')) return;
    try {
      await apiClient(`/jobs/${jobId}/candidates/${candidateId}`, { method: 'DELETE' });
      await fetchJobData();
    } catch (err: any) {
      alert(err.message || 'Failed to remove candidate');
    }
  };

  const handleOpenAssignModal = async () => {
    if (!job) return;
    setShowAssignModal(true);
    setAssignError(null);
    try {
      const res = await apiClient<any>(`/candidates?workspace_id=${job.workspace_id}&page_size=50`);
      setAvailableCandidates(res.items || []);
      if (res.items?.length > 0) {
        setSelectedCandidateId(res.items[0].id);
      }
    } catch (err: any) {
      setAssignError(err.message || 'Failed to load candidates');
    }
  };

  const handleAssignCandidate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCandidateId) return;

    setIsAssigning(true);
    setAssignError(null);

    try {
      await apiClient(`/jobs/${jobId}/candidates`, {
        method: 'POST',
        body: JSON.stringify({
          candidate_id: selectedCandidateId,
          status: 'new',
          source: 'inbound',
        }),
      });
      setShowAssignModal(false);
      await fetchJobData();
    } catch (err: any) {
      setAssignError(err.message || 'Failed to assign candidate');
    } finally {
      setIsAssigning(false);
    }
  };

  if (isLoading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center text-center">
        <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-xs text-zinc-500">Loading job details...</p>
      </div>
    );
  }

  if (error || !job) {
    return (
      <div className="p-8 text-center space-y-4">
        <div className="h-10 w-10 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
          <AlertCircle className="h-5 w-5" />
        </div>
        <h2 className="text-sm font-semibold text-white">Could not load job</h2>
        <p className="text-xs text-zinc-400">{error || 'Job not found or unauthorized'}</p>
        <Link href="/jobs">
          <Button size="sm" variant="outline" className="text-xs">
            Back to Jobs
          </Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <div>
        <Link
          href="/jobs"
          className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Jobs
        </Link>
      </div>

      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Badge variant="default" className="text-[10px] uppercase">
              {job.department || 'Engineering'}
            </Badge>
            <Badge variant={job.status === 'open' ? 'success' : 'outline'} className="text-[10px]">
              {job.status.toUpperCase()}
            </Badge>
            <Badge variant="outline" className="text-[10px] capitalize">
              Priority: {job.priority}
            </Badge>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            {job.title}
          </h1>
          <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-400">
            {job.location && (
              <span className="flex items-center gap-1">
                <MapPin className="h-3.5 w-3.5 text-zinc-500" />
                {job.location}
              </span>
            )}
            <span className="flex items-center gap-1 capitalize">
              <Clock className="h-3.5 w-3.5 text-zinc-500" />
              {job.employment_type.replace('_', ' ')}
            </span>
            {job.salary_min && job.salary_max && (
              <span className="flex items-center gap-1 text-emerald-400 font-medium">
                <DollarSign className="h-3.5 w-3.5" />
                ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()} {job.currency}
              </span>
            )}
            <span className="flex items-center gap-1 text-zinc-400">
              <Users className="h-3.5 w-3.5 text-indigo-400" />
              {applications.length} applied
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleArchiveJob}
            className="text-xs border-zinc-800 text-rose-400 hover:bg-rose-500/10"
          >
            <Archive className="h-3.5 w-3.5 mr-1" />
            Archive Job
          </Button>
          <Button
            size="sm"
            onClick={handleOpenAssignModal}
            className="text-xs font-semibold"
          >
            <Plus className="h-3.5 w-3.5 mr-1" />
            Add Candidate
          </Button>
        </div>
      </div>

      {/* Tabs Switcher */}
      <div className="flex items-center gap-2 border-b border-zinc-800 text-xs font-medium">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 border-b-2 transition-all ${
            activeTab === 'overview'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          Job Overview & Skills
        </button>
        <button
          onClick={() => setActiveTab('pipeline')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'pipeline'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <span>Candidate Pipeline</span>
          <span className="px-1.5 py-0.2 rounded text-[10px] bg-zinc-800 text-zinc-300">
            {applications.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('intelligence')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'intelligence'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <Sparkles className="h-3.5 w-3.5 text-primary" />
          <span>Job Intelligence & Matching</span>
        </button>
      </div>

      {/* TAB: INTELLIGENCE */}
      {activeTab === 'intelligence' && (
        <JobIntelligenceTab jobId={jobId} />
      )}

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
                Description & Impact
              </h3>
              <p className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">
                {job.description || 'No description provided for this job requisition.'}
              </p>
            </Card>

            {job.required_skills && job.required_skills.length > 0 && (
              <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-3">
                <h3 className="text-sm font-bold text-white uppercase tracking-wider text-zinc-400">
                  Required Competencies & Skills
                </h3>
                <div className="flex flex-wrap gap-2">
                  {job.required_skills.map((skill) => (
                    <Badge key={skill} variant="default" className="text-xs py-1 px-3">
                      {skill}
                    </Badge>
                  ))}
                </div>
              </Card>
            )}
          </div>

          <div className="lg:col-span-4 space-y-4">
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-5 space-y-3 text-xs">
              <h3 className="font-bold text-white uppercase tracking-wider text-[11px] text-zinc-400 border-b border-zinc-800/80 pb-2">
                Requisition Metadata
              </h3>
              <div className="space-y-2 text-zinc-300">
                <div>
                  <span className="text-zinc-500">Employment:</span>{' '}
                  <span className="capitalize">{job.employment_type.replace('_', ' ')}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Experience:</span>{' '}
                  <span>
                    {job.experience_min || 0} - {job.experience_max || '10+'} years
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500">Compensation:</span>{' '}
                  <span className="text-emerald-400 font-medium">
                    {formatSalary(job.salary_min, job.salary_max, job.currency) || 'Competitive'}
                  </span>
                </div>
                <div>
                  <span className="text-zinc-500">Created:</span>{' '}
                  <span>{new Date(job.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 2: PIPELINE */}
      {activeTab === 'pipeline' && (
        <div className="space-y-4">
          {applications.length === 0 ? (
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-12 text-center">
              <Users className="h-10 w-10 text-zinc-500 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-white mb-1">No applicants yet</h3>
              <p className="text-xs text-zinc-400 max-w-sm mx-auto mb-4">
                Candidates assigned to this requisition will appear here with active pipeline tracking.
              </p>
              <Button size="sm" onClick={handleOpenAssignModal} className="text-xs">
                <Plus className="h-3.5 w-3.5 mr-1" />
                Assign First Candidate
              </Button>
            </Card>
          ) : (
            <div className="space-y-2">
              {applications.map((app) => (
                <Card
                  key={app.id}
                  className="bg-[#0e0f15] border-zinc-800/80 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-3">
                    <div className="h-9 w-9 rounded-full bg-primary/20 border border-primary/40 text-primary font-bold text-xs flex items-center justify-center">
                      {app.candidate?.first_name?.[0] || 'C'}
                      {app.candidate?.last_name?.[0] || ''}
                    </div>
                    <div>
                      <Link
                        href={`/candidates/${app.candidate_id}`}
                        className="text-sm font-bold text-white hover:text-primary transition-colors"
                      >
                        {app.candidate?.first_name} {app.candidate?.last_name}
                      </Link>
                      <p className="text-[11px] text-zinc-400">
                        {app.candidate?.headline || app.candidate?.email}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-center">
                    {/* Pipeline Stage Selector */}
                    <div className="flex items-center gap-1.5">
                      <span className="text-[11px] text-zinc-500">Stage:</span>
                      <select
                        value={app.status}
                        onChange={(e) => handleUpdatePipelineStatus(app.candidate_id, e.target.value)}
                        className="h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none capitalize"
                      >
                        <option value="new">New</option>
                        <option value="screening">Screening</option>
                        <option value="shortlisted">Shortlisted</option>
                        <option value="interviewing">Interviewing</option>
                        <option value="offer">Offer</option>
                        <option value="hired">Hired</option>
                        <option value="rejected">Rejected</option>
                        <option value="withdrawn">Withdrawn</option>
                      </select>
                    </div>

                    <button
                      onClick={() => handleRemoveFromJob(app.candidate_id)}
                      className="text-zinc-500 hover:text-rose-400 p-1 transition-colors text-xs"
                      title="Remove from job"
                    >
                      ✕
                    </button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Modal: Assign Candidate */}
      {showAssignModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <h3 className="text-base font-bold text-white">Assign Candidate to Job</h3>
              <button
                onClick={() => setShowAssignModal(false)}
                className="text-zinc-500 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>

            {assignError && (
              <div className="rounded border border-rose-500/30 bg-rose-950/20 p-2 text-xs text-rose-400">
                {assignError}
              </div>
            )}

            <form onSubmit={handleAssignCandidate} className="space-y-4 text-xs font-sans">
              <div className="space-y-1.5">
                <label className="text-zinc-300">Select Candidate</label>
                {availableCandidates.length === 0 ? (
                  <p className="text-xs text-zinc-500 py-2">No candidates available in workspace.</p>
                ) : (
                  <select
                    value={selectedCandidateId}
                    onChange={(e) => setSelectedCandidateId(e.target.value)}
                    className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-3 text-xs text-white focus:border-primary focus:outline-none"
                  >
                    {availableCandidates.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.first_name} {c.last_name} ({c.email})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-zinc-800/80">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowAssignModal(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isAssigning || availableCandidates.length === 0}
                  className="text-xs font-semibold"
                >
                  {isAssigning ? 'Assigning...' : 'Assign to Job'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
