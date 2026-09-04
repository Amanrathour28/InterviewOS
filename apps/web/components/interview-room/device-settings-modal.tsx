'use client';

import React from 'react';
import { Camera, Mic, Volume2, X, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { MediaDeviceSettings } from '@/lib/webrtc/types';

interface DeviceSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  devices: MediaDeviceSettings;
  onCameraChange: (deviceId: string) => void;
  onMicChange: (deviceId: string) => void;
  onSpeakerChange: (deviceId: string) => void;
}

export const DeviceSettingsModal: React.FC<DeviceSettingsModalProps> = ({
  isOpen,
  onClose,
  devices,
  onCameraChange,
  onMicChange,
  onSpeakerChange,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 select-none">
      <div className="w-full max-w-md rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-white font-bold text-sm">
            <Settings className="h-4 w-4 text-indigo-400" />
            <span>Audio & Video Settings</span>
          </div>
          <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Camera Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5">
              <Camera className="h-3.5 w-3.5 text-indigo-400" />
              Camera Source
            </label>
            <select
              value={devices.selectedCameraId}
              onChange={(e) => onCameraChange(e.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
            >
              {devices.availableCameras.map((cam) => (
                <option key={cam.deviceId} value={cam.deviceId} className="bg-zinc-900">
                  {cam.label || `Camera ${cam.deviceId.slice(0, 5)}`}
                </option>
              ))}
            </select>
          </div>

          {/* Microphone Selection */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5">
              <Mic className="h-3.5 w-3.5 text-indigo-400" />
              Microphone Source
            </label>
            <select
              value={devices.selectedMicId}
              onChange={(e) => onMicChange(e.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
            >
              {devices.availableMics.map((mic) => (
                <option key={mic.deviceId} value={mic.deviceId} className="bg-zinc-900">
                  {mic.label || `Microphone ${mic.deviceId.slice(0, 5)}`}
                </option>
              ))}
            </select>
          </div>

          {/* Speaker Selection */}
          {devices.availableSpeakers.length > 0 && (
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5">
                <Volume2 className="h-3.5 w-3.5 text-indigo-400" />
                Audio Output / Speaker
              </label>
              <select
                value={devices.selectedSpeakerId}
                onChange={(e) => onSpeakerChange(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
              >
                {devices.availableSpeakers.map((spk) => (
                  <option key={spk.deviceId} value={spk.deviceId} className="bg-zinc-900">
                    {spk.label || `Speaker ${spk.deviceId.slice(0, 5)}`}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        <div className="pt-2 flex justify-end">
          <Button size="sm" onClick={onClose} className="text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white">
            Done
          </Button>
        </div>
      </div>
    </div>
  );
};
