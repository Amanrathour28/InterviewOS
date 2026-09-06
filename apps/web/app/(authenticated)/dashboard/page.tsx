'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Calendar,
  Users,
  Briefcase,
  Code2,
  Plus,
  ArrowRight,
  ShieldCheck,
  Building2,
  Sparkles,
  Layers,
  Zap,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api';
import { InstantInterviewModal } from '@/components/instant-interview/instant-interview-modal';

export default function DashboardPage() {
  const { user, activeOrg, activeWorkspace, fetchOrganizations } = useAuthStore();
  const [showWorkspaceModal, setShowWorkspaceModal] = useState(false);
  const [showInstantModal, setShowInstantModal] = useState(false);
  const [workspaceName, setWorkspaceName] = useState('');
  const [isCreatingWs, setIsCreatingWs] = useState(false);
  const [wsError, setWsError] = useState<string | null>(null);

  const handleCreateWorkspace = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeOrg || !workspaceName.trim()) return;

    setIsCreatingWs(true);
    setWsError(null);

    try {
      await apiClient('/workspaces', {
        method: 'POST',
        body: JSON.stringify({
          organization_id: activeOrg.id,
          name: workspaceName.trim(),
        }),
      });
      setWorkspaceName('');
      setShowWorkspaceModal(false);
      await fetchOrganizations();
    } catch (err: any) {
      setWsError(err.message || 'Failed to create workspace');
    } finally {
      setIsCreatingWs(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-6">
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Welcome back, {user?.first_name || 'Engineer'}.
          </h1>
          <p className="mt-1 text-xs sm:text-sm text-zinc-400 flex items-center gap-2">
            <span>Your technical interview workspace is ready.</span>
            <span className="text-zinc-600">•</span>
            <span className="text-indigo-400 font-medium">
              {activeOrg ? activeOrg.name : 'Personal Account'}
            </span>
          </p>
        </div>

        {/* Quick Action */}
        <div className="flex items-center gap-3">
          {/* ⚡ Start Instant Interview — primary action */}
          <Button
            id="start-instant-interview-btn"
            size="sm"
            onClick={() => setShowInstantModal(true)}
            className="text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 flex items-center gap-1.5 px-4 py-2 h-9"
          >
            <Zap className="h-3.5 w-3.5" />
            Start Instant Interview
          </Button>

          {activeOrg && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowWorkspaceModal(true)}
              className="text-xs border-zinc-700 text-zinc-300"
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              New Workspace
            </Button>
          )}
          {!activeOrg && (
            <Link href="/onboarding">
              <Button size="sm" className="text-xs">
                <Building2 className="h-3.5 w-3.5 mr-1" />
                Set Up Organization
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Quick Actions Grid */}
      <div>
        <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
          Quick Actions
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Action 1: Configure Interview */}
          <Link href="/interviews/new">
            <Card className="bg-[#0f1015] border-zinc-800/80 p-4 hover:border-indigo-500/50 transition-all cursor-pointer">
              <div className="flex items-center justify-between mb-3">
                <div className="h-9 w-9 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                  <Calendar className="h-4 w-4" />
                </div>
                <Badge variant="default" className="text-[10px] bg-indigo-500/10 text-indigo-400 border-indigo-500/30">
                  Active
                </Badge>
              </div>
              <h3 className="text-sm font-semibold text-white">Configure Interview</h3>
              <p className="mt-1 text-xs text-zinc-400">
                Define candidate rounds, question coverage, and panel assignments.
              </p>
            </Card>
          </Link>

          {/* Action 2: Add Candidate */}
          <Link href="/candidates">
            <Card className="bg-[#0f1015] border-zinc-800/80 p-4 hover:border-cyan-500/50 transition-all cursor-pointer">
              <div className="flex items-center justify-between mb-3">
                <div className="h-9 w-9 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
                  <Users className="h-4 w-4" />
                </div>
                <Badge variant="default" className="text-[10px] bg-cyan-500/10 text-cyan-400 border-cyan-500/30">
                  Active
                </Badge>
              </div>
              <h3 className="text-sm font-semibold text-white">Add Candidate</h3>
              <p className="mt-1 text-xs text-zinc-400">
                Create candidate profile, upload resume, and track pipeline status.
              </p>
            </Card>
          </Link>

          {/* Action 3: Create Job */}
          <Link href="/jobs">
            <Card className="bg-[#0f1015] border-zinc-800/80 p-4 hover:border-emerald-500/50 transition-all cursor-pointer">
              <div className="flex items-center justify-between mb-3">
                <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                  <Briefcase className="h-4 w-4" />
                </div>
                <Badge variant="default" className="text-[10px] bg-emerald-500/10 text-emerald-400 border-emerald-500/30">
                  Active
                </Badge>
              </div>
              <h3 className="text-sm font-semibold text-white">Create Job Requisition</h3>
              <p className="mt-1 text-xs text-zinc-400">
                Define required skills, salary ranges, and technical requisitions.
              </p>
            </Card>
          </Link>

          {/* Action 4: Start Practice */}
          <Card className="bg-[#0f1015] border-zinc-800/80 p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="h-9 w-9 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                <Code2 className="h-4 w-4" />
              </div>
              <Badge variant="outline" className="text-[10px] text-zinc-500">
                Phase 25
              </Badge>
            </div>
            <h3 className="text-sm font-semibold text-white">Coding Practice</h3>
            <p className="mt-1 text-xs text-zinc-400">
              Solve DSA challenges in isolated Docker sandboxes.
            </p>
          </Card>
        </div>
      </div>

      {/* Main Sections: Real Empty States */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left 8 cols: Upcoming Interviews */}
        <div className="lg:col-span-8 space-y-4">
          <Card className="border-zinc-800 bg-[#0d0e14]/90">
            <CardHeader className="pb-3 border-b border-zinc-800/80 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold text-white">
                  Upcoming Interviews
                </CardTitle>
                <CardDescription className="text-xs text-zinc-400">
                  Scheduled live sessions across your active workspaces.
                </CardDescription>
              </div>
              <span className="text-xs font-mono text-zinc-500">0 Active</span>
            </CardHeader>
            <CardContent className="py-12 flex flex-col items-center justify-center text-center">
              <div className="h-12 w-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500 mb-3">
                <Calendar className="h-6 w-6" />
              </div>
              <h4 className="text-sm font-semibold text-white mb-1">No interviews scheduled yet</h4>
              <p className="text-xs text-zinc-400 max-w-sm">
                When you schedule candidates or mock interview loops, they will appear here with live countdowns and room links.
              </p>
            </CardContent>
          </Card>

          {/* Candidates Pipeline */}
          <Card className="border-zinc-800 bg-[#0d0e14]/90">
            <CardHeader className="pb-3 border-b border-zinc-800/80 flex flex-row items-center justify-between">
              <div>
                <CardTitle className="text-base font-bold text-white">
                  Candidates Pipeline
                </CardTitle>
                <CardDescription className="text-xs text-zinc-400">
                  Active applicants and interview progress.
                </CardDescription>
              </div>
              <span className="text-xs font-mono text-zinc-500">0 Candidates</span>
            </CardHeader>
            <CardContent className="py-12 flex flex-col items-center justify-center text-center">
              <div className="h-12 w-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center text-zinc-500 mb-3">
                <Users className="h-6 w-6" />
              </div>
              <h4 className="text-sm font-semibold text-white mb-1">No candidates in pipeline</h4>
              <p className="text-xs text-zinc-400 max-w-sm">
                Candidates uploaded via resume parsing or job applications will be tracked here with automated skill match ratings.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Right 4 cols: Workspace Telemetry & Security */}
        <div className="lg:col-span-4 space-y-4">
          <Card className="border-zinc-800 bg-[#0d0e14]/90">
            <CardHeader className="pb-3 border-b border-zinc-800/80">
              <CardTitle className="text-base font-bold text-white flex items-center gap-2">
                <Building2 className="h-4 w-4 text-indigo-400" />
                Active Workspace
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 pt-4 text-xs font-sans">
              <div>
                <span className="text-zinc-500">Organization:</span>
                <p className="font-semibold text-white text-sm">
                  {activeOrg ? activeOrg.name : 'Personal Workspace'}
                </p>
              </div>
              <div>
                <span className="text-zinc-500">Current Workspace:</span>
                <p className="font-semibold text-indigo-400 text-sm">
                  {activeWorkspace ? activeWorkspace.name : 'Default'}
                </p>
              </div>
              <div>
                <span className="text-zinc-500">Your Role:</span>
                <p className="mt-1">
                  <Badge variant="default" className="text-[10px]">
                    {user?.role?.replace('_', ' ').toUpperCase()}
                  </Badge>
                </p>
              </div>

              <div className="pt-2 border-t border-zinc-800/80 space-y-2 text-[11px] text-zinc-400">
                <div className="flex items-center gap-2 text-emerald-400">
                  <ShieldCheck className="h-3.5 w-3.5" />
                  <span>Tenant Isolation: Active</span>
                </div>
                <div className="flex items-center gap-2 text-indigo-400">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Argon2 Session: Valid</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Modal: Create Workspace */}
      {showWorkspaceModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-white">Create New Workspace</h3>
              <button
                onClick={() => setShowWorkspaceModal(false)}
                className="text-zinc-500 hover:text-white text-sm"
              >
                ✕
              </button>
            </div>
            <p className="text-xs text-zinc-400">
              Add a new technical interview workspace to{' '}
              <strong className="text-white">{activeOrg?.name}</strong>.
            </p>

            {wsError && (
              <div className="rounded-lg border border-rose-500/30 bg-rose-950/30 p-2.5 text-xs text-rose-300">
                {wsError}
              </div>
            )}

            <form onSubmit={handleCreateWorkspace} className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Workspace Name</label>
                <input
                  type="text"
                  required
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  placeholder="e.g. Machine Learning, Mobile Core"
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowWorkspaceModal(false)}
                  className="text-xs"
                >
                  Cancel
                </Button>
                <Button type="submit" disabled={isCreatingWs} className="text-xs font-semibold">
                  {isCreatingWs ? 'Creating...' : 'Create Workspace'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Instant Interview Modal */}
      <InstantInterviewModal
        isOpen={showInstantModal}
        onClose={() => setShowInstantModal(false)}
      />
    </div>
  );
}
