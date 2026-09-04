'use client';

import React, { useEffect, useState, useCallback } from 'react';
import {
  BarChart3,
  Users,
  Terminal,
  Award,
  Scale,
  HelpCircle,
  ShieldCheck,
  Download,
  Sparkles,
  RefreshCw,
  Filter,
  Calendar,
  Briefcase,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';

import { AnalyticsOverviewTab } from '@/components/analytics/analytics-overview-tab';
import { InterviewAnalyticsTab } from '@/components/analytics/interview-analytics-tab';
import { CandidateDecisionTab } from '@/components/analytics/candidate-decision-tab';
import { CompetencyAnalyticsTab } from '@/components/analytics/competency-analytics-tab';
import { InterviewerCalibrationTab } from '@/components/analytics/interviewer-calibration-tab';
import { QuestionAnalyticsTab } from '@/components/analytics/question-analytics-tab';
import { AIEvidenceQualityTab } from '@/components/analytics/ai-evidence-quality-tab';
import { AnalyticsExportModal } from '@/components/analytics/analytics-export-modal';
import { AIAnalyticsExplainer } from '@/components/analytics/ai-analytics-explainer';

export default function AnalyticsPage() {
  const { activeWorkspace } = useAuthStore();

  const [activeTab, setActiveTab] = useState('overview');
  const [windowFilter, setWindowFilter] = useState('30d');
  const [selectedJobId, setSelectedJobId] = useState<string>('all');
  const [jobs, setJobs] = useState<any[]>([]);

  const [overviewData, setOverviewData] = useState<any>(null);
  const [interviewData, setInterviewData] = useState<any>(null);
  const [candidateData, setCandidateData] = useState<any>(null);
  const [competencyData, setCompetencyData] = useState<any>(null);
  const [interviewerData, setInterviewerData] = useState<any>(null);
  const [questionData, setQuestionData] = useState<any>(null);
  const [aiData, setAiData] = useState<any>(null);

  const [loading, setLoading] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [explainerOpen, setExplainerOpen] = useState(false);

  // Fetch jobs for filter dropdown
  useEffect(() => {
    if (!activeWorkspace?.id) return;
    apiClient<any[]>(`/jobs?workspace_id=${activeWorkspace.id}`)
      .then((res) => {
        if (Array.isArray(res)) setJobs(res);
      })
      .catch(() => {});
  }, [activeWorkspace?.id]);

  // Fetch data for active tab
  const fetchAnalytics = useCallback(async () => {
    if (!activeWorkspace?.id) return;

    setLoading(true);
    const wsId = activeWorkspace.id;
    const jobParam = selectedJobId !== 'all' ? `&job_id=${selectedJobId}` : '';

    try {
      if (activeTab === 'overview') {
        const res = await apiClient<any>(
          `/analytics/overview?workspace_id=${wsId}&window=${windowFilter}${jobParam}`
        );
        setOverviewData(res);
      } else if (activeTab === 'interviews') {
        const res = await apiClient<any>(
          `/analytics/interviews?workspace_id=${wsId}&window=${windowFilter}${jobParam}`
        );
        setInterviewData(res);
      } else if (activeTab === 'candidates') {
        const res = await apiClient<any>(
          `/analytics/candidates?workspace_id=${wsId}&window=${windowFilter}${jobParam}`
        );
        setCandidateData(res);
      } else if (activeTab === 'competencies') {
        const res = await apiClient<any>(
          `/analytics/competencies?workspace_id=${wsId}&window=${windowFilter}${jobParam}`
        );
        setCompetencyData(res);
      } else if (activeTab === 'interviewers') {
        const res = await apiClient<any>(
          `/analytics/interviewers?workspace_id=${wsId}&window=${windowFilter}${jobParam}`
        );
        setInterviewerData(res);
      } else if (activeTab === 'questions') {
        const res = await apiClient<any>(
          `/analytics/questions?workspace_id=${wsId}&window=${windowFilter}${jobParam}`
        );
        setQuestionData(res);
      } else if (activeTab === 'ai') {
        const res = await apiClient<any>(
          `/analytics/ai?workspace_id=${wsId}&window=${windowFilter}${jobParam}`
        );
        setAiData(res);
      }
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace?.id, activeTab, windowFilter, selectedJobId]);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  const getCurrentTabMetrics = () => {
    if (activeTab === 'overview') return overviewData || {};
    if (activeTab === 'interviews') return interviewData || {};
    if (activeTab === 'candidates') return candidateData || {};
    if (activeTab === 'competencies') return competencyData || {};
    if (activeTab === 'interviewers') return interviewerData || {};
    if (activeTab === 'questions') return questionData || {};
    if (activeTab === 'ai') return aiData || {};
    return {};
  };

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
              Interview Intelligence & Analytics Center
            </h1>
            <Badge className="bg-indigo-500/10 text-indigo-400 border-indigo-500/20 text-xs">
              Phase 16
            </Badge>
          </div>
          <p className="mt-1 text-xs sm:text-sm text-zinc-400">
            Deterministic decision matrix, competency distributions, interviewer calibration & AI evidence quality
          </p>
        </div>

        {/* Global Action Buttons */}
        <div className="flex items-center gap-2.5 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setExplainerOpen(true)}
            className="border-indigo-500/30 bg-indigo-500/10 text-indigo-300 hover:bg-indigo-500/20 text-xs h-9 gap-1.5 shadow-lg shadow-indigo-500/10"
          >
            <Sparkles className="h-4 w-4 text-indigo-400" />
            AI Interpretation
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={() => setExportOpen(true)}
            className="border-zinc-700 bg-zinc-900/60 text-zinc-200 hover:text-white text-xs h-9 gap-1.5"
          >
            <Download className="h-4 w-4 text-emerald-400" />
            Export Data
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchAnalytics}
            disabled={loading}
            className="border-zinc-800 bg-zinc-900/60 text-zinc-400 hover:text-white text-xs h-9 px-3"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin text-indigo-400' : ''}`} />
          </Button>
        </div>
      </div>

      {/* Filter Controls Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-950/60 p-3 backdrop-blur-md">
        <div className="flex items-center gap-3 flex-wrap text-xs">
          {/* Window Filter */}
          <div className="flex items-center gap-1.5 text-zinc-400">
            <Calendar className="h-3.5 w-3.5 text-indigo-400" />
            <span className="font-medium text-zinc-300">Window:</span>
            <select
              value={windowFilter}
              onChange={(e) => setWindowFilter(e.target.value)}
              className="rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-1 text-white text-xs focus:border-indigo-500 focus:outline-none"
            >
              <option value="7d">Last 7 Days</option>
              <option value="14d">Last 14 Days</option>
              <option value="30d">Last 30 Days</option>
              <option value="60d">Last 60 Days</option>
              <option value="90d">Last 90 Days</option>
              <option value="180d">Last 180 Days</option>
              <option value="365d">Last 365 Days</option>
              <option value="this_quarter">Current Quarter</option>
              <option value="previous_quarter">Previous Quarter</option>
            </select>
          </div>

          {/* Job Filter */}
          <div className="flex items-center gap-1.5 text-zinc-400">
            <Briefcase className="h-3.5 w-3.5 text-purple-400" />
            <span className="font-medium text-zinc-300">Job Role:</span>
            <select
              value={selectedJobId}
              onChange={(e) => setSelectedJobId(e.target.value)}
              className="rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-1 text-white text-xs focus:border-indigo-500 focus:outline-none max-w-[200px] truncate"
            >
              <option value="all">All Jobs & Roles</option>
              {jobs.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.title}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Workspace Scope Indicator */}
        <div className="text-[11px] text-zinc-500 flex items-center gap-1.5 font-mono">
          <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
          <span>Tenant Scoped: {activeWorkspace?.name || 'Default Workspace'}</span>
        </div>
      </div>

      {/* Main Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="flex flex-wrap h-auto gap-1 bg-zinc-900/60 border border-zinc-800 p-1 rounded-xl">
          <TabsTrigger value="overview" className="text-xs data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-1.5 py-2">
            <BarChart3 className="h-3.5 w-3.5" />
            Overview KPIs
          </TabsTrigger>
          <TabsTrigger value="interviews" className="text-xs data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-1.5 py-2">
            <Terminal className="h-3.5 w-3.5" />
            Interviews
          </TabsTrigger>
          <TabsTrigger value="candidates" className="text-xs data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-1.5 py-2">
            <Users className="h-3.5 w-3.5" />
            Decision Matrix & Funnel
          </TabsTrigger>
          <TabsTrigger value="competencies" className="text-xs data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-1.5 py-2">
            <Award className="h-3.5 w-3.5" />
            Competencies
          </TabsTrigger>
          <TabsTrigger value="interviewers" className="text-xs data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-1.5 py-2">
            <Scale className="h-3.5 w-3.5" />
            Interviewer Calibration
          </TabsTrigger>
          <TabsTrigger value="questions" className="text-xs data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-1.5 py-2">
            <HelpCircle className="h-3.5 w-3.5" />
            Questions
          </TabsTrigger>
          <TabsTrigger value="ai" className="text-xs data-[state=active]:bg-indigo-600 data-[state=active]:text-white gap-1.5 py-2">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            AI & Evidence Quality
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-0">
          <AnalyticsOverviewTab data={overviewData} loading={loading} />
        </TabsContent>

        <TabsContent value="interviews" className="mt-0">
          <InterviewAnalyticsTab data={interviewData} loading={loading} />
        </TabsContent>

        <TabsContent value="candidates" className="mt-0">
          <CandidateDecisionTab
            workspaceId={activeWorkspace?.id || ''}
            data={candidateData}
            loading={loading}
          />
        </TabsContent>

        <TabsContent value="competencies" className="mt-0">
          <CompetencyAnalyticsTab data={competencyData} loading={loading} />
        </TabsContent>

        <TabsContent value="interviewers" className="mt-0">
          <InterviewerCalibrationTab data={interviewerData} loading={loading} />
        </TabsContent>

        <TabsContent value="questions" className="mt-0">
          <QuestionAnalyticsTab data={questionData} loading={loading} />
        </TabsContent>

        <TabsContent value="ai" className="mt-0">
          <AIEvidenceQualityTab data={aiData} loading={loading} />
        </TabsContent>
      </Tabs>

      {/* Export Modal */}
      {exportOpen && (
        <AnalyticsExportModal
          workspaceId={activeWorkspace?.id || ''}
          isOpen={exportOpen}
          onClose={() => setExportOpen(false)}
          defaultWindow={windowFilter}
        />
      )}

      {/* AI Explanation Drawer */}
      {explainerOpen && (
        <AIAnalyticsExplainer
          workspaceId={activeWorkspace?.id || ''}
          contextLabel={`analytics_${activeTab}`}
          metrics={getCurrentTabMetrics()}
          isOpen={explainerOpen}
          onClose={() => setExplainerOpen(false)}
        />
      )}
    </div>
  );
}
