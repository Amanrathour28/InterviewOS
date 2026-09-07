'use client';

/**
 * Candidate Interview Room — Phase 17
 *
 * Reuses existing CodingWorkspace, WhiteboardWorkspace, ChatPanel, and VideoTile
 * components from the interviewer room.  Explicitly hides all interviewer-only UI.
 *
 * Candidate CAN see:   video, chat, coding, whiteboard
 * Candidate CANNOT:    AI copilot, evaluation controls, notes, evidence, hiring decision
 */
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Terminal,
  Video,
  Code2,
  PenTool,
  MessageSquare,
  Mic,
  MicOff,
  Camera,
  CameraOff,
  LogOut,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { getCandidateSession, clearCandidateSession } from '@/lib/candidate-session';
import { ChatPanel } from '@/components/interview-room/chat/chat-panel';
import { CodingWorkspace } from '@/components/interview-room/coding/coding-workspace';
import { WhiteboardWorkspace } from '@/components/interview-room/whiteboard/whiteboard-workspace';
import { VideoTile } from '@/components/interview-room/video-tile';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' ? '/api/v1' : 'http://127.0.0.1:8000/api/v1');

type CandidateTab = 'video' | 'code' | 'whiteboard' | 'chat';

export default function CandidateRoomPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const [activeTab, setActiveTab] = useState<CandidateTab>('video');
  const [sessionMissing, setSessionMissing] = useState(false);
  const [interviewId, setInterviewId] = useState<string | null>(null);
  const [candidateName, setCandidateName] = useState('');
  const [isMicEnabled, setIsMicEnabled] = useState(true);
  const [isCameraEnabled, setIsCameraEnabled] = useState(true);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string | null>(null);

  const streamRef = useRef<MediaStream | null>(null);

  // Validate candidate session
  useEffect(() => {
    const session = getCandidateSession(token);
    if (!session) {
      setSessionMissing(true);
      setIsLoading(false);
      return;
    }
    setInterviewId(session.interviewId);
    setCandidateName(session.candidateName);
  }, [token]);

  // Start local media
  const startMedia = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: isCameraEnabled,
        audio: isMicEnabled,
      });
      streamRef.current = stream;
      setLocalStream(stream);
    } catch {
      // Media unavailable — proceed without it
    } finally {
      setIsLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch/create session for collaborative tools
  useEffect(() => {
    if (!interviewId) return;
    const session = getCandidateSession(token);
    if (!session) return;

    (async () => {
      try {
        const res = await fetch(`${API_BASE}/interviews/${interviewId}/session`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.candidateSessionToken}`,
            'Content-Type': 'application/json',
          },
        });
        if (res.ok) {
          const data = await res.json();
          setSessionId(data.id);
        }
      } catch {
        // Session fetch failed — collaborative tools will work in degraded mode
      }
      await startMedia();
    })();

    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, [interviewId, token, startMedia]);

  const toggleMic = () => {
    const tracks = streamRef.current?.getAudioTracks() || [];
    const newState = !isMicEnabled;
    tracks.forEach((t) => { t.enabled = newState; });
    setIsMicEnabled(newState);
  };

  const toggleCamera = () => {
    const tracks = streamRef.current?.getVideoTracks() || [];
    const newState = !isCameraEnabled;
    tracks.forEach((t) => { t.enabled = newState; });
    setIsCameraEnabled(newState);
  };

  const handleLeave = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    clearCandidateSession();
    router.push(`/join/${token}/complete`);
  };

  const tabs: { id: CandidateTab; label: string; icon: React.ElementType }[] = [
    { id: 'video', label: 'Video', icon: Video },
    { id: 'code', label: 'Code', icon: Code2 },
    { id: 'whiteboard', label: 'Board', icon: PenTool },
    { id: 'chat', label: 'Chat', icon: MessageSquare },
  ];

  if (sessionMissing) {
    return (
      <div className="min-h-screen bg-[#07080c] text-white flex items-center justify-center p-4">
        <div className="max-w-md w-full rounded-2xl border border-zinc-800 bg-[#0d0e14] p-8 text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
          <h1 className="text-lg font-bold">Session Expired</h1>
          <p className="text-sm text-zinc-400">
            Your interview session has expired. Please rejoin using your interview link.
          </p>
          <button
            onClick={() => router.push(`/join/${token}`)}
            className="text-sm text-indigo-400 hover:text-indigo-300"
          >
            ← Rejoin interview
          </button>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#07080c] flex items-center justify-center">
        <div className="text-center space-y-3">
          <Loader2 className="h-8 w-8 animate-spin text-indigo-400 mx-auto" />
          <p className="text-xs text-zinc-500">Connecting to interview…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen w-screen bg-[#07080c] text-white overflow-hidden select-none">
      {/* Header */}
      <header className="h-12 shrink-0 flex items-center justify-between px-3.5 border-b border-zinc-800 bg-[#09090b]/90 backdrop-blur-md z-10 gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="h-7 w-7 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 shrink-0">
            <Terminal className="h-3.5 w-3.5" />
          </div>
          <span className="font-bold text-xs shrink-0">
            Interview<span className="text-indigo-400 font-black">OS</span>
          </span>
          <span className="text-zinc-700 hidden sm:inline">•</span>
          <span className="text-xs text-indigo-400 font-mono hidden sm:inline truncate">Live Assessment</span>
        </div>

        {candidateName && (
          <div className="min-w-0 max-w-[140px] sm:max-w-[200px] text-center">
            <span className="text-xs text-zinc-300 font-medium truncate block">{candidateName}</span>
          </div>
        )}

        {/* Media controls & leave */}
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            onClick={toggleMic}
            title={isMicEnabled ? 'Mute microphone' : 'Unmute microphone'}
            className={`p-2 rounded-lg border transition-colors ${
              isMicEnabled
                ? 'border-zinc-700 bg-zinc-800 text-zinc-300 hover:border-zinc-600'
                : 'border-rose-500/40 bg-rose-950/30 text-rose-400'
            }`}
          >
            {isMicEnabled ? <Mic className="h-3.5 w-3.5" /> : <MicOff className="h-3.5 w-3.5" />}
          </button>
          <button
            onClick={toggleCamera}
            title={isCameraEnabled ? 'Turn off camera' : 'Turn on camera'}
            className={`p-2 rounded-lg border transition-colors ${
              isCameraEnabled
                ? 'border-zinc-700 bg-zinc-800 text-zinc-300 hover:border-zinc-600'
                : 'border-rose-500/40 bg-rose-950/30 text-rose-400'
            }`}
          >
            {isCameraEnabled ? <Camera className="h-3.5 w-3.5" /> : <CameraOff className="h-3.5 w-3.5" />}
          </button>
          <button
            id="candidate-leave-room-btn"
            onClick={handleLeave}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-rose-500/30 bg-rose-950/20 text-rose-400 hover:bg-rose-950/40 text-xs font-semibold transition-colors"
          >
            <LogOut className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">Leave</span>
          </button>
        </div>
      </header>

      {/* Tab bar */}
      <div className="h-9 shrink-0 flex items-center gap-1 px-3 border-b border-zinc-800 bg-[#09090b] overflow-x-auto no-scrollbar">
        {tabs.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
              activeTab === id
                ? 'bg-zinc-800 text-white font-bold shadow-sm'
                : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900/60'
            }`}
          >
            <Icon className="h-3.5 w-3.5 text-indigo-400" />
            {label}
          </button>
        ))}
      </div>

      {/* Main content area */}
      <div className="flex-1 min-h-0 min-w-0 overflow-hidden relative flex flex-col">
        {activeTab === 'video' && (
          <div className="flex-1 min-h-0 p-3 sm:p-4 overflow-y-auto flex items-center justify-center">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4 w-full max-w-4xl h-full max-h-[calc(100vh-180px)]">
              {/* Local (candidate) video */}
              <VideoTile
                userId={`candidate-${token}`}
                userName={candidateName || 'You'}
                role="candidate"
                stream={localStream}
                isLocal
                cameraEnabled={isCameraEnabled}
                microphoneEnabled={isMicEnabled}
              />
              {/* Remote (interviewer) placeholder */}
              <div className="aspect-video w-full h-full min-h-[160px] sm:min-h-[200px] rounded-2xl border border-zinc-800 bg-zinc-900 flex items-center justify-center">
                <div className="text-center space-y-2 p-4">
                  <div className="h-10 w-10 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto">
                    <Video className="h-5 w-5 text-indigo-400" />
                  </div>
                  <p className="text-xs text-zinc-300 font-medium">Interviewer</p>
                  <p className="text-[10px] text-zinc-500 max-w-[200px]">
                    Live video connects when interviewer joins.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'code' && interviewId && sessionId && (
          <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
            <CodingWorkspace
              sessionId={sessionId}
              interviewId={interviewId}
              isInterviewer={false}
              realtimeClient={null}
            />
          </div>
        )}

        {activeTab === 'whiteboard' && interviewId && sessionId && (
          <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
            <WhiteboardWorkspace
              sessionId={sessionId}
              interviewId={interviewId}
              isInterviewer={false}
              realtimeClient={null}
            />
          </div>
        )}

        {activeTab === 'chat' && interviewId && sessionId && (
          <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
            <ChatPanel
              sessionId={sessionId}
              currentUserId={`candidate-${token}`}
              isInterviewer={false}
              realtimeClient={null}
            />
          </div>
        )}

        {/* Show message if session not yet established */}
        {(activeTab === 'code' || activeTab === 'whiteboard' || activeTab === 'chat') && (!interviewId || !sessionId) && (
          <div className="h-full flex items-center justify-center text-zinc-500 text-sm">
            Connecting to interview session…
          </div>
        )}
      </div>
    </div>
  );
}
