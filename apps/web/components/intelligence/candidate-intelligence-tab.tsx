'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  FileText,
  Upload,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  Shield,
  Layers,
  Sparkles,
  ExternalLink,
  ChevronRight,
  Clock,
  Briefcase,
  GraduationCap,
  Award,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

interface CandidateIntelligenceTabProps {
  candidateId: string;
  workspaceId: string;
}

export function CandidateIntelligenceTab({ candidateId, workspaceId }: CandidateIntelligenceTabProps) {
  const [versions, setVersions] = useState<any[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [intelligence, setIntelligence] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadVersions = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiClient<any[]>(`/intelligence/candidates/${candidateId}/resumes`);
      setVersions(data);
      if (data && data.length > 0) {
        const active = data.find((v) => v.is_active) || data[0];
        setSelectedVersionId(active.id);
      }
    } catch (err) {
      console.error('Failed to load resume versions:', err);
    } finally {
      setIsLoading(false);
    }
  }, [candidateId]);

  const loadIntelligence = useCallback(async (versionId: string) => {
    try {
      setIsLoading(true);
      const data = await apiClient<any>(`/intelligence/resumes/${versionId}/intelligence`);
      setIntelligence(data);
    } catch (err) {
      console.error('Failed to load resume intelligence:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadVersions();
  }, [loadVersions]);

  useEffect(() => {
    if (selectedVersionId) {
      loadIntelligence(selectedVersionId);
    }
  }, [selectedVersionId, loadIntelligence]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      const newVersion = await apiClient<any>(`/intelligence/candidates/${candidateId}/resumes`, {
        method: 'POST',
        body: formData,
      });
      await loadVersions();
      setSelectedVersionId(newVersion.id);
    } catch (err) {
      console.error('Failed to upload resume version:', err);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  return (
    <div className="space-y-6">
      {/* Resume Version Switcher & Upload Header */}
      <Card className="bg-slate-900/60 border-slate-800">
        <CardHeader className="pb-3 flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
              <FileText className="w-4 h-4 text-violet-400" />
              Resume Versions & Provenance
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Track historical resume uploads, extracted claims, and page-level evidence citations.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              className="hidden"
              accept=".pdf,.docx,.doc"
            />
            <Button
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="bg-violet-600 hover:bg-violet-500 text-white text-xs h-8 flex items-center gap-1.5"
            >
              <Upload className="w-3.5 h-3.5" />
              {isUploading ? 'Extracting...' : 'Upload New Version'}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {versions.length === 0 ? (
            <div className="p-6 text-center text-slate-400 text-xs border border-dashed border-slate-800 rounded-lg">
              No resume versions uploaded yet. Upload a PDF or DOCX resume to extract claims and profile intelligence.
            </div>
          ) : (
            <div className="flex items-center gap-2 overflow-x-auto pb-2">
              {versions.map((v) => (
                <button
                  key={v.id}
                  onClick={() => setSelectedVersionId(v.id)}
                  className={`px-3 py-2 rounded-lg border text-left text-xs transition-all flex items-center gap-2 ${
                    selectedVersionId === v.id
                      ? 'bg-violet-950/40 border-violet-500/50 text-white'
                      : 'bg-slate-950/50 border-slate-800 text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5 text-violet-400" />
                  <div>
                    <div className="font-semibold flex items-center gap-1.5">
                      v{v.version_number}: {v.file_name}
                      {v.is_active && (
                        <Badge className="bg-emerald-950 text-emerald-400 border border-emerald-800/40 text-[9px] px-1 py-0">
                          Active
                        </Badge>
                      )}
                    </div>
                    <div className="text-[10px] text-slate-500">
                      {new Date(v.created_at).toLocaleDateString()} · {(v.file_size / 1024).toFixed(0)} KB
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Structured Profile & Grounded Claims */}
      {intelligence && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left 2 Cols: Profile & Skills */}
          <div className="lg:col-span-2 space-y-6">
            {/* Candidate Summary */}
            <Card className="bg-slate-900/60 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-violet-400" />
                  Structured Extraction Summary
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/40 p-3 rounded border border-slate-800/50">
                  {intelligence.profile?.summary || 'No extracted summary available.'}
                </p>

                {/* Skills */}
                <div>
                  <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Extracted Skills & Competencies
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {intelligence.profile?.skills?.map((s: any, idx: number) => (
                      <div
                        key={idx}
                        className="px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-xs text-slate-200 flex items-center gap-1.5"
                      >
                        <span className="font-medium">{s.name || s.skill}</span>
                        {s.proficiency && (
                          <span className="text-[10px] text-violet-400">({s.proficiency})</span>
                        )}
                        {s.confidence && (
                          <span className="text-[9px] text-slate-500 font-mono">{(s.confidence * 100).toFixed(0)}%</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Projects */}
                {intelligence.profile?.projects && intelligence.profile.projects.length > 0 && (
                  <div>
                    <h4 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                      Key Projects & Architectural Experience
                    </h4>
                    <div className="space-y-2">
                      {intelligence.profile.projects.map((p: any, idx: number) => (
                        <div key={idx} className="p-3 bg-slate-950/50 rounded border border-slate-800/60 space-y-1.5">
                          <div className="text-xs font-semibold text-slate-200">{p.title}</div>
                          <p className="text-xs text-slate-400">{p.description}</p>
                          {p.technologies && p.technologies.length > 0 && (
                            <div className="flex flex-wrap gap-1 pt-1">
                              {p.technologies.map((t: string, tIdx: number) => (
                                <Badge key={tIdx} variant="outline" className="border-slate-800 text-slate-300 text-[10px] px-1.5 py-0">
                                  {t}
                                </Badge>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Col: Verified Claims & Suggested Interview Probes */}
          <div className="space-y-4">
            <Card className="bg-slate-900/60 border-slate-800">
              <CardHeader className="pb-3">
                <CardTitle className="text-xs font-semibold text-slate-300 uppercase tracking-wider flex items-center gap-1.5">
                  <Shield className="w-3.5 h-3.5 text-emerald-400" />
                  Extracted Claims & Provenance
                </CardTitle>
                <CardDescription className="text-xs text-slate-400">
                  Direct quotes and probe questions for live interview validation.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {intelligence.claims?.length === 0 ? (
                  <div className="text-slate-500 text-xs italic">No specific claims extracted for this version.</div>
                ) : (
                  intelligence.claims.map((claim: any, idx: number) => (
                    <div key={idx} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <div className="text-xs font-semibold text-slate-200">{claim.claim}</div>
                        <Badge
                          className={`text-[9px] uppercase px-1.5 py-0 ${
                            claim.verification_priority === 'high'
                              ? 'bg-rose-950 text-rose-400 border-rose-800/40'
                              : 'bg-amber-950 text-amber-400 border-amber-800/40'
                          }`}
                        >
                          {claim.verification_priority} Priority
                        </Badge>
                      </div>

                      {/* Evidence citation */}
                      {claim.evidence && (
                        <div className="text-[11px] text-slate-400 bg-slate-900/60 p-2 rounded border border-slate-800/40 flex items-start gap-1.5">
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                          <div>
                            <span className="text-slate-500 font-mono text-[10px]">
                              [Page {claim.evidence.page || 1}]
                            </span>{' '}
                            &ldquo;{claim.evidence.text || claim.claim}&rdquo;
                          </div>
                        </div>
                      )}

                      {/* Suggested probes */}
                      {claim.suggested_probes && claim.suggested_probes.length > 0 && (
                        <div className="space-y-1 pt-1">
                          <div className="text-[10px] font-semibold text-violet-400 uppercase tracking-wider flex items-center gap-1">
                            <HelpCircle className="w-3 h-3" />
                            Suggested Verification Probes
                          </div>
                          <ul className="text-xs text-slate-300 space-y-1 list-disc list-inside">
                            {claim.suggested_probes.map((probe: string, pIdx: number) => (
                              <li key={pIdx} className="text-slate-300 leading-snug">
                                {probe}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
}
