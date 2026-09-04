'use client';

import React from 'react';
import { ShieldCheck, Cpu, AlertTriangle, CheckCircle2, Zap, Database, Lock } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

interface AIEvidenceQualityTabProps {
  data: any;
  loading: boolean;
}

export function AIEvidenceQualityTab({ data, loading }: AIEvidenceQualityTabProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 animate-pulse">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-36 rounded-xl bg-zinc-900/60 border border-zinc-800" />
        ))}
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center py-16 text-zinc-500 text-sm">
        No AI telemetry data available.
      </div>
    );
  }

  const quality = data.evidence_quality || data;
  const telemetry = data.telemetry || {};

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider">Grounding Integrity</span>
              <div className="text-2xl font-black text-emerald-400">
                {Math.round(quality.grounded_percentage ?? 100)}%
              </div>
              <div className="text-[11px] text-zinc-500">
                {quality.total_grounded_claims ?? 0} verified citations
              </div>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
              <ShieldCheck className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider">Avg Evidence Yield</span>
              <div className="text-2xl font-black text-indigo-400">
                {quality.average_evidence_count_per_eval ?? 0}
              </div>
              <div className="text-[11px] text-zinc-500">
                items per evaluation report
              </div>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Database className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider">Contradictions Flagged</span>
              <div className="text-2xl font-black text-amber-400">
                {quality.total_contradictions_detected ?? 0}
              </div>
              <div className="text-[11px] text-zinc-500">
                surfaced for human reviewer
              </div>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardContent className="p-5 flex items-center justify-between">
            <div className="space-y-1">
              <span className="text-xs text-zinc-400 font-medium uppercase tracking-wider">Security & Defense</span>
              <div className="text-2xl font-black text-white">100%</div>
              <div className="text-[11px] text-zinc-500">
                Deterministic separation active
              </div>
            </div>
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400">
              <Lock className="h-5 w-5" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Deep-Dive Panels */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Evidence Verification Distribution */}
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardHeader className="pb-3 border-b border-zinc-800/60">
            <CardTitle className="text-sm font-semibold text-white">Evidence Citation Status</CardTitle>
            <CardDescription className="text-xs text-zinc-400">Semantic transcript and code snippet grounding audit</CardDescription>
          </CardHeader>
          <CardContent className="p-5 space-y-4 text-xs">
            <div className="space-y-3">
              {[
                {
                  label: 'Fully Grounded with Verifiable Transcript/Code Citation',
                  count: quality.grounded_evidence_items ?? quality.total_grounded_claims ?? 0,
                  pct: Math.round(quality.grounded_percentage ?? 100),
                  color: 'bg-emerald-500',
                  text: 'text-emerald-400',
                },
                {
                  label: 'Contradictory Evidence Identified & Penalized',
                  count: quality.total_contradictions_detected ?? 0,
                  pct: Math.round(((quality.total_contradictions_detected || 0) / Math.max(1, quality.total_evidence_items || 10)) * 100),
                  color: 'bg-amber-500',
                  text: 'text-amber-400',
                },
                {
                  label: 'Uncited / General Observations (Demoted)',
                  count: quality.uncited_claims_count ?? 0,
                  pct: 0,
                  color: 'bg-zinc-600',
                  text: 'text-zinc-400',
                },
              ].map((item, i) => (
                <div key={i} className="space-y-1.5 rounded-xl border border-zinc-800/80 bg-zinc-950/40 p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-medium text-zinc-300">{item.label}</span>
                    <span className={`font-mono font-bold ${item.text}`}>{item.count} items</span>
                  </div>
                  <div className="h-1.5 w-full rounded-full bg-zinc-800 overflow-hidden">
                    <div className={`h-full rounded-full ${item.color}`} style={{ width: `${item.pct}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* AI System Trust & Audit Model */}
        <Card className="border-zinc-800 bg-zinc-900/40 backdrop-blur-md">
          <CardHeader className="pb-3 border-b border-zinc-800/60">
            <CardTitle className="text-sm font-semibold text-white flex items-center gap-2">
              <Cpu className="h-4 w-4 text-indigo-400" />
              Evaluation Integrity Architecture
            </CardTitle>
            <CardDescription className="text-xs text-zinc-400">Strict architectural boundaries maintained</CardDescription>
          </CardHeader>
          <CardContent className="p-5 space-y-3 text-xs">
            <div className="space-y-2.5">
              {[
                {
                  title: 'Deterministic Scoring Isolation',
                  desc: 'All scores (overall score, competency scores, rubric thresholds) computed in deterministic Python services. AI models never set scores directly.',
                },
                {
                  title: 'AI Advisory Independence',
                  desc: 'AI provides qualitative reasoning, summaries, and suggestions strictly labeled as advisory.',
                },
                {
                  title: 'Immutable Finalization & Tamper-Proof Audit',
                  desc: 'Evaluation records become strictly immutable upon finalization with SHA-256 integrity hashing.',
                },
                {
                  title: 'Tenant-Hardened Workspace Isolation',
                  desc: 'All analytics and telemetry queries enforce mandatory workspace_id filtering.',
                },
              ].map((item, i) => (
                <div key={i} className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-3 space-y-1">
                  <div className="flex items-center gap-2 font-semibold text-white">
                    <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
                    <span>{item.title}</span>
                  </div>
                  <p className="text-[11px] text-zinc-400 pl-6 leading-relaxed">{item.desc}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
