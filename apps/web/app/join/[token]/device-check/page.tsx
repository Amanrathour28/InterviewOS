'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Terminal,
  Camera,
  Mic,
  Volume2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  ChevronRight,
  ArrowLeft,
} from 'lucide-react';
import { getCandidateSession } from '@/lib/candidate-session';

type DeviceState = 'checking' | 'ok' | 'error' | 'denied';

export default function CandidateDeviceCheckPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [cameraState, setCameraState] = useState<DeviceState>('checking');
  const [micState, setMicState] = useState<DeviceState>('checking');
  const [speakerState, setSpeakerState] = useState<DeviceState>('ok'); // browsers don't test speakers directly
  const [isReady, setIsReady] = useState(false);
  const [sessionMissing, setSessionMissing] = useState(false);

  // Validate candidate session
  useEffect(() => {
    const session = getCandidateSession(token);
    if (!session) {
      setSessionMissing(true);
    }
  }, [token]);

  const startDeviceCheck = useCallback(async () => {
    setCameraState('checking');
    setMicState('checking');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });
      streamRef.current = stream;

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }

      setCameraState('ok');
      setMicState('ok');
      setIsReady(true);
    } catch (err: any) {
      const denied =
        err.name === 'NotAllowedError' ||
        err.name === 'PermissionDeniedError';

      if (denied) {
        setCameraState('denied');
        setMicState('denied');
      } else {
        setCameraState('error');
        setMicState('error');
      }
      setIsReady(false);
    }
  }, []);

  useEffect(() => {
    startDeviceCheck();
    return () => {
      // Cleanup media on unmount
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [startDeviceCheck]);

  const handleJoin = () => {
    // Keep stream alive — it will be picked up by the room page
    router.push(`/join/${token}/waiting`);
  };

  const stateIcon = (s: DeviceState) => {
    switch (s) {
      case 'checking':
        return <Loader2 className="h-4 w-4 text-indigo-400 animate-spin" />;
      case 'ok':
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-rose-400" />;
      case 'denied':
        return <XCircle className="h-4 w-4 text-amber-400" />;
    }
  };

  const stateLabel = (s: DeviceState) => {
    switch (s) {
      case 'checking': return 'Checking…';
      case 'ok': return 'Ready';
      case 'error': return 'Not detected';
      case 'denied': return 'Permission denied';
    }
  };

  const stateColor = (s: DeviceState) => {
    switch (s) {
      case 'checking': return 'text-indigo-400';
      case 'ok': return 'text-emerald-400';
      case 'error': return 'text-rose-400';
      case 'denied': return 'text-amber-400';
    }
  };

  if (sessionMissing) {
    return (
      <div className="min-h-screen bg-[#07080c] text-white flex items-center justify-center p-4">
        <div className="max-w-md w-full rounded-2xl border border-zinc-800 bg-[#0d0e14] p-8 text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
          <h1 className="text-lg font-bold">Session Expired</h1>
          <p className="text-sm text-zinc-400">
            Your session has expired or is invalid. Please rejoin using your interview link.
          </p>
          <button
            onClick={() => router.push(`/join/${token}`)}
            className="text-sm text-indigo-400 hover:text-indigo-300"
          >
            ← Back to interview
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#07080c] text-white flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-800/60">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
            <Terminal className="h-4 w-4" />
          </div>
          <span className="font-bold text-sm">
            Interview<span className="text-indigo-400 font-black">OS</span>
          </span>
        </div>
        <button
          onClick={() => router.push(`/join/${token}/identity`)}
          className="flex items-center gap-1 text-xs text-zinc-500 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back
        </button>
      </header>

      {/* Progress bar */}
      <div className="h-1 bg-zinc-900">
        <div className="h-1 w-2/3 bg-indigo-500 rounded-full transition-all" />
      </div>

      <main className="flex-1 flex items-center justify-center p-6">
        <div className="w-full max-w-lg space-y-6">
          <div className="text-center space-y-1">
            <h1 className="text-xl font-bold text-white">Camera &amp; Microphone Check</h1>
            <p className="text-xs text-zinc-500">
              Make sure your devices are working before joining.
            </p>
          </div>

          <div className="rounded-2xl border border-zinc-800 bg-[#0d0e14] overflow-hidden">
            {/* Camera preview */}
            <div className="relative aspect-video bg-zinc-950 flex items-center justify-center">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover"
              />
              {cameraState !== 'ok' && (
                <div className="absolute inset-0 flex flex-col items-center justify-center gap-2">
                  <Camera className="h-10 w-10 text-zinc-700" />
                  <p className="text-xs text-zinc-500">
                    {cameraState === 'denied'
                      ? 'Camera permission denied — please allow access in browser settings'
                      : cameraState === 'checking'
                      ? 'Starting camera…'
                      : 'Camera not detected'}
                  </p>
                </div>
              )}
            </div>

            {/* Device status */}
            <div className="p-6 space-y-3">
              {[
                { icon: Camera, label: 'Camera', state: cameraState },
                { icon: Mic, label: 'Microphone', state: micState },
                { icon: Volume2, label: 'Speaker', state: speakerState },
              ].map(({ icon: Icon, label, state }) => (
                <div
                  key={label}
                  className="flex items-center justify-between py-2.5 border-b border-zinc-800/60 last:border-0"
                >
                  <div className="flex items-center gap-2.5">
                    <Icon className="h-4 w-4 text-zinc-400" />
                    <span className="text-sm text-zinc-300 font-medium">{label}</span>
                  </div>
                  <div className={`flex items-center gap-1.5 text-xs font-semibold ${stateColor(state)}`}>
                    {stateIcon(state)}
                    {stateLabel(state)}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Retry if denied */}
          {(cameraState === 'denied' || cameraState === 'error') && (
            <div className="rounded-xl border border-amber-500/20 bg-amber-950/10 p-4 text-xs text-amber-300 space-y-2">
              <p className="font-semibold">Camera/microphone access needed</p>
              <p>Allow access in your browser&apos;s address bar, then click Retry.</p>
              <button
                onClick={startDeviceCheck}
                className="mt-1 text-xs text-indigo-400 hover:text-indigo-300 font-semibold"
              >
                Retry →
              </button>
            </div>
          )}

          <button
            id="candidate-join-btn"
            onClick={handleJoin}
            disabled={!isReady}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed px-6 py-3.5 text-sm font-bold text-white transition-all shadow-lg shadow-indigo-500/20 active:scale-95"
          >
            Join Interview
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </main>
    </div>
  );
}
