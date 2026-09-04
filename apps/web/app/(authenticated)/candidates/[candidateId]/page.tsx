'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  Users,
  ArrowLeft,
  Mail,
  Phone,
  MapPin,
  Building2,
  Briefcase,
  FileText,
  MessageSquare,
  History,
  Upload,
  Download,
  Trash2,
  Plus,
  ExternalLink,
  Github,
  Linkedin,
  AlertCircle,
  CheckCircle2,
  Tag,
  Clock,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { CandidateIntelligenceTab } from '@/components/intelligence/candidate-intelligence-tab';
import { CandidateJobMatchCard } from '@/components/intelligence/candidate-job-match-card';

interface CandidateDetail {
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
  education_summary?: string;
  linkedin_url?: string;
  github_url?: string;
  portfolio_url?: string;
  status: string;
  source: string;
  notes_summary?: string;
  created_at: string;
  tags: { id: string; name: string; color: string }[];
  job_applications: {
    id: string;
    job_id: string;
    job_title?: string;
    job_department?: string;
    status: string;
    applied_at: string;
  }[];
  document_count: number;
  note_count: number;
}

interface DocumentItem {
  id: string;
  candidate_id: string;
  file_name: string;
  mime_type: string;
  file_size: number;
  document_type: string;
  created_at: string;
}

interface NoteItem {
  id: string;
  candidate_id: string;
  author_id?: string;
  author_name?: string;
  content: string;
  created_at: string;
}

interface ActivityItem {
  id: string;
  candidate_id: string;
  actor_name?: string;
  event_type: string;
  details: any;
  created_at: string;
}

