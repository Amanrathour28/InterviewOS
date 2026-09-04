'use client';

import React, { useState, useEffect, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Video,
  VideoOff,
  Mic,
  MicOff,
  Volume2,
  Wifi,
  Shield,
  Clock,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function CandidateWaitingRoomPage() {
  const params = useParams();
  const router = useRouter();
  const interviewId = params?.interviewId as string;

  const [session, setSession] = useState<any>(null);
  const [waitingRoomData, setWaitingRoomData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Device Test State
  const [devices, setDevices] = useState<{
    cameras: MediaDeviceInfo[];
    microphones: MediaDeviceInfo[];
    speakers: MediaDeviceInfo[];
  }>({ cameras: [], microphones: [], speakers: [] });

  const [selectedCamera, setSelectedCamera] = useState<string>('');
  const [selectedMicrophone, setSelectedMicrophone] = useState<string>('');
  const [selectedSpeaker, setSelectedSpeaker] = useState<string>('');

  const [isCameraActive, setIsCameraActive] = useState(true);
  const [isMicrophoneActive, setIsMicrophoneActive] = useState(true);
  const [micVolume, setMicVolume] = useState(0);
  const [hasPermission, setHasPermission] = useState<boolean | null>(null);

  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // 1. Fetch Session & Waiting Room Data
  useEffect(() => {
    async function loadWaitingData() {
      try {
        setIsLoading(true);
        const sess = await apiClient<any>(`/interviews/${interviewId}/session`, { method: 'POST' });
        setSession(sess);

        const wrData = await apiClient<any>(`/sessions/${sess.id}/waiting-room`);
        setWaitingRoomData(wrData);
      } catch (err) {
        console.error('Failed to load waiting room data:', err);
      } finally {
        setIsLoading(false);
      }
    }
    if (interviewId) {
      loadWaitingData();
    }
  }, [interviewId]);

  // 2. Enumerate & Acquire Devices
  useEffect(() => {
    async function initMedia() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });
        streamRef.current = stream;
        setHasPermission(true);

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }

        // Setup Audio Analyser for Mic volume meter
        const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
        audioCtxRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 256;
        source.connect(analyser);

        const dataArray = new Uint8Array(analyser.frequencyBinCount);
        const checkVolume = () => {
          analyser.getByteFrequencyData(dataArray);
          let sum = 0;
          for (let i = 0; i < dataArray.length; i++) {
            sum += dataArray[i];
          }
          const avg = sum / dataArray.length;
          setMicVolume(Math.min(100, Math.round((avg / 128) * 100)));
          animationFrameRef.current = requestAnimationFrame(checkVolume);
        };
        checkVolume();

        // Enumerate devices
        const deviceList = await navigator.mediaDevices.enumerateDevices();
        const cameras = deviceList.filter((d) => d.kind === 'videoinput');
        const microphones = deviceList.filter((d) => d.kind === 'audioinput');
        const speakers = deviceList.filter((d) => d.kind === 'audiooutput');

        setDevices({ cameras, microphones, speakers });
        if (cameras[0]) setSelectedCamera(cameras[0].deviceId);
        if (microphones[0]) setSelectedMicrophone(microphones[0].deviceId);
        if (speakers[0]) setSelectedSpeaker(speakers[0].deviceId);
      } catch (err) {
        console.warn('Device permission error:', err);
        setHasPermission(false);
      }
    }

    initMedia();

    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop());
      }
      if (audioCtxRef.current) {
        audioCtxRef.current.close();
      }
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  const toggleCamera = () => {
    if (streamRef.current) {
      const videoTracks = streamRef.current.getVideoTracks();
      videoTracks.forEach((t) => (t.enabled = !t.enabled));
      setIsCameraActive(!isCameraActive);
    }
  };

  const toggleMicrophone = () => {
    if (streamRef.current) {
      const audioTracks = streamRef.current.getAudioTracks();
      audioTracks.forEach((t) => (t.enabled = !t.enabled));
      setIsMicrophoneActive(!isMicrophoneActive);
    }
  };

  const playSpeakerTest = () => {
    const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.connect(gain);
    gain.connect(audioCtx.destination);
    osc.frequency.setValueAtTime(440, audioCtx.currentTime); // A4 note
    gain.gain.setValueAtTime(0.1, audioCtx.currentTime);
    osc.start();
    osc.stop(audioCtx.currentTime + 0.4);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-slate-400 text-xs">
        Connecting to Waiting Room...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Top Banner */}
      <div className="text-center space-y-2 pb-4 border-b border-slate-800">
        <Badge variant="outline" className="border-indigo-500/40 text-indigo-400 text-[10px] font-mono uppercase">
          {waitingRoomData?.workspace_name || 'InterviewOS'} Technical Interview
        </Badge>
        <h1 className="text-2xl font-bold text-white tracking-tight">
          {waitingRoomData?.interview_title || 'Live Technical Assessment'}
        </h1>
        <p className="text-xs text-slate-400 max-w-lg mx-auto">
          Welcome, <strong>{waitingRoomData?.candidate_name}</strong>. Please verify your camera, microphone, and speakers before entering the interview room.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Device Preview (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="p-3 bg-slate-900/90 border-slate-800 space-y-3">
            {/* Video Viewport */}
            <div className="relative aspect-video rounded-xl bg-slate-950 overflow-hidden border border-slate-800 flex items-center justify-center">
              <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover -scale-x-100 ${!isCameraActive ? 'hidden' : ''}`}
              />
              {!isCameraActive && (
                <div className="flex flex-col items-center gap-2 text-slate-500">
                  <VideoOff className="w-8 h-8" />
                  <span className="text-xs">Camera is turned off</span>
                </div>
              )}

              {/* In-viewport quick buttons */}
              <div className="absolute bottom-3 left-1/2 -translate-x-1/2 flex items-center gap-2 bg-slate-900/80 backdrop-blur-md px-3 py-1.5 rounded-full border border-slate-700/60 shadow-xl">
                <button
                  onClick={toggleCamera}
                  className={`p-2 rounded-full transition-colors ${
                    isCameraActive ? 'bg-slate-800 text-white hover:bg-slate-700' : 'bg-rose-600 text-white'
                  }`}
                >
                  {isCameraActive ? <Video className="w-4 h-4" /> : <VideoOff className="w-4 h-4" />}
                </button>
                <button
                  onClick={toggleMicrophone}
                  className={`p-2 rounded-full transition-colors ${
                    isMicrophoneActive ? 'bg-slate-800 text-white hover:bg-slate-700' : 'bg-rose-600 text-white'
                  }`}
                >
                  {isMicrophoneActive ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Mic Meter */}
            <div className="space-y-1 px-1">
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span>Microphone Input Level</span>
                <span>{micVolume}%</span>
              </div>
              <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-75"
                  style={{ width: `${micVolume}%` }}
                />
              </div>
            </div>

            {/* Device Selectors */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2 border-t border-slate-800/80 text-xs">
              <div>
                <label className="text-[10px] font-mono text-slate-400 block mb-1">Camera</label>
                <select
                  value={selectedCamera}
                  onChange={(e) => setSelectedCamera(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded p-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {devices.cameras.map((c) => (
                    <option key={c.deviceId} value={c.deviceId}>
                      {c.label || `Camera ${c.deviceId.slice(0, 5)}`}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-mono text-slate-400 block mb-1">Microphone</label>
                <select
                  value={selectedMicrophone}
                  onChange={(e) => setSelectedMicrophone(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded p-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                >
                  {devices.microphones.map((m) => (
                    <option key={m.deviceId} value={m.deviceId}>
                      {m.label || `Mic ${m.deviceId.slice(0, 5)}`}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-mono text-slate-400 block mb-1">Speaker Test</label>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={playSpeakerTest}
                  className="w-full border-slate-800 bg-slate-950 text-slate-300 hover:text-white text-xs h-8 flex items-center justify-center gap-1.5"
                >
                  <Volume2 className="w-3.5 h-3.5 text-indigo-400" />
                  <span>Play Test Sound</span>
                </Button>
              </div>
            </div>
          </Card>
        </div>

        {/* Right: Instructions & Join (5 cols) */}
        <div className="lg:col-span-5 space-y-4 flex flex-col justify-between">
          <div className="space-y-3">
            <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-2.5">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-1.5">
                <Clock className="w-3.5 h-3.5 text-amber-400" /> Interview Overview
              </h3>
              <div className="text-xs text-slate-300 space-y-1.5">
                <div className="flex justify-between">
                  <span className="text-slate-400">Duration:</span>
                  <span className="font-semibold text-white">{waitingRoomData?.duration_minutes || 60} Minutes</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Format:</span>
                  <span className="font-semibold text-white">Live Code & Architecture</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Connection:</span>
                  <span className="text-emerald-400 flex items-center gap-1">
                    <Wifi className="w-3 h-3" /> Ready
                  </span>
                </div>
              </div>
            </Card>

            <Card className="p-4 bg-slate-900/60 border-slate-800 space-y-2">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Instructions for Candidates
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                {waitingRoomData?.instructions ||
                  'You will collaborate with your interviewer on algorithmic problems and cloud architecture design. Ensure you are in a quiet environment with a stable internet connection.'}
              </p>
            </Card>
          </div>

          <Button
            size="lg"
            onClick={() => router.push(`/interviews/${interviewId}/room`)}
            className="w-full bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold h-11 flex items-center justify-center gap-2 shadow-xl shadow-indigo-600/25"
          >
            <span>Join Interview Room</span>
            <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}
