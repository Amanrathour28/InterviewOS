'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  Users,
  Code2,
  GraduationCap,
  Building2,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { apiClient } from '@/lib/api';
import { useAuthStore } from '@/lib/auth/auth-store';
import { AuthGuard } from '@/components/auth/auth-guard';

export default function OnboardingPage() {
  return (
    <AuthGuard>
      <OnboardingContent />
    </AuthGuard>
  );
}

function OnboardingContent() {
  const router = useRouter();
  const { user, fetchOrganizations } = useAuthStore();

  const [intent, setIntent] = useState<'hiring' | 'interviewing' | 'preparing' | null>(null);
  const [step, setStep] = useState<1 | 2>(1);

  // Org form state
  const [orgName, setOrgName] = useState('');
  const [workspaceName, setWorkspaceName] = useState('Engineering');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSelectIntent = (selected: 'hiring' | 'interviewing' | 'preparing') => {
    setIntent(selected);
    if (selected === 'hiring') {
      setStep(2);
    } else {
      // Direct to dashboard
      router.push('/dashboard');
    }
  };

  const handleCreateOrg = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!orgName.trim()) return;

    setError(null);
    setIsSubmitting(true);

    try {
      await apiClient('/organizations', {
        method: 'POST',
        body: JSON.stringify({
          name: orgName.trim(),
          initial_workspace_name: workspaceName.trim() || 'Engineering',
        }),
      });

      await fetchOrganizations();
      router.push('/dashboard');
    } catch (err: any) {
      setError(err.message || 'Failed to create organization');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-4 bg-background bg-grid-pattern">
      <div className="w-full max-w-2xl space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <Badge variant="default" className="py-1 px-3">
            <Sparkles className="h-3 w-3 mr-1 text-indigo-400" />
            Personalized Setup
          </Badge>
          <h1 className="text-3xl font-extrabold text-white tracking-tight sm:text-4xl">
            Welcome, {user?.first_name || 'Engineer'}
          </h1>
          <p className="text-sm text-zinc-400 max-w-md mx-auto">
            {step === 1
              ? 'Tell us how you plan to use InterviewOS to customize your workspace.'
              : 'Create your organization and primary technical workspace.'}
          </p>
        </div>

        {/* STEP 1: INTENT SELECTION */}
        {step === 1 && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Option 1: Hiring */}
            <Card
              onClick={() => handleSelectIntent('hiring')}
              className="p-4 cursor-pointer border-zinc-800 bg-[#0d0e14] hover:border-primary/60 hover:bg-zinc-900/50 transition-all group relative"
            >
              <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 mb-3 group-hover:scale-110 transition-transform">
                <Building2 className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-white mb-1">Hiring / Recruiting</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Build an engineering organization, invite candidates, and run multi-stage technical loops.
              </p>
              <div className="mt-4 flex items-center text-xs font-semibold text-primary">
                Set up Team <ArrowRight className="h-3.5 w-3.5 ml-1" />
              </div>
            </Card>

            {/* Option 2: Interviewer */}
            <Card
              onClick={() => handleSelectIntent('interviewing')}
              className="p-4 cursor-pointer border-zinc-800 bg-[#0d0e14] hover:border-cyan-500/60 hover:bg-zinc-900/50 transition-all group relative"
            >
              <div className="h-10 w-10 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 mb-3 group-hover:scale-110 transition-transform">
                <Users className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-white mb-1">Conducting Interviews</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Lead collaborative coding and system design sessions with real-time AI copilot assistance.
              </p>
              <div className="mt-4 flex items-center text-xs font-semibold text-cyan-400">
                Join Workspace <ArrowRight className="h-3.5 w-3.5 ml-1" />
              </div>
            </Card>

            {/* Option 3: Candidate */}
            <Card
              onClick={() => handleSelectIntent('preparing')}
              className="p-4 cursor-pointer border-zinc-800 bg-[#0d0e14] hover:border-emerald-500/60 hover:bg-zinc-900/50 transition-all group relative"
            >
              <div className="h-10 w-10 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-3 group-hover:scale-110 transition-transform">
                <GraduationCap className="h-5 w-5" />
              </div>
              <h3 className="text-base font-bold text-white mb-1">Preparing & Practice</h3>
              <p className="text-xs text-zinc-400 leading-relaxed">
                Practice algorithms, take AI mock interviews, and master distributed system architectures.
              </p>
              <div className="mt-4 flex items-center text-xs font-semibold text-emerald-400">
                Start Practice <ArrowRight className="h-3.5 w-3.5 ml-1" />
              </div>
            </Card>
          </div>
        )}

        {/* STEP 2: CREATE ORGANIZATION */}
        {step === 2 && (
          <Card className="border-zinc-800 bg-[#0d0e14]/90 backdrop-blur-xl p-6 shadow-2xl">
            <CardHeader className="p-0 mb-6">
              <CardTitle className="text-xl font-bold text-white">Create your organization</CardTitle>
              <CardDescription className="text-xs text-zinc-400">
                This provisions your tenant, root workspace, and owner privileges.
              </CardDescription>
            </CardHeader>

            <form onSubmit={handleCreateOrg} className="space-y-4">
              {error && (
                <div className="flex items-start gap-2.5 rounded-lg border border-rose-500/30 bg-rose-950/30 p-3 text-xs text-rose-300">
                  <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Organization Name</label>
                <input
                  type="text"
                  required
                  value={orgName}
                  onChange={(e) => setOrgName(e.target.value)}
                  placeholder="e.g. Acme Technologies, Stripe"
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950/80 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-zinc-300">Initial Workspace</label>
                <input
                  type="text"
                  required
                  value={workspaceName}
                  onChange={(e) => setWorkspaceName(e.target.value)}
                  placeholder="Engineering"
                  className="w-full h-10 rounded-lg border border-zinc-800 bg-zinc-950/80 px-3 py-2 text-sm text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                />
              </div>

              <div className="pt-4 flex items-center justify-between">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setStep(1)}
                  className="text-xs text-zinc-400"
                >
                  Back
                </Button>
                <Button type="submit" disabled={isSubmitting} className="text-xs font-semibold px-6">
                  {isSubmitting ? 'Provisioning...' : 'Create & Launch Dashboard'}
                  {!isSubmitting && <ArrowRight className="h-3.5 w-3.5 ml-1.5" />}
                </Button>
              </div>
            </form>
          </Card>
        )}
      </div>
    </div>
  );
}
