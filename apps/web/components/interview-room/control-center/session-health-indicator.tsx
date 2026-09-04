'use client';

import React, { useState } from 'react';
import { Activity, Wifi, Shield, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { ConnectionState } from '@/lib/realtime/realtime-client';

interface SessionHealthIndicatorProps {
  connectionState: ConnectionState;
  isPaused: boolean;
  activeParticipantsCount: number;
}

export const SessionHealthIndicator: React.FC<SessionHealthIndicatorProps> = ({
  connectionState,
  isPaused,
  activeParticipantsCount,
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const isConnected = connectionState === 'connected';

  return (
    <div className="relative">
      <button
        onClick={() => setShowDetails(!showDetails)}
        className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-slate-800/80 border border-slate-700/80 text-xs hover:bg-slate-700 transition-colors"
        title="Session Health"
      >
        <span
          className={`w-2 h-2 rounded-full ${
            !isConnected
              ? 'bg-rose-500 animate-ping'
              : isPaused
              ? 'bg-amber-400'
              : 'bg-emerald-400'
          }`}
        />
        <span className="text-[11px] font-mono text-slate-300 hidden sm:inline">
          {isConnected ? (isPaused ? 'Paused' : 'Healthy') : 'Reconnecting'}
        </span>
      </button>

      {showDetails && (
        <div className="absolute right-0 mt-2 w-64 p-3 bg-slate-950 border border-slate-800 rounded-xl shadow-2xl z-50 text-xs space-y-2.5">
          <div className="flex items-center justify-between font-bold text-white border-b border-slate-800 pb-1.5">
            <span>Session Diagnostics</span>
            <Activity className="w-3.5 h-3.5 text-indigo-400" />
          </div>

          <div className="space-y-1.5 text-slate-300">
            <div className="flex justify-between items-center">
              <span className="text-slate-400">WebSocket Realtime:</span>
              <span className={isConnected ? 'text-emerald-400 font-mono' : 'text-rose-400 font-mono'}>
                {isConnected ? 'Connected' : 'Disconnected'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Mesh WebRTC:</span>
              <span className="text-emerald-400 font-mono">Operational</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-slate-400">Active Participants:</span>
              <span className="text-white font-mono">{activeParticipantsCount}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
