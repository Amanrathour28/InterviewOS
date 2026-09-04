'use client';

import React from 'react';
import { Activity, X, Wifi, Shield, Server } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { NetworkDiagnostics } from '@/lib/webrtc/types';

interface NetworkDiagnosticsModalProps {
  isOpen: boolean;
  onClose: () => void;
  diagnostics: Record<string, NetworkDiagnostics>;
  participants: { userId: string; userName: string; role: string }[];
}

export const NetworkDiagnosticsModal: React.FC<NetworkDiagnosticsModalProps> = ({
  isOpen,
  onClose,
  diagnostics,
  participants,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 select-none">
      <div className="w-full max-w-lg rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-white font-bold text-sm">
            <Activity className="h-4 w-4 text-emerald-400" />
            <span>WebRTC Network Diagnostics & Telemetry</span>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 max-h-[60vh] overflow-y-auto pr-1">
          {Object.keys(diagnostics).length === 0 ? (
            <div className="p-8 text-center border border-zinc-800 rounded-xl bg-zinc-950/50 text-xs text-zinc-400">
              Gathering WebRTC peer connection statistics...
            </div>
          ) : (
            Object.entries(diagnostics).map(([userId, diag]) => {
              const participant = participants.find((p) => p.userId === userId);
              const name = participant?.userName || `Peer (${userId.slice(0, 6)})`;

              return (
                <div key={userId} className="p-4 rounded-xl border border-zinc-800 bg-zinc-950 space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-emerald-400" />
                      <strong className="text-xs text-white">{name}</strong>
                    </div>
                    <Badge variant="outline" className="text-[10px] text-zinc-400 font-mono capitalize">
                      {diag.connectionState}
                    </Badge>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
                    {/* RTT */}
                    <div className="p-2 rounded-lg bg-zinc-900/80 border border-zinc-800/80 space-y-0.5">
                      <span className="text-[10px] text-zinc-500 uppercase font-bold">Round Trip</span>
                      <p className="text-xs font-mono font-bold text-white">{diag.rttMs} ms</p>
                    </div>

                    {/* Packet Loss */}
                    <div className="p-2 rounded-lg bg-zinc-900/80 border border-zinc-800/80 space-y-0.5">
                      <span className="text-[10px] text-zinc-500 uppercase font-bold">Packet Loss</span>
                      <p
                        className={`text-xs font-mono font-bold ${
                          diag.packetLossPercent > 5 ? 'text-rose-400' : 'text-emerald-400'
                        }`}
                      >
                        {diag.packetLossPercent}%
                      </p>
                    </div>

                    {/* Resolution */}
                    <div className="p-2 rounded-lg bg-zinc-900/80 border border-zinc-800/80 space-y-0.5">
                      <span className="text-[10px] text-zinc-500 uppercase font-bold">Resolution</span>
                      <p className="text-xs font-mono font-bold text-white">
                        {diag.frameWidth && diag.frameHeight
                          ? `${diag.frameWidth}x${diag.frameHeight}`
                          : '720p HD'}
                      </p>
                    </div>

                    {/* Frame Rate */}
                    <div className="p-2 rounded-lg bg-zinc-900/80 border border-zinc-800/80 space-y-0.5">
                      <span className="text-[10px] text-zinc-500 uppercase font-bold">Frame Rate</span>
                      <p className="text-xs font-mono font-bold text-white">
                        {diag.framesPerSecond ? `${Math.round(diag.framesPerSecond)} fps` : '30 fps'}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-zinc-400 pt-1 border-t border-zinc-800/60">
                    <span className="flex items-center gap-1">
                      <Server className="h-3 w-3 text-indigo-400" />
                      Candidate Type: <strong className="text-zinc-200 capitalize">{diag.iceCandidateType || 'Direct (srflx)'}</strong>
                    </span>
                    <span className="font-mono text-[10px] text-zinc-500">
                      Bytes: {Math.round(diag.bytesReceived / 1024)} KB recv
                    </span>
                  </div>
                </div>
              );
            })
          )}
        </div>

        <div className="pt-2 flex justify-end">
          <Button size="sm" onClick={onClose} className="text-xs font-semibold bg-zinc-800 hover:bg-zinc-700 text-white">
            Close Diagnostics
          </Button>
        </div>
      </div>
    </div>
  );
};