export default function CandidateDetailPage() {
  const params = useParams();
  const router = useRouter();
  const candidateId = params?.candidateId as string;
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [candidate, setCandidate] = useState<CandidateDetail | null>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [notes, setNotes] = useState<NoteItem[]>([]);
  const [activities, setActivities] = useState<ActivityItem[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'intelligence' | 'matching' | 'documents' | 'jobs' | 'notes' | 'activity'>('overview');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New Note state
  const [noteContent, setNoteContent] = useState('');
  const [isAddingNote, setIsAddingNote] = useState(false);

  // Document upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fetchCandidateData = useCallback(async () => {
    if (!candidateId) return;
    setIsLoading(true);
    setError(null);

    try {
      const [candData, docsData, notesData, actsData] = await Promise.all([
        apiClient<CandidateDetail>(`/candidates/${candidateId}`),
        apiClient<DocumentItem[]>(`/candidates/${candidateId}/documents`),
        apiClient<NoteItem[]>(`/candidates/${candidateId}/notes`),
        apiClient<ActivityItem[]>(`/candidates/${candidateId}/activity`),
      ]);

      setCandidate(candData);
      setDocuments(docsData || []);
      setNotes(notesData || []);
      setActivities(actsData || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load candidate details');
    } finally {
      setIsLoading(false);
    }
  }, [candidateId]);

  useEffect(() => {
    fetchCandidateData();
  }, [fetchCandidateData]);

  const handleStatusChange = async (newStatus: string) => {
    try {
      await apiClient(`/candidates/${candidateId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
      await fetchCandidateData();
    } catch (err: any) {
      alert(err.message || 'Failed to update candidate status');
    }
  };

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!noteContent.trim()) return;

    setIsAddingNote(true);
    try {
      await apiClient(`/candidates/${candidateId}/notes`, {
        method: 'POST',
        body: JSON.stringify({ content: noteContent.trim() }),
      });
      setNoteContent('');
      await fetchCandidateData();
    } catch (err: any) {
      alert(err.message || 'Failed to add note');
    } finally {
      setIsAddingNote(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', 'resume');

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
      const token = localStorage.getItem('interviewos_token');
      const headers: Record<string, string> = {};
      if (token) headers['Authorization'] = `Bearer ${token}`;

      const res = await fetch(`${apiUrl}/candidates/${candidateId}/documents`, {
        method: 'POST',
        headers,
        body: formData,
        credentials: 'include',
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data?.detail || 'Failed to upload document');
      }

      await fetchCandidateData();
    } catch (err: any) {
      setUploadError(err.message || 'Failed to upload document');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
      await apiClient(`/candidates/${candidateId}/documents/${docId}`, { method: 'DELETE' });
      await fetchCandidateData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete document');
    }
  };

  const handleDeleteCandidate = async () => {
    if (!confirm('Are you sure you want to soft delete this candidate profile?')) return;
    try {
      await apiClient(`/candidates/${candidateId}`, { method: 'DELETE' });
      router.push('/candidates');
    } catch (err: any) {
      alert(err.message || 'Failed to delete candidate');
    }
  };

  if (isLoading) {
    return (
      <div className="py-20 flex flex-col items-center justify-center text-center">
        <div className="h-6 w-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-xs text-zinc-500">Loading candidate profile...</p>
      </div>
    );
  }

  if (error || !candidate) {
    return (
      <div className="p-8 text-center space-y-4">
        <div className="h-10 w-10 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
          <AlertCircle className="h-5 w-5" />
        </div>
        <h2 className="text-sm font-semibold text-white">Could not load candidate</h2>
        <p className="text-xs text-zinc-400">{error || 'Candidate not found or unauthorized'}</p>
        <Link href="/candidates">
          <Button size="sm" variant="outline" className="text-xs">
            Back to Pipeline
          </Button>
        </Link>
      </div>
    );
  }

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

  return (
    <div className="space-y-6">
      {/* Back Link */}
      <div>
        <Link
          href="/candidates"
          className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Candidates
        </Link>
      </div>

      {/* Candidate Profile Header */}
      <div className="rounded-xl border border-zinc-800 bg-[#0d0e14]/90 p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex items-start gap-4">
            <div className="h-14 w-14 rounded-2xl bg-gradient-to-tr from-indigo-600 to-primary text-white font-black text-xl flex items-center justify-center uppercase shadow-lg shadow-primary/20 shrink-0">
              {candidate.first_name[0]}
              {candidate.last_name[0]}
            </div>

            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center gap-2.5">
                <h1 className="text-2xl font-extrabold text-white tracking-tight">
                  {candidate.first_name} {candidate.last_name}
                </h1>
                <select
                  value={candidate.status}
                  onChange={(e) => handleStatusChange(e.target.value)}
                  className="h-7 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs font-semibold text-white uppercase tracking-wider focus:border-primary focus:outline-none"
                >
                  <option value="new">NEW</option>
                  <option value="screening">SCREENING</option>
                  <option value="shortlisted">SHORTLISTED</option>
                  <option value="interviewing">INTERVIEWING</option>
                  <option value="offer">OFFER</option>
                  <option value="hired">HIRED</option>
                  <option value="rejected">REJECTED</option>
                  <option value="withdrawn">WITHDRAWN</option>
                </select>
              </div>

              <p className="text-xs text-zinc-300 font-medium">
                {candidate.current_title || 'Software Engineer'}
                {candidate.current_company ? ` at ${candidate.current_company}` : ''}
              </p>

              <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-zinc-400 pt-1">
                <span className="flex items-center gap-1">
                  <Mail className="h-3 w-3 text-zinc-500" />
                  {candidate.email}
                </span>
                {candidate.phone && (
                  <span className="flex items-center gap-1">
                    <Phone className="h-3 w-3 text-zinc-500" />
                    {candidate.phone}
                  </span>
                )}
                {candidate.location && (
                  <span className="flex items-center gap-1">
                    <MapPin className="h-3 w-3 text-zinc-500" />
                    {candidate.location}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Social Links & Danger Zone */}
          <div className="flex flex-wrap items-center gap-2 self-start lg:self-center">
            {candidate.linkedin_url && (
              <a
                href={candidate.linkedin_url}
                target="_blank"
                rel="noreferrer"
                className="p-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-400 hover:text-white transition-colors"
                title="LinkedIn Profile"
              >
                <Linkedin className="h-3.5 w-3.5" />
              </a>
            )}
            {candidate.github_url && (
              <a
                href={candidate.github_url}
                target="_blank"
                rel="noreferrer"
                className="p-2 rounded-lg border border-zinc-800 bg-zinc-950 text-zinc-400 hover:text-white transition-colors"
                title="GitHub Profile"
              >
                <Github className="h-3.5 w-3.5" />
              </a>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleDeleteCandidate}
              className="text-xs border-zinc-800 text-rose-400 hover:bg-rose-500/10"
            >
              <Trash2 className="h-3.5 w-3.5 mr-1" />
              Delete Profile
            </Button>
          </div>
        </div>

        {/* Tags bar */}
        {candidate.tags && candidate.tags.length > 0 && (
          <div className="mt-4 pt-3 border-t border-zinc-800/80 flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] text-zinc-500 mr-1 flex items-center gap-1">
              <Tag className="h-3 w-3" /> Tags:
            </span>
            {candidate.tags.map((t) => (
              <span
                key={t.id}
                className="px-2 py-0.5 rounded text-[10px] bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-medium"
              >
                {t.name}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-zinc-800 text-xs font-medium overflow-x-auto">
        <button
          onClick={() => setActiveTab('overview')}
          className={`pb-3 border-b-2 transition-all ${
            activeTab === 'overview'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          Overview & Experience
        </button>
        <button
          onClick={() => setActiveTab('intelligence')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'intelligence'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <Sparkles className="h-3 w-3 text-violet-400" />
          <span>Resume Intelligence</span>
        </button>
        <button
          onClick={() => setActiveTab('matching')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'matching'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <span>Job Matching</span>
        </button>
        <button
          onClick={() => setActiveTab('documents')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'documents'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <span>Raw Documents</span>
          <span className="px-1.5 py-0.2 rounded text-[10px] bg-zinc-800 text-zinc-300">
            {documents.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('jobs')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'jobs'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <span>Job Applications</span>
          <span className="px-1.5 py-0.2 rounded text-[10px] bg-zinc-800 text-zinc-300">
            {candidate.job_applications?.length || 0}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('notes')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'notes'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <span>Internal Notes</span>
          <span className="px-1.5 py-0.2 rounded text-[10px] bg-zinc-800 text-zinc-300">
            {notes.length}
          </span>
        </button>
        <button
          onClick={() => setActiveTab('activity')}
          className={`pb-3 border-b-2 transition-all flex items-center gap-1.5 ${
            activeTab === 'activity'
              ? 'border-primary text-white font-semibold'
              : 'border-transparent text-zinc-400 hover:text-white'
          }`}
        >
          <span>Timeline</span>
        </button>
      </div>

      {/* TAB: INTELLIGENCE */}
      {activeTab === 'intelligence' && (
        <CandidateIntelligenceTab candidateId={candidateId} workspaceId={candidate.workspace_id} />
      )}

      {/* TAB: MATCHING */}
      {activeTab === 'matching' && (
        candidate.job_applications && candidate.job_applications.length > 0 ? (
          <CandidateJobMatchCard
            jobId={candidate.job_applications[0].job_id}
            candidateId={candidateId}
          />
        ) : (
          <div className="p-8 text-center text-zinc-400 text-xs border border-dashed border-zinc-800 rounded-lg">
            Candidate is not currently associated with an active job application. Link a job in the Job Applications tab to evaluate match fit.
          </div>
        )
      )}

      {/* TAB 1: OVERVIEW */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 space-y-6">
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-3">
              <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                Candidate Summary
              </h3>
              <p className="text-xs text-zinc-300 leading-relaxed">
                {candidate.headline || 'No summary available.'}
              </p>
            </Card>

            {candidate.education_summary && (
              <Card className="border-zinc-800 bg-[#0d0e14]/90 p-6 space-y-3">
                <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                  Education & Credentials
                </h3>
                <p className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">
                  {candidate.education_summary}
                </p>
              </Card>
            )}
          </div>

          <div className="lg:col-span-4 space-y-4">
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-5 space-y-3 text-xs">
              <h3 className="font-bold text-white uppercase tracking-wider text-[11px] text-zinc-400 border-b border-zinc-800/80 pb-2">
                Candidate Details
              </h3>
              <div className="space-y-2 text-zinc-300">
                <div>
                  <span className="text-zinc-500">Experience:</span>{' '}
                  <span>{candidate.experience_years || 0} years</span>
                </div>
                <div>
                  <span className="text-zinc-500">Source:</span>{' '}
                  <span className="capitalize">{candidate.source.replace('_', ' ')}</span>
                </div>
                <div>
                  <span className="text-zinc-500">Added:</span>{' '}
                  <span>{new Date(candidate.created_at).toLocaleDateString()}</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* TAB 2: RESUME & DOCUMENTS */}
      {activeTab === 'documents' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Candidate Resumes & Files</h3>
              <p className="text-xs text-zinc-400">
                Supported formats: PDF, DOCX, DOC (up to 10 MB). Stored securely in MinIO object storage.
              </p>
            </div>

            <div>
              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept=".pdf,.docx,.doc,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                className="hidden"
              />
              <Button
                size="sm"
                disabled={isUploading}
                onClick={() => fileInputRef.current?.click()}
                className="text-xs font-semibold gap-1.5"
              >
                <Upload className="h-3.5 w-3.5" />
                {isUploading ? 'Uploading...' : 'Upload Document'}
              </Button>
            </div>
          </div>

          {uploadError && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-950/20 p-3 text-xs text-rose-400">
              {uploadError}
            </div>
          )}

          {documents.length === 0 ? (
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-12 text-center">
              <FileText className="h-10 w-10 text-zinc-500 mx-auto mb-3" />
              <h4 className="text-sm font-semibold text-white mb-1">No documents uploaded</h4>
              <p className="text-xs text-zinc-400 max-w-sm mx-auto mb-4">
                Upload candidate resume or technical portfolio to review attachments directly.
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                className="text-xs border-zinc-800 text-zinc-300"
              >
                Upload Resume (PDF)
              </Button>
            </Card>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {documents.map((doc) => (
                <Card
                  key={doc.id}
                  className="bg-[#0e0f15] border-zinc-800/80 p-4 flex items-center justify-between gap-3"
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <div className="h-10 w-10 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 shrink-0">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="overflow-hidden">
                      <p className="text-xs font-bold text-white truncate max-w-[200px]">
                        {doc.file_name}
                      </p>
                      <p className="text-[11px] text-zinc-400">
                        {Math.round(doc.file_size / 1024)} KB • {new Date(doc.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1">
                    <a
                      href={`${apiUrl}/candidates/${candidateId}/documents/${doc.id}/download`}
                      download
                      className="p-1.5 rounded-lg border border-zinc-800 hover:bg-zinc-800 text-zinc-300 hover:text-white transition-colors"
                      title="Download document"
                    >
                      <Download className="h-3.5 w-3.5" />
                    </a>
                    <button
                      onClick={() => handleDeleteDocument(doc.id)}
                      className="p-1.5 rounded-lg border border-zinc-800 hover:bg-rose-500/10 text-zinc-500 hover:text-rose-400 transition-colors"
                      title="Delete document"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 3: JOB APPLICATIONS */}
      {activeTab === 'jobs' && (
        <div className="space-y-4">
          {candidate.job_applications?.length === 0 ? (
            <Card className="border-zinc-800 bg-[#0d0e14]/90 p-12 text-center">
              <Briefcase className="h-10 w-10 text-zinc-500 mx-auto mb-3" />
              <h4 className="text-sm font-semibold text-white mb-1">No active job applications</h4>
              <p className="text-xs text-zinc-400 max-w-sm mx-auto mb-4">
                This candidate is not currently assigned to any job requisitions in this workspace.
              </p>
              <Link href="/jobs">
                <Button size="sm" className="text-xs">
                  View Job Board
                </Button>
              </Link>
            </Card>
          ) : (
            <div className="space-y-2">
              {candidate.job_applications.map((app) => (
                <Card
                  key={app.id}
                  className="bg-[#0e0f15] border-zinc-800/80 p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                >
                  <div>
                    <Link
                      href={`/jobs/${app.job_id}`}
                      className="text-sm font-bold text-white hover:text-primary transition-colors flex items-center gap-1.5"
                    >
                      {app.job_title || 'Engineering Role'}
                      <ExternalLink className="h-3 w-3 text-zinc-500" />
                    </Link>
                    <p className="text-xs text-zinc-400">
                      Applied: {new Date(app.applied_at).toLocaleDateString()}
                    </p>
                  </div>

                  <Badge variant="default" className="text-xs capitalize self-start sm:self-center">
                    {app.status}
                  </Badge>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* TAB 4: NOTES */}
      {activeTab === 'notes' && (
        <div className="space-y-6">
          {/* Add note card */}
          <Card className="border-zinc-800 bg-[#0d0e14]/90 p-4">
            <form onSubmit={handleAddNote} className="space-y-3">
              <label className="text-xs font-bold text-white uppercase tracking-wider text-zinc-400">
                Add Internal Recruiter / Interviewer Note
              </label>
              <textarea
                rows={3}
                required
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
                placeholder="Record candidate strengths, compensation expectations, or panel feedback..."
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 p-2.5 text-xs text-white focus:border-primary focus:outline-none"
              />
              <div className="flex justify-end">
                <Button type="submit" size="sm" disabled={isAddingNote} className="text-xs font-semibold">
                  {isAddingNote ? 'Saving note...' : 'Save Note'}
                </Button>
              </div>
            </form>
          </Card>

          {/* Notes list */}
          <div className="space-y-3">
            {notes.length === 0 ? (
              <p className="text-xs text-zinc-500 text-center py-6">No notes added yet.</p>
            ) : (
              notes.map((n) => (
                <Card key={n.id} className="bg-[#0e0f15] border-zinc-800/80 p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs border-b border-zinc-800/60 pb-2">
                    <span className="font-bold text-indigo-400">{n.author_name || 'Team Member'}</span>
                    <span className="text-[11px] text-zinc-500">
                      {new Date(n.created_at).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-zinc-300 whitespace-pre-wrap leading-relaxed">
                    {n.content}
                  </p>
                </Card>
              ))
            )}
          </div>
        </div>
      )}

      {/* TAB 5: ACTIVITY TIMELINE */}
      {activeTab === 'activity' && (
        <div className="space-y-4">
          <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
            Audit Trail & Activity
          </h3>

          <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-zinc-800">
            {activities.length === 0 ? (
              <p className="text-xs text-zinc-500">No activity recorded yet.</p>
            ) : (
              activities.map((act) => (
                <div key={act.id} className="relative space-y-1">
                  <div className="absolute -left-6 top-1 h-3 w-3 rounded-full bg-primary border-2 border-background" />
                  <div className="flex items-center gap-2 text-xs">
                    <span className="font-semibold text-white capitalize">
                      {act.event_type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-zinc-500">•</span>
                    <span className="text-[11px] text-zinc-500">
                      {new Date(act.created_at).toLocaleString()}
                    </span>
                  </div>
                  {act.actor_name && (
                    <p className="text-[11px] text-zinc-400">by {act.actor_name}</p>
                  )}
                  {act.details && Object.keys(act.details).length > 0 && (
                    <pre className="text-[10px] font-mono text-zinc-400 bg-zinc-950 p-2 rounded border border-zinc-800/80 inline-block">
                      {JSON.stringify(act.details, null, 2)}
                    </pre>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
