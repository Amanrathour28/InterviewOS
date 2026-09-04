'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  CheckCircle2,
  Code2,
  PenTool,
  Clock,
  ArrowRight,
  Home,
  FileText,
  Shield,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function InterviewCompletePage() {
  const params = useParams();
  const router = useRouter();
  const interviewId = params?.interviewId as string;

  const [sessionData, setSessionData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadSummary() {
      try {
        setIsLoading(true);
        const itw = await apiClient<any>(`/interviews/${interviewId}`);
        const sess = await apiClient<any>(`/interviews/${interviewId}/session`, { method: 'POST' }).catch(() => null);
        setSessionData({ interview: itw, session: sess });
      } catch (err) {
        console.error('Failed to load completed interview details:', err);
      } finally {
        setIsLoading(false);
      }
    }
    if (interviewId) {
      loadSummary();
    }
  }, [interviewId]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400 text-xs">
        Loading completion summary...
      </div>
    );
  }

  const isInterviewer = sessionData?.session?.is_interviewer;

  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6 pt-12 text-center">
      {/* Success Icon */}
      <div className="w-16 h-16 bg-emerald-500/20 border border-emerald-500/40 rounded-full flex items-center justify-center mx-auto text-emerald-400">
        <CheckCircle2 className="w-8 h-8" />
      </div>

      <div className="space-y-1.5">
        <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 text-[10px] font-mono uppercase">
          Interview Concluded
        </Badge>
        <h1 className="text-2xl font-bold text-white tracking-tight">
          {sessionData?.interview?.title || 'Technical Assessment'}
        </h1>
        <p className="text-xs text-slate-400 max-w-md mx-auto">
          {isInterviewer
            ? 'The interview session has completed. All technical artifacts, code submissions, and private rubric notes have been securely saved.'
            : 'Thank you for participating. Your coding submissions and architecture diagrams have been recorded and sent to the hiring team.'}
        </p>
      </div>

      {/* Artifacts Preserved Card */}
      <Card className="p-4 bg-slate-900/60 border-slate-800 text-left space-y-3">
        <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
          Session Artifacts Recorded
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs text-slate-300">
          <div className="flex items-center gap-2 p-2 rounded bg-slate-950/60 border border-slate-800">
            <Code2 className="w-4 h-4 text-cyan-400" />
            <span>Monaco Source Files</span>
          </div>
          <div className="flex items-center gap-2 p-2 rounded bg-slate-950/60 border border-slate-800">
            <PenTool className="w-4 h-4 text-indigo-400" />
            <span>System Design Canvas</span>
          </div>
          <div className="flex items-center gap-2 p-2 rounded bg-slate-950/60 border border-slate-800">
            <Clock className="w-4 h-4 text-amber-400" />
            <span>Timeline Event Log</span>
          </div>
          <div className="flex items-center gap-2 p-2 rounded bg-slate-950/60 border border-slate-800">
            <Shield className="w-4 h-4 text-purple-400" />
            <span>Encrypted Session Audit</span>
          </div>
        </div>
      </Card>

      {/* Action Buttons */}
      <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4">
        {isInterviewer ? (
          <>
            <Button
              onClick={() => router.push(`/interviews/${interviewId}`)}
              className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-5 h-9"
            >
              Review Interview Details
            </Button>
            <Button
              variant="outline"
              onClick={() => router.push('/dashboard')}
              className="w-full sm:w-auto border-slate-800 text-slate-300 hover:text-white text-xs px-5 h-9"
            >
              Go to Dashboard
            </Button>
          </>
        ) : (
          <Button
            onClick={() => router.push('/dashboard')}
            className="w-full sm:w-auto bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-6 h-9 flex items-center gap-2"
          >
            <Home className="w-3.5 h-3.5" />
            <span>Return to Home</span>
          </Button>
        )}
      </div>
    </div>
  );
}
