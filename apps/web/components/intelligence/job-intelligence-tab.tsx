'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  Briefcase,
  Layers,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  ChevronRight,
  RefreshCw,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';

interface JobIntelligenceTabProps {
  jobId: string;
}

export function JobIntelligenceTab({ jobId }: JobIntelligenceTabProps) {
  const [intelligence, setIntelligence] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadJobIntelligence = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiClient<any>(`/intelligence/jobs/${jobId}/intelligence`);
      setIntelligence(data);
    } catch (err) {
      console.error('Failed to load job intelligence:', err);
    } finally {
      setIsLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    loadJobIntelligence();
  }, [loadJobIntelligence]);

  if (isLoading) {
    return <div className="p-8 text-center text-xs text-slate-400">Analyzing job requirements & taxonomy...</div>;
  }

  if (!intelligence) {
    return (
      <div className="p-6 text-center text-xs text-slate-400 border border-dashed border-slate-800 rounded-lg">
        No job description intelligence available. Click below to analyze.
        <div className="mt-3">
          <Button size="sm" onClick={loadJobIntelligence} className="bg-violet-600 hover:bg-violet-500 text-xs">
            Analyze Job Description
          </Button>
        </div>
      </div>
    );
  }

  const requiredReqs = intelligence.requirements?.filter((r: any) => r.requirement_type === 'required') || [];
  const preferredReqs = intelligence.requirements?.filter((r: any) => r.requirement_type !== 'required') || [];

  return (
    <div className="space-y-6">
      {/* Top Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="bg-slate-900/60 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Target Seniority</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-lg font-bold text-white capitalize">{intelligence.seniority || 'Mid-Level'}</div>
            <p className="text-[11px] text-slate-400 mt-1">Based on required scope and architectural responsibilities</p>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/60 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Technical Domains</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {intelligence.technical_domains?.map((d: string, idx: number) => (
                <Badge key={idx} variant="outline" className="border-slate-800 text-slate-200 text-xs px-2 py-0.5">
                  {d}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900/60 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Suggested Rounds</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-xs text-slate-300 space-y-1">
              {intelligence.suggested_rounds?.map((r: string, idx: number) => (
                <div key={idx} className="flex items-center gap-1.5">
                  <ChevronRight className="w-3 h-3 text-violet-400 shrink-0" />
                  <span>{r}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Structured Requirements Breakdown */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Required Skills */}
        <Card className="bg-slate-900/60 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-semibold text-rose-400 uppercase tracking-wider flex items-center gap-1.5">
              <AlertCircle className="w-3.5 h-3.5" />
              Mandatory Requirements ({requiredReqs.length})
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Core competencies required for candidate qualification.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {requiredReqs.map((req: any) => (
              <div key={req.id} className="p-3 bg-slate-950/60 rounded border border-slate-800/80 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white">{req.skill}</span>
                  <Badge className="bg-rose-950 text-rose-400 border border-rose-800/40 text-[10px] px-1.5 py-0">
                    Required
                  </Badge>
                </div>
                {req.evidence && (
                  <p className="text-[11px] text-slate-400 italic">&ldquo;{req.evidence}&rdquo;</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Preferred / Inferred Skills */}
        <Card className="bg-slate-900/60 border-slate-800">
          <CardHeader className="pb-3">
            <CardTitle className="text-xs font-semibold text-indigo-400 uppercase tracking-wider flex items-center gap-1.5">
              <Sparkles className="w-3.5 h-3.5" />
              Preferred & Inferred Skills ({preferredReqs.length})
            </CardTitle>
            <CardDescription className="text-xs text-slate-400">
              Bonus qualifications and valuable related technologies.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {preferredReqs.map((req: any) => (
              <div key={req.id} className="p-3 bg-slate-950/60 rounded border border-slate-800/80 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-white">{req.skill}</span>
                  <Badge className="bg-indigo-950 text-indigo-400 border border-indigo-800/40 text-[10px] px-1.5 py-0">
                    {req.requirement_type}
                  </Badge>
                </div>
                {req.evidence && (
                  <p className="text-[11px] text-slate-400 italic">&ldquo;{req.evidence}&rdquo;</p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
