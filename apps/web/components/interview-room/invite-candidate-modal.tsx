'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  UserPlus,
  Copy,
  Check,
  Share2,
  X,
  Clock,
  AlertCircle,
  Loader2,
  Link as LinkIcon,
  ExternalLink,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api';

interface InviteCandidateModalProps {
  isOpen: boolean;
  onClose: () => void;
  interviewId: string;
  interviewTitle?: string;
  onCopyToast?: (message: string) => void;
}

interface InviteLinkData {
  interview_id: string;
  token: string;
  join_url: string;
  expires_at: string;
}

export const InviteCandidateModal: React.FC<InviteCandidateModalProps> = ({
  isOpen,
  onClose,
  interviewId,
  interviewTitle,
  onCopyToast,
}) => {
  const [data, setData] = useState<InviteLinkData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [shared, setShared] = useState(false);
  const copyButtonRef = useRef<HTMLButtonElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  // Fetch candidate join link
  const fetchInviteLink = useCallback(async () => {
    if (!interviewId) return;
    setIsLoading(true);
    setError(null);

    try {
      const resp = await apiClient<InviteLinkData>(
        `/interviews/${interviewId}/invite-link`
      );
      setData(resp);
    } catch (err: any) {
      console.error('[InviteModal] Failed to fetch join link:', err);
      setError(
        err?.message ||
          'Failed to retrieve candidate join URL. Please check permissions.'
      );
    } finally {
      setIsLoading(false);
    }
  }, [interviewId]);

  useEffect(() => {
    if (isOpen) {
      fetchInviteLink();
    } else {
      setCopied(false);
      setShared(false);
    }
  }, [isOpen, fetchInviteLink]);

  // Keyboard accessibility: Escape to close
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Focus copy button on load
  useEffect(() => {
    if (isOpen && data && copyButtonRef.current) {
      copyButtonRef.current.focus();
    }
  }, [isOpen, data]);

  // Copy join URL with fallback
  const handleCopy = async () => {
    if (!data?.join_url) return;

    try {
      if (typeof navigator !== 'undefined' && navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(data.join_url);
      } else {
        // Fallback for environments where clipboard API is restricted
        if (inputRef.current) {
          inputRef.current.select();
          inputRef.current.setSelectionRange(0, 99999);
          document.execCommand('copy');
        } else {
          const textarea = document.createElement('textarea');
          textarea.value = data.join_url;
          textarea.style.position = 'fixed';
          textarea.style.opacity = '0';
          document.body.appendChild(textarea);
          textarea.select();
          document.execCommand('copy');
          document.body.removeChild(textarea);
        }
      }

      setCopied(true);
      if (onCopyToast) {
        onCopyToast('Interview link copied');
      }
      setTimeout(() => setCopied(false), 2500);
    } catch (err) {
      console.error('[InviteModal] Clipboard copy failed:', err);
      // Fallback: select input text so user can copy manually
      if (inputRef.current) {
        inputRef.current.select();
      }
    }
  };

  // Browser Web Share API with safe fallback
  const handleShare = async () => {
    if (!data?.join_url) return;

    const shareData = {
      title: interviewTitle
        ? `${interviewTitle} — InterviewOS`
        : 'InterviewOS Interview',
      text: 'Join this interview',
      url: data.join_url,
    };

    if (
      typeof navigator !== 'undefined' &&
      navigator.share &&
      navigator.canShare?.(shareData)
    ) {
      try {
        await navigator.share(shareData);
        setShared(true);
        setTimeout(() => setShared(false), 2500);
        return;
      } catch (err: any) {
        if (err?.name === 'AbortError') {
          // User closed share sheet, do not fallback or error
          return;
        }
      }
    }

    // Fall back to copy link
    await handleCopy();
  };

  // Compute expiration text
  const getExpirationText = (): string | null => {
    if (!data?.expires_at) return null;
    try {
      const expDate = new Date(data.expires_at);
      const now = new Date();
      const diffMs = expDate.getTime() - now.getTime();
      if (diffMs <= 0) return 'Expired';
      const diffHours = Math.round(diffMs / (1000 * 60 * 60));
      if (diffHours < 1) {
        const diffMins = Math.max(1, Math.round(diffMs / (1000 * 60)));
        return `Link expires in ${diffMins} minute${diffMins === 1 ? '' : 's'}`;
      }
      return `Link expires in ${diffHours} hour${diffHours === 1 ? '' : 's'}`;
    } catch {
      return null;
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="invite-dialog-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-150 select-none"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#0d0e14] p-5 sm:p-6 shadow-2xl space-y-5 text-left animate-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-indigo-600/15 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
              <UserPlus className="h-5 w-5" />
            </div>
            <div>
              <h3
                id="invite-dialog-title"
                className="text-base font-bold text-white tracking-tight"
              >
                Invite to this interview
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">
                Share this link with the candidate to join this interview.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close invite dialog"
            className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800/60 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content Body */}
        {isLoading ? (
          <div className="py-8 flex flex-col items-center justify-center gap-2 text-slate-400">
            <Loader2 className="h-6 w-6 animate-spin text-indigo-400" />
            <span className="text-xs">Generating secure join link...</span>
          </div>
        ) : error ? (
          <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/10 space-y-2.5">
            <div className="flex items-center gap-2 text-rose-400 text-xs font-semibold">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>Unable to retrieve join link</span>
            </div>
            <p className="text-[11px] text-rose-300/80">{error}</p>
            <Button
              size="sm"
              variant="outline"
              onClick={fetchInviteLink}
              className="text-xs border-rose-500/40 text-rose-300 hover:bg-rose-500/20"
            >
              Retry
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Join URL Display Box */}
            <div className="space-y-1.5">
              <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider">
                Candidate Join URL
              </label>
              <div className="flex items-center gap-2 p-1.5 rounded-xl border border-slate-800 bg-slate-950/80 focus-within:border-indigo-500/60 transition-colors">
                <div className="pl-2 text-slate-500">
                  <LinkIcon className="h-3.5 w-3.5" />
                </div>
                <input
                  ref={inputRef}
                  type="text"
                  readOnly
                  value={data?.join_url || ''}
                  aria-label="Candidate join link"
                  className="w-full bg-transparent text-xs font-mono text-slate-200 outline-none select-all truncate pr-1"
                  onClick={(e) => (e.target as HTMLInputElement).select()}
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="grid grid-cols-2 gap-2.5 pt-1">
              <Button
                ref={copyButtonRef}
                onClick={handleCopy}
                aria-label="Copy interview link to clipboard"
                className={`h-9 text-xs font-semibold flex items-center justify-center gap-1.5 transition-all ${
                  copied
                    ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                    : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25'
                }`}
              >
                {copied ? (
                  <>
                    <Check className="h-3.5 w-3.5" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5" />
                    <span>Copy link</span>
                  </>
                )}
              </Button>

              <Button
                variant="outline"
                onClick={handleShare}
                aria-label="Share interview link via device share"
                className="h-9 text-xs font-semibold border-slate-700 bg-slate-900/60 text-slate-200 hover:bg-slate-800 hover:text-white flex items-center justify-center gap-1.5"
              >
                {shared ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span>Shared!</span>
                  </>
                ) : (
                  <>
                    <Share2 className="h-3.5 w-3.5 text-slate-400" />
                    <span>Share interview</span>
                  </>
                )}
              </Button>
            </div>

            {/* Expiration and Security Notice */}
            <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-[11px] text-slate-400">
              <div className="flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-slate-500" />
                <span>{getExpirationText() || 'Active interview session'}</span>
              </div>
              <span className="text-[10px] text-slate-500">
                Single secure token
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
