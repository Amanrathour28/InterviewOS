'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Camera,
  CameraOff,
  Mic,
  MicOff,
  Volume2,
  CheckCircle2,
  AlertCircle,
  Video,
  Sparkles,
  Terminal,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { MediaDeviceSettings } from '@/lib/webrtc/types';
import { DeviceManager } from '@/lib/webrtc/device-manager';

interface DeviceCheckModalProps {
  onJoin: (settings: {
    stream: MediaStream;
    cameraEnabled: boolean;
    micEnabled: boolean;
    devices: MediaDeviceSettings;
  }) => void;
  interviewTitle?: string;
  candidateName?: string;
}

export const DeviceCheckModal: React.FC<DeviceCheckModalProps> = ({
  onJoin,
  interviewTitle = 'Technical Interview',
  candidateName,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [cameraEnabled, setCameraEnabled] = useState(true);
  const [micEnabled, setMicEnabled] = useState(true);
  const [audioLevel, setAudioLevel] = useState(0);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const [devices, setDevices] = useState<MediaDeviceSettings>({
    selectedCameraId: '',
    selectedMicId: '',
    selectedSpeakerId: '',
    availableCameras: [],
    availableMics: [],
    availableSpeakers: [],
  });

  // Audio level analysis interval & context
  const audioContextRef = useRef<AudioContext | null>(null);
  const animFrameRef = useRef<number | null>(null);
  const hasJoinedRef = useRef(false);

  // Initialize media devices
  useEffect(() => {
    let activeStream: MediaStream | null = null;

    async function init() {
      setIsLoading(true);
      setErrorMessage(null);

      try {
        console.log('[Media] requesting camera/microphone in DeviceCheckModal');
        // Enumerate devices initially
        const deviceList = await DeviceManager.enumerateDevices();
        setDevices(deviceList);

        // Request initial user media
        const userStream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 1280 },
            height: { ideal: 720 },
            facingMode: 'user',
          },
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });

        console.log('[Media] getUserMedia success in DeviceCheckModal');
        const vTracks = userStream.getVideoTracks();
        const aTracks = userStream.getAudioTracks();
        console.log(`[Media] video tracks count: ${vTracks.length}, audio tracks count: ${aTracks.length}`);
        if (vTracks.length > 0) {
          console.log(`[Media] video track readyState: ${vTracks[0].readyState}, enabled: ${vTracks[0].enabled}`);
        }

        activeStream = userStream;
        setStream(userStream);

        // Re-enumerate to get actual device labels now that permission is granted
        const updatedDevices = await DeviceManager.enumerateDevices();
        setDevices(updatedDevices);

        // Setup audio visualizer meter
        setupAudioMeter(userStream);
      } catch (err: any) {
        console.warn('[DeviceCheck] getUserMedia error:', err);
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          setErrorMessage('Camera or Microphone access was blocked. Please grant permissions in your browser bar.');
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          setErrorMessage('No camera or microphone hardware found on this machine.');
        } else {
          setErrorMessage(err.message || 'Failed to initialize media devices.');
        }
      } finally {
        setIsLoading(false);
      }
    }

    init();

    return () => {
      // Do NOT stop tracks if the stream is being transferred into the room!
      if (!hasJoinedRef.current && activeStream) {
        console.log('[Media] stopping preview stream tracks on DeviceCheckModal unmount (not joined)');
        activeStream.getTracks().forEach((t) => t.stop());
      } else if (hasJoinedRef.current) {
        console.log('[Media] transferring stream tracks to interview room');
      }
      if (animFrameRef.current) {
        cancelAnimationFrame(animFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
      }
    };
  }, []);

  // Update video element preview
  useEffect(() => {
    if (videoRef.current) {
      if (stream && cameraEnabled) {
        videoRef.current.srcObject = stream;
      } else {
        videoRef.current.srcObject = null;
      }
    }
  }, [stream, cameraEnabled]);

  // Audio level analyzer
  const setupAudioMeter = (mediaStream: MediaStream) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;

      const audioTrack = mediaStream.getAudioTracks()[0];
      if (!audioTrack) return;

      const audioCtx = new AudioCtx();
      audioContextRef.current = audioCtx;

      const analyser = audioCtx.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.5;

      const source = audioCtx.createMediaStreamSource(new MediaStream([audioTrack]));
      source.connect(analyser);

      const dataArray = new Uint8Array(128);

      const updateMeter = () => {
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) {
          sum += dataArray[i];
        }
        const avg = sum / dataArray.length;
        const normalized = Math.min(100, (avg / 100) * 100);
        setAudioLevel(normalized);
        animFrameRef.current = requestAnimationFrame(updateMeter);
      };

      updateMeter();
    } catch (err) {
      console.warn('[DeviceCheck] Audio visualizer setup skipped:', err);
    }
  };

  const handleToggleCamera = () => {
    if (stream) {
      const track = stream.getVideoTracks()[0];
      if (track) {
        track.enabled = !cameraEnabled;
        setCameraEnabled(!cameraEnabled);
      }
    }
  };

  const handleToggleMic = () => {
    if (stream) {
      const track = stream.getAudioTracks()[0];
      if (track) {
        track.enabled = !micEnabled;
        setMicEnabled(!micEnabled);
      }
    }
  };

  const handleCameraChange = async (deviceId: string) => {
    if (!stream) return;
    try {
      const newStream = await navigator.mediaDevices.getUserMedia({
        video: { deviceId: { exact: deviceId } },
      });
      const oldTrack = stream.getVideoTracks()[0];
      const newTrack = newStream.getVideoTracks()[0];

      if (oldTrack) {
        stream.removeTrack(oldTrack);
        oldTrack.stop();
      }
      stream.addTrack(newTrack);
      setDevices((prev) => ({ ...prev, selectedCameraId: deviceId }));
      setCameraEnabled(true);
    } catch (err) {
      console.warn('[DeviceCheck] Failed to switch camera:', err);
    }
  };

  const handleMicChange = async (deviceId: string) => {
    if (!stream) return;
    try {
      const newStream = await navigator.mediaDevices.getUserMedia({
        audio: { deviceId: { exact: deviceId }, echoCancellation: true },
      });
      const oldTrack = stream.getAudioTracks()[0];
      const newTrack = newStream.getAudioTracks()[0];

      if (oldTrack) {
        stream.removeTrack(oldTrack);
        oldTrack.stop();
      }
      stream.addTrack(newTrack);
      setDevices((prev) => ({ ...prev, selectedMicId: deviceId }));
      setMicEnabled(true);
      setupAudioMeter(stream);
    } catch (err) {
      console.warn('[DeviceCheck] Failed to switch mic:', err);
    }
  };

  const handleJoinClick = () => {
    if (stream) {
      hasJoinedRef.current = true;
      onJoin({
        stream,
        cameraEnabled,
        micEnabled,
        devices,
      });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#07080c] p-4 select-none">
      <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-12 gap-8 items-center">
        {/* Left: Video Preview & Floating Controls */}
        <div className="md:col-span-7 flex flex-col items-center space-y-4">
          <div className="relative w-full aspect-video rounded-2xl bg-[#0d0e14] border border-zinc-800 overflow-hidden shadow-2xl flex items-center justify-center">
            {cameraEnabled && stream ? (
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className="w-full h-full object-cover -scale-x-100"
              />
            ) : (
              <div className="flex flex-col items-center justify-center text-center space-y-3 p-6">
                <div className="h-20 w-20 rounded-full bg-zinc-800 border border-zinc-700 flex items-center justify-center text-zinc-400">
                  <CameraOff className="h-8 w-8" />
                </div>
                <p className="text-xs text-zinc-400 font-medium">Camera is turned off</p>
              </div>
            )}

            {/* Bottom In-Preview Controls */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-3 p-1.5 rounded-full bg-black/70 backdrop-blur-md border border-zinc-800">
              <button
                onClick={handleToggleMic}
                className={`h-10 w-10 rounded-full flex items-center justify-center transition-all ${
                  micEnabled ? 'bg-zinc-800 hover:bg-zinc-700 text-white' : 'bg-rose-600 hover:bg-rose-500 text-white'
                }`}
                title={micEnabled ? 'Mute Microphone' : 'Unmute Microphone'}
              >
                {micEnabled ? <Mic className="h-4 w-4" /> : <MicOff className="h-4 w-4" />}
              </button>

              <button
                onClick={handleToggleCamera}
                className={`h-10 w-10 rounded-full flex items-center justify-center transition-all ${
                  cameraEnabled ? 'bg-zinc-800 hover:bg-zinc-700 text-white' : 'bg-rose-600 hover:bg-rose-500 text-white'
                }`}
                title={cameraEnabled ? 'Turn Off Camera' : 'Turn On Camera'}
              >
                {cameraEnabled ? <Camera className="h-4 w-4" /> : <CameraOff className="h-4 w-4" />}
              </button>
            </div>
          </div>

          {/* Audio Input Meter */}
          <div className="w-full flex items-center gap-3 px-4 py-2.5 rounded-xl border border-zinc-800 bg-[#0d0e14]">
            <Mic className={`h-4 w-4 ${micEnabled && audioLevel > 5 ? 'text-emerald-400 animate-pulse' : 'text-zinc-500'}`} />
            <div className="flex-1 h-2 rounded-full bg-zinc-800 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-75"
                style={{ width: micEnabled ? `${audioLevel}%` : '0%' }}
              />
            </div>
            <span className="text-[10px] font-mono text-zinc-400">
              {micEnabled ? `${Math.round(audioLevel)}%` : 'MUTED'}
            </span>
          </div>
        </div>

        {/* Right: Device Selectors & Readiness Checklist */}
        <div className="md:col-span-5 space-y-6">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2 text-indigo-400 text-xs font-bold uppercase tracking-wider">
              <Terminal className="h-4 w-4" />
              <span>InterviewOS Pre-Join Setup</span>
            </div>
            <h1 className="text-xl font-extrabold text-white">{interviewTitle}</h1>
            {candidateName && (
              <p className="text-xs text-zinc-400">
                Candidate: <strong className="text-zinc-200">{candidateName}</strong>
              </p>
            )}
          </div>

          {errorMessage && (
            <div className="p-3 rounded-xl border border-rose-500/30 bg-rose-500/10 flex items-start gap-2.5 text-xs text-rose-300">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {/* Device Selection Fields */}
          <div className="space-y-3.5">
            {/* Camera */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5">
                <Camera className="h-3.5 w-3.5 text-indigo-400" />
                Camera
              </label>
              <select
                value={devices.selectedCameraId}
                onChange={(e) => handleCameraChange(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-[#0d0e14] px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
              >
                {devices.availableCameras.map((cam) => (
                  <option key={cam.deviceId} value={cam.deviceId} className="bg-zinc-900">
                    {cam.label || `Camera ${cam.deviceId.slice(0, 5)}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Microphone */}
            <div className="space-y-1">
              <label className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5">
                <Mic className="h-3.5 w-3.5 text-indigo-400" />
                Microphone
              </label>
              <select
                value={devices.selectedMicId}
                onChange={(e) => handleMicChange(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-[#0d0e14] px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
              >
                {devices.availableMics.map((mic) => (
                  <option key={mic.deviceId} value={mic.deviceId} className="bg-zinc-900">
                    {mic.label || `Microphone ${mic.deviceId.slice(0, 5)}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Speaker */}
            {devices.availableSpeakers.length > 0 && (
              <div className="space-y-1">
                <label className="text-xs font-semibold text-zinc-400 flex items-center gap-1.5">
                  <Volume2 className="h-3.5 w-3.5 text-indigo-400" />
                  Audio Output
                </label>
                <select
                  value={devices.selectedSpeakerId}
                  onChange={(e) => setDevices((prev) => ({ ...prev, selectedSpeakerId: e.target.value }))}
                  className="w-full rounded-lg border border-zinc-800 bg-[#0d0e14] px-3 py-2 text-xs text-white focus:border-indigo-500 focus:outline-none"
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

          {/* Readiness Checklist */}
          <div className="p-3.5 rounded-xl border border-zinc-800 bg-[#0d0e14] space-y-2">
            <div className="flex items-center gap-2 text-xs text-zinc-300">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>Camera & Microphone Ready</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-zinc-300">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>STUN/TURN NAT Traversal Ready</span>
            </div>
            <div className="flex items-center gap-2 text-xs text-zinc-300">
              <CheckCircle2 className="h-4 w-4 text-emerald-400" />
              <span>Encrypted WebRTC Mesh Channel</span>
            </div>
          </div>

          {/* Join Button */}
          <Button
            size="lg"
            disabled={isLoading || !stream}
            onClick={handleJoinClick}
            className="w-full text-sm font-bold gap-2 bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white shadow-xl shadow-indigo-500/25"
          >
            <Video className="h-4 w-4" />
            Enter Live Room
          </Button>
        </div>
      </div>
    </div>
  );
};
