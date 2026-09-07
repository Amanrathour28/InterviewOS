'use client';

import React, { useState } from 'react';
import { Activity, Wifi, Shield, AlertTriangle, CheckCircle2, Video } from 'lucide-react';
import { ConnectionState } from '@/lib/realtime/realtime-client';

interface SessionHealthIndicatorProps {
  connectionState: ConnectionState;
  isPaused?: boolean;
  activeParticipantsCount: number;
  webrtcState?: string;
  remoteVideoReceived?: boolean;
}

export const SessionHealthIndicator: React.FC<SessionHealthIndicatorProps> = ({
  connectionState,
  isPaused = false,
  activeParticipantsCount,
  webrtcState,
  remoteVideoReceived,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const getStatusConfig = () => {
    switch (connectionState) {
      case 'connected':
        return {
          label: isPaused ? 'Paused' : 'Healthy',
          dotClass: isPaused ? 'bg-amber-400' : 'bg-emerald-400',
        };
      case 'connecting':
        return {
          label: 'Connecting...',
          dotClass: 'bg-amber-400 animate-ping',
        };
      case 'reconnecting':
        return {
          label: 'Reconnecting...',
          dotClass: 'bg-amber-400 animate-ping',
        };
      case 'disconnected':
      default:
        return {
          label: 'Realtime Offline',
          dotClass: 'bg-rose-500',
        };
    }
  };

  const status = getStatusConfig();
  const isConnected = connectionState === 'connected';

  return (
    <div className="relative">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700/80 text-xs hover:bg-slate-700 transition-colors"
        title="Session Diagnostics"
      >
        <span className={`w-2 h-2 rounded-full shrink-0 ${status.dotClass}`} />
        <span className="text-[11px] font-mono text-slate-300 hidden sm:inline">
          {status.label}
        </span>
      </button>

      {showDetails && (
        <div className="absolute right-0 mt-2 w-72 p-3.5 bg-slate-950 border border-slate-800 rounded-xl shadow-2xl z-50 text-xs space-y-3">
          <div className="flex items-center justify-between font-bold text-white border-b border-slate-800 pb-2">
            <span>Session Diagnostics</span>
            <Activity className="w-3.5 h-3.5 text-indigo-400" />
          </div>

          <div className="space-y-2 text-slate-300">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Socket.IO Realtime:</span>
              <span
                className={`font-mono capitalize font-medium ${
                  isConnected
                    ? 'text-emerald-400'
                    : connectionState === 'reconnecting' || connectionState === 'connecting'
                    ? 'text-amber-400'
                    : 'text-rose-400'
                }`}
              >
                {connectionState}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-slate-400">Mesh WebRTC:</span>
              <span
                className={`font-mono capitalize font-medium ${
                  webrtcState === 'connected'
                    ? 'text-emerald-400'
                    : webrtcState === 'connecting'
                    ? 'text-amber-400'
                    : 'text-zinc-400'
                }`}
              >
                {webrtcState || (isConnected ? 'Standby' : 'Offline')}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="text-slate-400">Remote Video:</span>
              <span
                className={`font-mono font-medium ${
                  remoteVideoReceived ? 'text-emerald-400' : 'text-zinc-500'
                }`}
              >
                {remoteVideoReceived ? 'Streaming' : 'Not Received'}
              </span>
            </div>

            <div className="flex justify-between items-center border-t border-slate-800 pt-2">
              <span className="text-slate-400">Active Participants:</span>
              <span className="text-white font-mono font-bold">{activeParticipantsCount}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
