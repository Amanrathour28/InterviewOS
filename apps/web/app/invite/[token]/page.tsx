'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'next/navigation';
import {
  Terminal,
  Calendar,
  Clock,
  Globe,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Users,
  Briefcase,
  ShieldCheck,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface PublicInvitation {
  interview_id: string;
  title: string;
  description?: string;
  scheduled_start_at: string;
  scheduled_end_at: string;
  timezone: string;
  duration_minutes: number;
  candidate_name?: string;
  job_title?: string;
  interviewer_names: string[];
  status: string;
  expires_at: string;
}

export default function PublicInvitationPage() {
  const params = useParams();
  const token = params?.token as string;

  const [invitation, setInvitation] = useState<PublicInvitation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [actionStatus, setActionStatus] = useState<'idle' | 'accepted' | 'declined'>('idle');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);

  const fetchInvitation = useCallback(async () => {
    if (!token) return;
    setIsLoading(true);
    setError(null);

    try {
      const data = await apiClient<PublicInvitation>(`/invitations/${token}`);
      setInvitation(data);
      if (data.status === 'accepted') setActionStatus('accepted');
      if (data.status === 'declined') setActionStatus('declined');
    } catch (err: any) {
      setError(err.message || 'Invitation link is invalid or expired.');
    } finally {
      setIsLoading(false);
    }
  }, [token]);

  useEffect(() => {
    fetchInvitation();
  }, [fetchInvitation]);

  const handleAccept = async () => {
    setIsSubmitting(true);
    try {
      await apiClient(`/invitations/${token}/accept`, { method: 'POST' });
      setActionStatus('accepted');
      setActionMessage('Your participation is confirmed. A calendar reminder has been sent.');
    } catch (err: any) {
      alert(err.message || 'Failed to accept invitation');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDecline = async () => {
    const reason = prompt('Optional: Reason for declining');
    if (reason === null) return;

    setIsSubmitting(true);
    try {
      await apiClient(`/invitations/${token}/decline`, {
        method: 'POST',
        body: JSON.stringify({ reason }),
      });
      setActionStatus('declined');
      setActionMessage('You have declined the invitation. The organizer has been notified.');
    } catch (err: any) {
      alert(err.message || 'Failed to decline invitation');
    } finally {
      setIsSubmitting(false);
    }
  };

  const formatLocalTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return new Intl.DateTimeFormat('en-US', {
        weekday: 'short',
        month: 'long',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        timeZoneName: 'short',
      }).format(d);
    } catch {
      return isoString;
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#07080c] text-white flex items-center justify-center p-4">
        <div className="text-center space-y-3">
          <div className="h-8 w-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-xs text-zinc-500 font-mono">Verifying invitation link...</p>
        </div>
      </div>
    );
  }

  if (error || !invitation) {
    return (
      <div className="min-h-screen bg-[#07080c] text-white flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-zinc-800 bg-[#0d0e14] p-8 text-center space-y-4 shadow-2xl">
          <div className="h-12 w-12 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold text-white">Invitation Unavailable</h2>
          <p className="text-xs text-zinc-400 leading-relaxed">
            {error || 'This invitation link is invalid, has expired, or has been revoked.'}
          </p>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#07080c] text-white flex flex-col justify-between p-4 sm:p-8">
      {/* Top Header */}
      <div className="max-w-2xl mx-auto w-full flex items-center justify-between pb-6 border-b border-zinc-800/60">
        <div className="flex items-center gap-2.5">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Terminal className="h-4 w-4" />
          </div>
          <span className="font-bold tracking-tight text-sm text-white">InterviewOS</span>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-zinc-500 font-medium">
          <ShieldCheck className="h-4 w-4 text-emerald-400" />
          Verified Secure Invitation
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-2xl mx-auto w-full my-8 space-y-6">
        <Card className="border-zinc-800 bg-[#0d0e14] p-6 sm:p-8 shadow-2xl space-y-6">
          <div className="space-y-2 border-b border-zinc-800/80 pb-5">
            <div className="flex items-center gap-2">
              <Badge variant="default" className="text-[10px] uppercase">
                Technical Interview
              </Badge>
              {actionStatus === 'accepted' && (
                <Badge variant="success" className="text-[10px]">
                  CONFIRMED
                </Badge>
              )}
              {actionStatus === 'declined' && (
                <Badge variant="outline" className="text-[10px] text-zinc-500">
                  DECLINED
                </Badge>
              )}
            </div>

            <h1 className="text-2xl font-extrabold text-white tracking-tight">
              {invitation.title}
            </h1>

            {invitation.job_title && (
              <p className="text-xs text-indigo-400 flex items-center gap-1.5 font-medium">
                <Briefcase className="h-3.5 w-3.5" />
                Position: {invitation.job_title}
              </p>
            )}
          </div>

          {/* Time & Duration card */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-4 space-y-3 text-xs">
            <div className="flex items-start gap-3">
              <Calendar className="h-4 w-4 text-indigo-400 shrink-0 mt-0.5" />
              <div>
                <span className="text-[10px] uppercase font-bold text-zinc-500">Your Local Time</span>
                <p className="font-bold text-white text-sm">
                  {formatLocalTime(invitation.scheduled_start_at)}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2 border-t border-zinc-800/60">
              <Globe className="h-4 w-4 text-zinc-500 shrink-0" />
              <div className="text-zinc-400">
                <span>Organizer Timezone: </span>
                <strong className="text-zinc-200">{invitation.timezone}</strong>
                <span className="text-zinc-500"> • </span>
                <span>UTC: <strong className="text-zinc-300">{new Date(invitation.scheduled_start_at).toUTCString()}</strong></span>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-2 border-t border-zinc-800/60">
              <Clock className="h-4 w-4 text-zinc-500 shrink-0" />
              <div className="text-zinc-400">
                <span>Expected Duration: </span>
                <strong className="text-white">{invitation.duration_minutes} minutes</strong>
              </div>
            </div>
          </div>

          {/* Interviewer Panel preview */}
          {invitation.interviewer_names.length > 0 && (
            <div className="space-y-2 text-xs">
              <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500">
                Evaluation Panel
              </span>
              <div className="flex flex-wrap gap-2">
                {invitation.interviewer_names.map((name, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-zinc-800 bg-zinc-950 text-xs font-semibold text-zinc-200"
                  >
                    <Users className="h-3.5 w-3.5 text-indigo-400" />
                    <span>{name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Action Message Banner */}
          {actionMessage && (
            <div
              className={`p-4 rounded-xl border text-xs flex items-center gap-2.5 ${
                actionStatus === 'accepted'
                  ? 'border-emerald-500/30 bg-emerald-950/20 text-emerald-300'
                  : 'border-zinc-800 bg-zinc-900/60 text-zinc-400'
              }`}
            >
              {actionStatus === 'accepted' ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0" />
              ) : (
                <XCircle className="h-4 w-4 text-zinc-400 shrink-0" />
              )}
              <span>{actionMessage}</span>
            </div>
          )}

          {/* Action Buttons */}
          {actionStatus === 'idle' && (
            <div className="flex flex-col sm:flex-row items-center gap-3 pt-4 border-t border-zinc-800/80">
              <Button
                size="lg"
                disabled={isSubmitting}
                onClick={handleAccept}
                className="w-full sm:flex-1 text-xs font-bold gap-2 shadow-lg shadow-primary/25"
              >
                <CheckCircle2 className="h-4 w-4" />
                Accept & Confirm Attendance
              </Button>
              <Button
                variant="outline"
                size="lg"
                disabled={isSubmitting}
                onClick={handleDecline}
                className="w-full sm:w-auto text-xs border-zinc-800 text-zinc-400 hover:text-white"
              >
                Decline
              </Button>
            </div>
          )}
        </Card>
      </div>

      {/* Footer */}
      <div className="text-center text-[11px] text-zinc-600 max-w-2xl mx-auto w-full pt-4 border-t border-zinc-900">
        InterviewOS • Where Technical Interviews Become Intelligent
      </div>
    </div>
  );
}
