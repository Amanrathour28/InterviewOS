'use client';

import React, { useEffect, useRef } from 'react';
import {
  Mic,
  MicOff,
  CameraOff,
  ScreenShare,
  Wifi,
  WifiOff,
  Sparkles,
  Shield,
  User,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { NetworkQuality } from '@/lib/webrtc/types';

interface VideoTileProps {
  userId: string;
  userName: string;
  role: string;
  stream: MediaStream | null;
  isLocal?: boolean;
  cameraEnabled?: boolean;
  microphoneEnabled?: boolean;
  screenSharing?: boolean;
  activeSpeaker?: boolean;
  networkQuality?: NetworkQuality;
  connectionState?: string;
  mediaError?: string | null;
  className?: string;
}

export const VideoTile: React.FC<VideoTileProps> = ({
  userId,
  userName,
  role,
  stream,
  isLocal = false,
  cameraEnabled = true,
  microphoneEnabled = true,
  screenSharing = false,
  activeSpeaker = false,
  networkQuality = 'good',
  connectionState = 'connected',
  mediaError = null,
  className = '',
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);

  // Robust video stream attachment and diagnostic logging
  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    if (cameraEnabled && stream) {
      const vTracks = stream.getVideoTracks();
      const aTracks = stream.getAudioTracks();
      console.log(`[Media] video tracks count: ${vTracks.length}, audio tracks count: ${aTracks.length}`);
      if (vTracks.length > 0) {
        console.log(`[Media] video track readyState: ${vTracks[0].readyState}, enabled: ${vTracks[0].enabled}`);
      }

      if (video.srcObject !== stream) {
        video.srcObject = stream;
        console.log(`[Media] video element attached for ${userName || userId} (local: ${isLocal})`);
      }

      const handleLoadedMetadata = () => {
        console.log(`[Media] video element dimensions: ${video.videoWidth}x${video.videoHeight}`);
      };
      video.addEventListener('loadedmetadata', handleLoadedMetadata);

      video
        .play()
        .then(() => {
          console.log(`[Media] video play success for ${userName || userId}`);
        })
        .catch((err) => {
          console.warn(`[Media] video play failure for ${userName || userId}:`, err);
        });

      return () => {
        video.removeEventListener('loadedmetadata', handleLoadedMetadata);
      };
    } else {
      if (video.srcObject) {
        video.srcObject = null;
      }
    }
  }, [stream, cameraEnabled, isLocal, userId, userName]);

  const initials = userName
    ? userName
        .split(' ')
        .map((n) => n[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
    : 'U';

  const isInterviewer =
    role === 'interviewer' ||
    role === 'lead_interviewer' ||
    role === 'panelist' ||
    role === 'recruiter' ||
    role === 'admin' ||
    role === 'organizer';

  const hasLiveVideo = Boolean(
    cameraEnabled &&
    stream &&
    stream.getVideoTracks().length > 0 &&
    stream.getVideoTracks().some((t) => t.readyState === 'live')
  );

  return (
    <div
      className={`relative w-full h-full min-h-[160px] sm:min-h-[200px] aspect-video max-h-full rounded-2xl overflow-hidden bg-[#0a0b10] border transition-all duration-300 flex items-center justify-center select-none ${
        activeSpeaker
          ? 'border-emerald-500 ring-2 ring-emerald-500/50 shadow-lg shadow-emerald-500/20'
          : 'border-zinc-800/80 hover:border-zinc-700'
      } ${className}`}
    >
      {/* Video Element */}
      {hasLiveVideo ? (
        <video
          ref={(el) => {
            (videoRef as any).current = el;
            if (el && stream && cameraEnabled && el.srcObject !== stream) {
              el.srcObject = stream;
              el.play().catch(() => {});
            }
          }}
          autoPlay
          playsInline
          muted={isLocal} // Avoid local echo
          className={`w-full h-full object-cover transition-opacity duration-300 ${
            isLocal && !screenSharing ? '-scale-x-100' : ''
          }`}
        />
      ) : (
        /* Avatar / Error Fallback */
        <div className="flex flex-col items-center justify-center p-6 text-center space-y-3">
          <div
            className={`h-20 w-20 rounded-full flex items-center justify-center text-2xl font-bold border ${
              mediaError
                ? 'bg-rose-500/10 border-rose-500/30 text-rose-400'
                : isInterviewer
                ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
                : 'bg-zinc-800 border-zinc-700 text-zinc-200'
            }`}
          >
            {initials}
          </div>
          <div className="space-y-1 max-w-[220px]">
            <p className="text-sm font-bold text-white truncate">{userName}</p>
            {mediaError ? (
              <div className="flex items-center justify-center gap-1.5 text-xs text-rose-400 font-medium">
                <CameraOff className="h-3.5 w-3.5 shrink-0" />
                <span>{mediaError}</span>
              </div>
            ) : !cameraEnabled ? (
              <div className="flex items-center justify-center gap-1.5 text-xs text-zinc-500">
                <CameraOff className="h-3.5 w-3.5 text-zinc-500" />
                <span>Camera Off</span>
              </div>
            ) : (
              <div className="flex items-center justify-center gap-1.5 text-xs text-zinc-400">
                <CameraOff className="h-3.5 w-3.5 text-zinc-500" />
                <span>{isLocal ? 'Camera unavailable' : 'Waiting for video...'}</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Top Floating Badges */}
      <div className="absolute top-3 left-3 right-3 flex items-center justify-between pointer-events-none">
        {/* Role / Name tag */}
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-black/70 backdrop-blur-md border border-zinc-800 text-xs text-zinc-200">
          {isInterviewer ? (
            <Shield className="h-3 w-3 text-indigo-400" />
          ) : (
            <User className="h-3 w-3 text-emerald-400" />
          )}
          <span className="font-semibold truncate max-w-[120px]">{userName}</span>
          {isLocal && <span className="text-[10px] text-zinc-400 font-mono">(You)</span>}
        </div>

        {/* Status indicators */}
        <div className="flex items-center gap-1.5">
          {screenSharing && (
            <Badge variant="default" className="text-[10px] bg-indigo-600 gap-1 py-0.5">
              <ScreenShare className="h-3 w-3" />
              Presenting
            </Badge>
          )}

          {/* Network Quality */}
          <div className="px-1.5 py-1 rounded-md bg-black/70 backdrop-blur-md border border-zinc-800 flex items-center">
            {networkQuality === 'poor' ? (
              <WifiOff className="h-3 w-3 text-rose-400" />
            ) : networkQuality === 'fair' ? (
              <Wifi className="h-3 w-3 text-amber-400" />
            ) : (
              <Wifi className="h-3 w-3 text-emerald-400" />
            )}
          </div>
        </div>
      </div>

      {/* Bottom Floating Control State */}
      <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between pointer-events-none">
        {/* Active speaker status */}
        {activeSpeaker ? (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-[10px] text-emerald-300 font-medium animate-pulse">
            <Sparkles className="h-3 w-3" />
            Speaking
          </div>
        ) : (
          <div />
        )}

        {/* Microphone Mute Status Icon */}
        <div
          className={`h-7 w-7 rounded-full flex items-center justify-center backdrop-blur-md border ${
            microphoneEnabled
              ? 'bg-black/60 border-zinc-800 text-zinc-300'
              : 'bg-rose-500/20 border-rose-500/40 text-rose-400'
          }`}
        >
          {microphoneEnabled ? <Mic className="h-3.5 w-3.5" /> : <MicOff className="h-3.5 w-3.5" />}
        </div>
      </div>
    </div>
  );
};
