'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  Terminal,
  Video,
  Code2,
  PenTool,
  MessageSquare,
  FileText,
  Sparkles,
  Users,
  Mic,
  MicOff,
  Camera,
  CameraOff,
  ScreenShare,
  Settings,
  Activity,
  Play,
  Pause,
  StopCircle,
  Clock,
  Wifi,
  WifiOff,
  Layers,
  Shield,
  AlertCircle,
  LogOut,
  Maximize2,
  Bell,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { RealtimeClient, ConnectionState, resolveRealtimeUrl } from '@/lib/realtime/realtime-client';
import { useInterviewRoomStore, WorkspaceTab } from '@/lib/stores/use-interview-room-store';
import { MediaManager } from '@/lib/webrtc/media-manager';
import { PeerConnectionManager } from '@/lib/webrtc/peer-connection-manager';
import { SignalingManager } from '@/lib/webrtc/signaling-manager';
import { MediaDeviceSettings } from '@/lib/webrtc/types';
import { AudioSTTManager } from '@/lib/webrtc/audio-stt-manager';
import { buildEffectiveIceServers, resolveIceTransportPolicy } from '@/lib/webrtc/ice-config';
import { VideoTile } from '@/components/interview-room/video-tile';
import { DeviceCheckModal } from '@/components/interview-room/device-check-modal';
import { DeviceSettingsModal } from '@/components/interview-room/device-settings-modal';
import { NetworkDiagnosticsModal } from '@/components/interview-room/network-diagnostics-modal';
import { ChatPanel } from '@/components/interview-room/chat/chat-panel';
import { CodingWorkspace } from '@/components/interview-room/coding/coding-workspace';
import { WhiteboardWorkspace } from '@/components/interview-room/whiteboard/whiteboard-workspace';
import { StageStepper } from '@/components/interview-room/control-center/stage-stepper';
import { InterviewTimer } from '@/components/interview-room/control-center/interview-timer';
import { ActivityTimelineDrawer } from '@/components/interview-room/control-center/activity-timeline-drawer';
import { StructuredNotesPanel } from '@/components/interview-room/control-center/structured-notes-panel';
import { QuickActionsMenu } from '@/components/interview-room/control-center/quick-actions-menu';
import { SessionHealthIndicator } from '@/components/interview-room/control-center/session-health-indicator';
import { EndInterviewModal } from '@/components/interview-room/control-center/end-interview-modal';
import { AIStatusBadge } from '@/components/interview-room/ai/ai-status-badge';
import { AICopilotPanel } from '@/components/interview-room/ai/ai-copilot-panel';
import { useChatStore } from '@/lib/stores/use-chat-store';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

export default function InterviewRoomPage() {
  const params = useParams();
  const router = useRouter();
  const interviewId = params?.interviewId as string;

  const {
    session,
    participants,
    connectionState,
    activeTab,
    currentStage,
    elapsedSeconds,
    isInterviewer,
    events,
    privateNotes,
    isPreJoinDone,
    localStream,
    isCameraEnabled,
    isMicEnabled,
    isScreenSharing,
    activeSpeakerId,
    remoteStreams,
    deviceSettings,
    diagnostics,
    isSettingsModalOpen,
    isDiagnosticsModalOpen,
    setSession,
    setParticipants,
    updateParticipantPresence,
    setConnectionState,
    setActiveTab,
    setCurrentStage,
    setElapsedSeconds,
    addEvent,
    setPrivateNotes,
    setIsPreJoinDone,
    setLocalStream,
    setIsCameraEnabled,
    setIsMicEnabled,
    setIsScreenSharing,
    setActiveSpeakerId,
    setRemoteStream,
    removeRemoteStream,
    setDeviceSettings,
    setDiagnostics,
    setIsSettingsModalOpen,
    setIsDiagnosticsModalOpen,
    reset,
  } = useInterviewRoomStore();

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [isSubmittingAction, setIsSubmittingAction] = useState(false);
  const [isEndModalOpen, setIsEndModalOpen] = useState(false);
  const [isTimelineOpen, setIsTimelineOpen] = useState(false);
  const [stageAlert, setStageAlert] = useState<string | null>(null);

  // WebRTC & Gateway References
  const [realtimeClient, setRealtimeClient] = useState<RealtimeClient | null>(null);
  const realtimeClientRef = useRef<RealtimeClient | null>(null);
  const mediaManagerRef = useRef<MediaManager | null>(null);
  const peerManagerRef = useRef<PeerConnectionManager | null>(null);
  const signalingManagerRef = useRef<SignalingManager | null>(null);
  const audioSTTManagerRef = useRef<AudioSTTManager | null>(null);
  const joinDataRef = useRef<any | null>(null);

  // 1. Initial Room Session Fetch
  const fetchSessionData = useCallback(async () => {
    if (!interviewId) return;
    setIsLoading(true);
    setError(null);

    try {
      // Get or create session
      const sessionData = await apiClient<any>(`/interviews/${interviewId}/session`, {
        method: 'POST',
      });
      const sessionId = sessionData.id;

      // Fetch detail
      const detail = await apiClient<any>(`/sessions/${sessionId}`);
      setSession(detail);
      setElapsedSeconds(detail.current_elapsed_seconds || 0);
      if (detail.current_stage) {
        setCurrentStage(detail.current_stage);
      }

      // Fetch join token & ICE servers
      const joinData = await apiClient<any>(`/sessions/${sessionId}/join-token`, {
        method: 'POST',
      });
      joinDataRef.current = joinData;
    } catch (err: any) {
      setError(err.message || 'Failed to initialize interview room');
    } finally {
      setIsLoading(false);
    }
  }, [interviewId, setSession, setElapsedSeconds, setCurrentStage]);

  useEffect(() => {
    fetchSessionData();
    return () => {
      audioSTTManagerRef.current?.stop();
      mediaManagerRef.current?.stopAllTracks();
      peerManagerRef.current?.closeAll();
      realtimeClientRef.current?.disconnect();
      reset();
    };
  }, [fetchSessionData, reset]);

  // 2. Setup WebRTC & Realtime once Pre-Join Check is completed
  const handlePreJoinComplete = async (setup: {
    stream: MediaStream;
    cameraEnabled: boolean;
    micEnabled: boolean;
    devices: MediaDeviceSettings;
  }) => {
    setIsPreJoinDone(true);
    let activeStream = setup.stream;

    // Verify stream tracks are live; re-acquire if ended
    const vTracks = activeStream?.getVideoTracks() || [];
    const isLive = vTracks.length > 0 && vTracks.some((t) => t.readyState === 'live');
    if (!isLive && setup.cameraEnabled) {
      console.log('[Media] Stream tracks ended, re-acquiring fresh local media stream in room...');
      try {
        const freshStream = await navigator.mediaDevices.getUserMedia({
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
        activeStream = freshStream;
        console.log('[Media] Successfully re-acquired fresh local media stream');
      } catch (err: any) {
        console.warn('[Media] Failed to re-acquire fresh media stream:', err);
      }
    }

    setLocalStream(activeStream);
    setIsCameraEnabled(setup.cameraEnabled);
    setIsMicEnabled(setup.micEnabled);
    setDeviceSettings(setup.devices);

    const joinData = joinDataRef.current;
    if (!joinData || !session) return;

    // Initialize MediaManager and assign localStream
    const mediaManager = new MediaManager();
    mediaManagerRef.current = mediaManager;
    mediaManager.setLocalStream(activeStream);

    // Initialize PeerConnectionManager with effective STUN/TURN servers
    const peerManager = new PeerConnectionManager({
      iceServers: buildEffectiveIceServers(joinData.ice_servers),
      iceTransportPolicy: resolveIceTransportPolicy(),
      sessionId: String(session.id),
      localUserId: String(joinData.user_id),
      localUserName: joinData.user_name || 'User',
      localUserRole: joinData.role || 'candidate',
    });
    peerManagerRef.current = peerManager;
    peerManager.setLocalStream(activeStream);

    // Track replacement wire-up
    mediaManager.setTrackReplacementCallback((kind, newTrack) => {
      peerManager.replaceTrack(kind, newTrack);
    });

    // Initialize RealtimeClient
    const realtimeClient = new RealtimeClient({
      url: resolveRealtimeUrl(joinData.realtime_url),
      token: joinData.token,
      onConnectionChange: (state: ConnectionState) => {
        setConnectionState(state);
      },
      onSync: (syncData: any) => {
        if (syncData.participants) {
          setParticipants(syncData.participants);
          // Auto-initiate mesh peer connections for existing participants
          syncData.participants.forEach((p: any) => {
            if (p.userId !== joinData.user_id && p.online) {
              peerManager.getOrCreatePeer(p.userId, p.userName, p.role);
            }
          });
        }
      },
      onEvent: (event: any) => {
        addEvent(event);
        if (event.event_type === 'PARTICIPANT_JOINED') {
          updateParticipantPresence(event.payload.user_id, true, event.payload.role, event.payload.user_name);
          if (event.payload.user_id !== joinData.user_id) {
            peerManager.getOrCreatePeer(event.payload.user_id, event.payload.user_name, event.payload.role);
          }
        } else if (event.event_type === 'PARTICIPANT_LEFT') {
          updateParticipantPresence(event.payload.user_id, false, event.payload.role);
          peerManager.removePeer(event.payload.user_id);
          removeRemoteStream(event.payload.user_id);
        } else if (event.event_type === 'PARTICIPANT_STATUS_CHANGED') {
          updateParticipantPresence(event.payload.user_id, true, undefined, undefined, event.payload.deviceState);
          setRemoteStream(event.payload.user_id, {
            cameraEnabled: event.payload.deviceState?.camera !== false,
            microphoneEnabled: event.payload.deviceState?.microphone !== false,
            screenSharing: Boolean(event.payload.deviceState?.screenShare),
          });
        } else if (event.event_type === 'STAGE_CHANGED') {
          const newStage = event.payload?.new_stage || event.payload?.stage;
          if (newStage) {
            setCurrentStage(newStage);
            setStageAlert(event.payload.stage_name || newStage.replace('_', ' ').toUpperCase());
            setTimeout(() => setStageAlert(null), 4500);
          }
        } else if (event.event_type === 'SESSION_STARTED') {
          setSession({ ...session, status: 'active', started_at: event.payload.started_at });
        } else if (event.event_type === 'SESSION_PAUSED') {
          setSession({ ...session, status: 'paused', paused_at: new Date().toISOString() });
        } else if (event.event_type === 'SESSION_RESUMED') {
          setSession({ ...session, status: 'active', paused_at: null });
        } else if (event.event_type === 'SESSION_ENDED') {
          setSession({ ...session, status: 'completed', ended_at: event.payload.ended_at });
          router.push(`/interviews/${interviewId}/complete`);
        } else if (event.event_type === 'CHAT_MESSAGE_CREATED') {
          const channelId = event.payload?.channel_id;
          if (channelId && event.payload?.message) {
            useChatStore.getState().addMessage(channelId, event.payload.message);
          } else if (channelId) {
            const currentActiveId = useChatStore.getState().activeChannelId;
            if (currentActiveId === channelId) {
              apiClient<any[]>(`/chat/channels/${channelId}/messages?limit=50`)
                .then((msgs) => useChatStore.getState().setMessages(channelId, msgs))
                .catch(() => {});
            } else {
              const channels = useChatStore.getState().channels.map((c) =>
                c.id === channelId ? { ...c, unread_count: c.unread_count + 1 } : c
              );
              useChatStore.getState().setChannels(channels);
            }
          }
        } else if (event.event_type === 'CHAT_THREAD_REPLY_CREATED') {
          if (event.payload?.parent_message_id) {
            apiClient<{ parent_message: any; replies: any[] }>(
              `/chat/messages/${event.payload.parent_message_id}/thread`
            )
              .then((res) => useChatStore.getState().setThread(event.payload.parent_message_id, res.replies))
              .catch(() => {});
          }
        } else if (
          event.event_type === 'CHAT_MESSAGE_UPDATED' ||
          event.event_type === 'CHAT_MESSAGE_DELETED' ||
          event.event_type === 'CHAT_REACTION_ADDED' ||
          event.event_type === 'CHAT_REACTION_REMOVED'
        ) {
          const currentActiveId = useChatStore.getState().activeChannelId;
          if (currentActiveId === event.payload?.channel_id) {
            apiClient<any[]>(`/chat/channels/${event.payload.channel_id}/messages?limit=50`)
              .then((msgs) => useChatStore.getState().setMessages(event.payload.channel_id, msgs))
              .catch(() => {});
          }
        }
      },
      onError: (err: any) => {
        console.error('[Room Socket Error]:', err);
      },
    });
    realtimeClientRef.current = realtimeClient;
    setRealtimeClient(realtimeClient);

    // Connect Signaling Manager
    const signalingManager = new SignalingManager(realtimeClient, peerManager);
    signalingManagerRef.current = signalingManager;
    signalingManager.initialize();

    // Wire-up PeerManager Callbacks to Zustand Store
    peerManager.setCallbacks({
      onSendSignal: (msg) => {
        realtimeClient.sendSignaling(msg);
      },
      onRemoteStreamAdded: (userId, rStream) => {
        setRemoteStream(userId, { stream: rStream });
      },
      onPeerConnectionChanged: (userId, connState, iceState) => {
        setRemoteStream(userId, {
          connectionState: connState,
          iceConnectionState: iceState,
        });
      },
      onActiveSpeakerChanged: (userId, level, isActive) => {
        setActiveSpeakerId(isActive ? userId : null);
      },
      onDiagnosticsUpdated: (userId, stats) => {
        setDiagnostics(userId, stats);
      },
    });

    // Connect Realtime Socket
    realtimeClient.connect();

    // Broadcast candidate ready status if candidate
    if (!session.is_interviewer) {
      realtimeClient.emit('candidate_ready', { candidate_name: joinData.user_name });
    }

    // Initialize AudioSTTManager for live microphone capture and speech transcription
    const audioSTT = new AudioSTTManager({
      interviewId: interviewId,
      speakerRole: session.is_interviewer ? 'interviewer' : 'candidate',
      onTranscript: (segment, boundaryStatus) => {
        if (realtimeClientRef.current) {
          realtimeClientRef.current.emit('transcript_segment', {
            segment: segment,
            boundary_status: boundaryStatus,
          });
        }
      },
    });
    audioSTTManagerRef.current = audioSTT;
    if (setup.micEnabled && setup.stream) {
      audioSTT.start(setup.stream);
    }
  };

  // 3. Stage Stepper Selection Handler
  const handleStageSelect = async (stageId: string) => {
    if (!session || !isInterviewer) return;
    try {
      await apiClient(`/sessions/${session.id}/stage`, {
        method: 'POST',
        body: JSON.stringify({ stage: stageId }),
      });
      setCurrentStage(stageId);
      realtimeClientRef.current?.emit('stage_transition', { stage: stageId });
    } catch (err) {
      console.error('Failed to change stage:', err);
    }
  };

  // 4. Session Pause / Resume Toggle
  const handleTogglePause = async () => {
    if (!session || !isInterviewer) return;
    try {
      if (session.status === 'paused') {
        const res = await apiClient<any>(`/sessions/${session.id}/resume`, { method: 'POST' });
        setSession({ ...session, status: 'active', paused_at: null });
        realtimeClientRef.current?.emit('dispatch_event', { event_type: 'SESSION_RESUMED', payload: {} });
      } else {
        const res = await apiClient<any>(`/sessions/${session.id}/pause`, {
          method: 'POST',
          body: JSON.stringify({ reason: 'Paused by interviewer' }),
        });
        setSession({ ...session, status: 'paused', paused_at: new Date().toISOString() });
        realtimeClientRef.current?.emit('dispatch_event', { event_type: 'SESSION_PAUSED', payload: {} });
      }
    } catch (err) {
      console.error('Failed to toggle session pause:', err);
    }
  };

  // 5. Start Session Handler
  const handleStartSession = async () => {
    if (!session || !isInterviewer) return;
    try {
      setIsSubmittingAction(true);
      const res = await apiClient<any>(`/sessions/${session.id}/start`, { method: 'POST' });
      setSession({ ...session, status: 'active', started_at: res.started_at });
      realtimeClientRef.current?.emit('dispatch_event', {
        event_type: 'SESSION_STARTED',
        payload: { started_at: res.started_at },
      });
    } catch (err) {
      console.error('Failed to start session:', err);
    } finally {
      setIsSubmittingAction(false);
    }
  };

  // 6. End Session Handler
  const handleConfirmEnd = async () => {
    if (!session || !isInterviewer) return;
    try {
      setIsSubmittingAction(true);
      await apiClient<any>(`/sessions/${session.id}/end`, {
        method: 'POST',
        body: JSON.stringify({ reason: 'Interview completed normally' }),
      });
      realtimeClientRef.current?.emit('dispatch_event', {
        event_type: 'SESSION_ENDED',
        payload: { ended_at: new Date().toISOString() },
      });
      setIsEndModalOpen(false);
      router.push(`/interviews/${interviewId}/complete`);
    } catch (err) {
      console.error('Failed to end session:', err);
    } finally {
      setIsSubmittingAction(false);
    }
  };

  // Media Toggle Handlers
  const handleToggleCamera = async () => {
    const newState = !isCameraEnabled;
    setIsCameraEnabled(newState);
    if (mediaManagerRef.current) {
      await mediaManagerRef.current.toggleCamera(newState);
    }
    if (localStream) {
      localStream.getVideoTracks().forEach((t) => {
        t.enabled = newState;
      });
    }
    realtimeClientRef.current?.sendMediaState({
      camera: newState,
      microphone: isMicEnabled,
      screenShare: isScreenSharing,
    });
  };

  const handleToggleMic = async () => {
    const newState = !isMicEnabled;
    setIsMicEnabled(newState);
    if (mediaManagerRef.current) {
      await mediaManagerRef.current.toggleMicrophone(newState);
    }
    if (localStream) {
      localStream.getAudioTracks().forEach((t) => {
        t.enabled = newState;
      });
    }
    realtimeClientRef.current?.sendMediaState({
      camera: isCameraEnabled,
      microphone: newState,
      screenShare: isScreenSharing,
    });
  };

  const handleToggleScreenShare = async () => {
    if (!mediaManagerRef.current || !peerManagerRef.current) return;
    try {
      if (isScreenSharing) {
        await mediaManagerRef.current.stopScreenShare();
        setIsScreenSharing(false);
        const originalVideoTrack = mediaManagerRef.current.getVideoTrack();
        if (originalVideoTrack) {
          peerManagerRef.current.replaceTrack('video', originalVideoTrack);
        }
        realtimeClientRef.current?.sendMediaState({
          camera: isCameraEnabled,
          microphone: isMicEnabled,
          screenShare: false,
        });
      } else {
        const screenTrack = await mediaManagerRef.current.startScreenShare();
        setIsScreenSharing(true);
        if (screenTrack) {
          peerManagerRef.current.replaceTrack('video', screenTrack);
          screenTrack.onended = () => {
            handleToggleScreenShare();
          };
        }
        realtimeClientRef.current?.sendMediaState({
          camera: isCameraEnabled,
          microphone: isMicEnabled,
          screenShare: true,
        });
      }
    } catch (err) {
      console.error('Screen sharing error:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="h-screen w-screen bg-[#07080c] flex items-center justify-center text-slate-400 text-xs">
        Loading Interview Control Center...
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="h-screen w-screen bg-[#07080c] flex items-center justify-center p-4">
        <Card className="max-w-md w-full border-slate-800 bg-[#0d0e14] p-8 text-center space-y-4 shadow-2xl">
          <div className="h-12 w-12 rounded-full bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center justify-center mx-auto">
            <AlertCircle className="h-6 w-6" />
          </div>
          <h2 className="text-lg font-bold text-white">Room Unavailable</h2>
          <p className="text-xs text-slate-400 leading-relaxed">{error || 'Session could not be loaded.'}</p>
          <Link href={`/interviews/${interviewId}`}>
            <Button size="sm" variant="outline" className="text-xs border-slate-800">
              Return to Interview Detail
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  // Pre-join Device Check Gate
  if (!isPreJoinDone) {
    return (
      <DeviceCheckModal
        onJoin={handlePreJoinComplete}
        interviewTitle={session.interview_title}
        candidateName={session.candidate_name}
      />
    );
  }

  const activeRemoteScreenShare = Object.values(remoteStreams).find((p) => p.screenSharing);
  const activeScreenStream = isScreenSharing
    ? mediaManagerRef.current?.getScreenStream() || localStream
    : activeRemoteScreenShare?.stream || null;

  return (
    <div className="h-screen w-screen bg-[#07080c] text-white flex flex-col overflow-hidden select-none">
      {/* 1. TOP INTERVIEW HEADER / TIMER / ACTIONS */}
      <header className="h-12 border-b border-slate-800/80 bg-[#0d0e14]/95 px-3.5 flex items-center justify-between shrink-0 gap-2.5 z-20">
        {/* Left: Branding & Candidate Badge */}
        <div className="flex items-center gap-2 shrink-0 min-w-0">
          <Link
            href={`/interviews/${interviewId}`}
            className="flex items-center gap-1.5 text-slate-400 hover:text-white transition-colors shrink-0"
          >
            <div className="h-7 w-7 rounded-lg bg-indigo-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400">
              <Terminal className="h-3.5 w-3.5" />
            </div>
            <span className="font-bold text-xs tracking-tight text-white hidden sm:inline">InterviewOS</span>
          </Link>

          <span className="text-slate-700 hidden sm:inline">•</span>

          <div className="min-w-0 max-w-[150px] sm:max-w-[200px] lg:max-w-[280px]">
            <h2 className="text-xs font-bold text-white truncate">{session.interview_title}</h2>
            <p className="text-[10px] text-slate-400 truncate">
              {isInterviewer ? (
                <>Candidate: <span className="text-slate-200">{session.candidate_name || 'Candidate'}</span></>
              ) : (
                <span className="text-indigo-400 font-mono">Live Assessment</span>
              )}
            </p>
          </div>
        </div>

        {/* Center: Synchronized Timer */}
        <div className="flex items-center justify-center shrink-0">
          <InterviewTimer
            startedAt={session.started_at}
            pausedAt={session.paused_at}
            stageStartedAt={session.stage_started_at}
            totalPausedSeconds={session.total_paused_seconds || 0}
            durationMinutes={session.duration_minutes || 60}
            isPaused={session.status === 'paused'}
            status={session.status}
          />
        </div>

        {/* Right: Quick Actions, Diagnostics & Session Panel Toggle */}
        <div className="flex items-center gap-1.5 shrink-0">
          <QuickActionsMenu
            isInterviewer={isInterviewer}
            isPaused={session.status === 'paused'}
            status={session.status}
            onTogglePause={handleTogglePause}
            onOpenTimeline={() => setIsTimelineOpen(true)}
            onOpenEndModal={() => setIsEndModalOpen(true)}
          />

          {isInterviewer && (
            <AIStatusBadge onClick={() => setActiveTab('ai')} />
          )}

          <SessionHealthIndicator
            connectionState={connectionState}
            isPaused={session.status === 'paused'}
            activeParticipantsCount={participants.length}
            webrtcState={Object.values(remoteStreams)[0]?.connectionState}
            remoteVideoReceived={Object.values(remoteStreams).some((r: any) => Boolean(r.stream))}
          />

          <Button
            size="sm"
            variant="ghost"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className={`h-7 px-2 text-xs transition-colors ${
              isSidebarOpen ? 'bg-slate-800 text-white font-semibold' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Users className="h-3.5 w-3.5 mr-1 text-slate-400" />
            <span className="hidden sm:inline">Panel ({participants.length})</span>
          </Button>
        </div>
      </header>

      {/* 2. DEDICATED STAGE NAVIGATION BAR */}
      <div className="h-9 border-b border-slate-800/60 bg-[#090a0f] px-3.5 flex items-center justify-between shrink-0 gap-2 z-10">
        <div className="flex-1 min-w-0 overflow-x-auto no-scrollbar py-0.5">
          <StageStepper
            currentStage={currentStage}
            isInterviewer={isInterviewer}
            onSelectStage={handleStageSelect}
          />
        </div>

        {session.status === 'waiting' && isInterviewer && (
          <Button
            size="sm"
            onClick={handleStartSession}
            disabled={isSubmittingAction}
            className="bg-emerald-600 hover:bg-emerald-500 text-white text-[11px] h-6 px-2.5 flex items-center gap-1 shrink-0 shadow-sm shadow-emerald-600/20"
          >
            <Play className="w-2.5 h-2.5 fill-current" />
            <span>Start Session</span>
          </Button>
        )}
      </div>

      {/* Stage Transition Floating Toast Alert */}
      {stageAlert && (
        <div className="absolute top-24 left-1/2 -translate-x-1/2 z-50 bg-indigo-600/90 backdrop-blur-md border border-indigo-400/50 text-white text-xs font-semibold px-4 py-2 rounded-full shadow-2xl flex items-center gap-2 animate-in fade-in slide-in-from-top-2 duration-300">
          <Bell className="w-3.5 h-3.5 text-indigo-200 animate-bounce" />
          <span>Interview Stage Advanced to: <strong>{stageAlert}</strong></span>
        </div>
      )}

      {/* 3. MAIN WORKSPACE CONTAINER */}
      <div className="flex-1 min-h-0 flex overflow-hidden relative">
        {/* Workspace Central View */}
        <main className="flex-1 min-w-0 min-h-0 flex flex-col overflow-hidden bg-[#07080c]">
          {/* Workspace Tabs Header */}
          <div className="h-9 border-b border-slate-800 bg-slate-950/70 px-3 flex items-center gap-1 shrink-0 overflow-x-auto no-scrollbar">
            <button
              onClick={() => setActiveTab('video')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                activeTab === 'video' ? 'bg-slate-800 text-white font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Video className="h-3.5 w-3.5 text-indigo-400" />
              <span>Live Video</span>
            </button>

            <button
              onClick={() => setActiveTab('code')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                activeTab === 'code' ? 'bg-slate-800 text-white font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Code2 className="h-3.5 w-3.5 text-cyan-400" />
              <span>Collaborative Code</span>
            </button>

            <button
              onClick={() => setActiveTab('whiteboard')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                activeTab === 'whiteboard' ? 'bg-slate-800 text-white font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <PenTool className="h-3.5 w-3.5 text-purple-400" />
              <span>System Design Whiteboard</span>
            </button>

            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                activeTab === 'chat' ? 'bg-slate-800 text-white font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <MessageSquare className="h-3.5 w-3.5 text-emerald-400" />
              <span>Room Chat</span>
            </button>

            {isInterviewer && (
              <>
                <button
                  onClick={() => setActiveTab('notes')}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                    activeTab === 'notes' ? 'bg-slate-800 text-white font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <FileText className="h-3.5 w-3.5 text-purple-400" />
                  <span>Structured Notes</span>
                </button>

                <button
                  onClick={() => setActiveTab('ai')}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium transition-all ${
                    activeTab === 'ai' ? 'bg-slate-800 text-white font-bold shadow-sm' : 'text-slate-400 hover:text-slate-200'
                  }`}
                >
                  <Sparkles className="h-3.5 w-3.5 text-amber-400" />
                  <span>AI Copilot</span>
                </button>
              </>
            )}
          </div>

          {/* Active Workspace Body */}
          <div className="flex-1 min-h-0 min-w-0 overflow-hidden relative flex flex-col">
            {/* TAB: VIDEO */}
            {activeTab === 'video' && (
              <div className="flex-1 min-h-0 p-3 sm:p-4 overflow-y-auto flex items-center justify-center">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 sm:gap-4 w-full max-w-5xl h-full max-h-[calc(100vh-230px)]">
                  <VideoTile
                    userId={joinDataRef.current?.user_id || 'local'}
                    stream={localStream}
                    userName={`${joinDataRef.current?.user_name || 'You'} (You)`}
                    isLocal={true}
                    cameraEnabled={isCameraEnabled}
                    microphoneEnabled={isMicEnabled}
                    activeSpeaker={activeSpeakerId === joinDataRef.current?.user_id}
                    screenSharing={isScreenSharing}
                    role={joinDataRef.current?.role || 'interviewer'}
                  />

                  {Object.entries(remoteStreams).map(([remoteUserId, remoteData]) => {
                    const participantMeta = participants.find((p) => p.userId === remoteUserId);
                    return (
                      <VideoTile
                        key={remoteUserId}
                        userId={remoteUserId}
                        stream={remoteData.stream}
                        userName={participantMeta?.userName || 'Remote Participant'}
                        isLocal={false}
                        cameraEnabled={remoteData.cameraEnabled !== false}
                        microphoneEnabled={remoteData.microphoneEnabled !== false}
                        activeSpeaker={activeSpeakerId === remoteUserId}
                        screenSharing={remoteData.screenSharing}
                        connectionState={remoteData.connectionState}
                        role={participantMeta?.role || 'candidate'}
                      />
                    );
                  })}
                </div>
              </div>
            )}

            {/* TAB: CODE */}
            {activeTab === 'code' && (
              <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
                <CodingWorkspace
                  sessionId={session.id}
                  interviewId={interviewId}
                  isInterviewer={isInterviewer}
                  realtimeClient={realtimeClient}
                />
              </div>
            )}

            {/* TAB: WHITEBOARD */}
            {activeTab === 'whiteboard' && (
              <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
                <WhiteboardWorkspace
                  sessionId={session.id}
                  interviewId={interviewId}
                  isInterviewer={isInterviewer}
                  token={joinDataRef.current?.token}
                  realtimeClient={realtimeClient}
                />
              </div>
            )}

            {/* TAB: CHAT */}
            {activeTab === 'chat' && (
              <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
                <ChatPanel
                  sessionId={session.id}
                  currentUserId={joinDataRef.current?.user_id || ''}
                  isInterviewer={isInterviewer}
                  realtimeClient={realtimeClient}
                />
              </div>
            )}

            {/* TAB: STRUCTURED NOTES */}
            {activeTab === 'notes' && isInterviewer && (
              <div className="flex-1 min-h-0 min-w-0 overflow-y-auto p-3 sm:p-4">
                <StructuredNotesPanel
                  sessionId={session.id}
                  currentStage={currentStage}
                />
              </div>
            )}

            {/* TAB: AI COPILOT */}
            {activeTab === 'ai' && isInterviewer && (
              <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
                <AICopilotPanel
                  interviewId={interviewId}
                  workspaceId={session.workspace_id || ''}
                  sessionId={session.id}
                  currentStage={currentStage}
                  onClose={() => setActiveTab('video')}
                  onInsertNote={(text, category) => {
                    setActiveTab('notes');
                  }}
                />
              </div>
            )}
          </div>
        </main>

        {/* 4. COLLAPSIBLE PARTICIPANT SIDEBAR (SESSION PANEL) */}
        {isSidebarOpen && (
          <aside className="w-60 lg:w-64 xl:w-72 border-l border-slate-800/80 bg-[#0a0b10] flex flex-col shrink-0 min-h-0">
            <div className="h-9 border-b border-slate-800/80 px-3 flex items-center justify-between text-xs font-bold text-slate-400 uppercase tracking-wider shrink-0">
              <span>Session Panel ({participants.length})</span>
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="p-1 text-slate-500 hover:text-white rounded hover:bg-slate-800 transition-colors"
                title="Collapse Session Panel"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 min-h-0 p-2.5 space-y-1.5 overflow-y-auto">
              {participants.map((p) => (
                <div
                  key={p.userId}
                  className="p-2 rounded-lg border border-slate-800/90 bg-slate-950/70 flex items-center justify-between gap-2"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="relative shrink-0">
                      <div className="h-7 w-7 rounded-full bg-slate-800 flex items-center justify-center text-[11px] font-bold text-white uppercase">
                        {p.userName?.[0] || 'U'}
                      </div>
                      <span
                        className={`absolute bottom-0 right-0 h-2 w-2 rounded-full border border-slate-950 ${
                          p.online ? 'bg-emerald-400 ring-2 ring-emerald-400/20' : 'bg-slate-600'
                        }`}
                      />
                    </div>
                    <div className="min-w-0">
                      <p className="text-xs font-bold text-white truncate">{p.userName}</p>
                      <p className="text-[10px] text-slate-500 capitalize truncate">{p.role}</p>
                    </div>
                  </div>

                  <span className={`text-[10px] font-semibold shrink-0 ${p.online ? 'text-emerald-400' : 'text-slate-600'}`}>
                    {p.online ? 'Online' : 'Offline'}
                  </span>
                </div>
              ))}
            </div>
          </aside>
        )}


        {/* 4. ACTIVITY TIMELINE DRAWER */}
        <ActivityTimelineDrawer
          sessionId={session.id}
          isOpen={isTimelineOpen}
          onClose={() => setIsTimelineOpen(false)}
        />
      </div>

      {/* 5. BOTTOM ACTION CONTROL BAR */}
      <footer className="h-16 border-t border-slate-800/80 bg-[#0d0e14] px-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          {/* Mic */}
          <button
            onClick={handleToggleMic}
            className={`p-2.5 rounded-xl border transition-colors ${
              isMicEnabled
                ? 'bg-slate-800 text-white border-slate-700 hover:bg-slate-700'
                : 'bg-rose-600 text-white border-rose-500 hover:bg-rose-700'
            }`}
            title={isMicEnabled ? 'Mute Mic' : 'Unmute Mic'}
          >
            {isMicEnabled ? <Mic className="w-4 h-4" /> : <MicOff className="w-4 h-4" />}
          </button>

          {/* Camera */}
          <button
            onClick={handleToggleCamera}
            className={`p-2.5 rounded-xl border transition-colors ${
              isCameraEnabled
                ? 'bg-slate-800 text-white border-slate-700 hover:bg-slate-700'
                : 'bg-rose-600 text-white border-rose-500 hover:bg-rose-700'
            }`}
            title={isCameraEnabled ? 'Turn Off Camera' : 'Turn On Camera'}
          >
            {isCameraEnabled ? <Camera className="w-4 h-4" /> : <CameraOff className="w-4 h-4" />}
          </button>

          {/* Screen Share */}
          <button
            onClick={handleToggleScreenShare}
            className={`p-2.5 rounded-xl border transition-colors ${
              isScreenSharing
                ? 'bg-indigo-600 text-white border-indigo-500 hover:bg-indigo-700'
                : 'bg-slate-800 text-white border-slate-700 hover:bg-slate-700'
            }`}
            title={isScreenSharing ? 'Stop Screen Share' : 'Share Screen'}
          >
            <ScreenShare className="w-4 h-4" />
          </button>

          {/* Device Settings */}
          <button
            onClick={() => setIsSettingsModalOpen(true)}
            className="p-2.5 rounded-xl border border-slate-700 bg-slate-800 text-slate-300 hover:text-white hover:bg-slate-700 transition-colors"
            title="Audio / Video Settings"
          >
            <Settings className="w-4 h-4" />
          </button>
        </div>

        {/* End / Leave Room Button */}
        <div className="flex items-center gap-2">
          {isInterviewer ? (
            <Button
              onClick={() => setIsEndModalOpen(true)}
              className="bg-rose-600 hover:bg-rose-500 text-white text-xs h-9 px-4 flex items-center gap-1.5 shadow-lg shadow-rose-600/20"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Conclude Interview</span>
            </Button>
          ) : (
            <Button
              onClick={() => router.push(`/interviews/${interviewId}/complete`)}
              className="bg-slate-800 hover:bg-slate-700 text-white text-xs h-9 px-4 flex items-center gap-1.5 border border-slate-700"
            >
              <LogOut className="w-3.5 h-3.5" />
              <span>Leave Room</span>
            </Button>
          )}
        </div>
      </footer>

      {/* Modals */}
      <DeviceSettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        devices={deviceSettings}
        onCameraChange={async (deviceId) => {
          setDeviceSettings({ selectedCameraId: deviceId });
          if (mediaManagerRef.current) {
            await mediaManagerRef.current.switchCamera(deviceId);
          }
        }}
        onMicChange={async (deviceId) => {
          setDeviceSettings({ selectedMicId: deviceId });
          if (mediaManagerRef.current) {
            await mediaManagerRef.current.switchMicrophone(deviceId);
          }
        }}
        onSpeakerChange={(deviceId) => {
          setDeviceSettings({ selectedSpeakerId: deviceId });
        }}
      />

      <NetworkDiagnosticsModal
        isOpen={isDiagnosticsModalOpen}
        onClose={() => setIsDiagnosticsModalOpen(false)}
        diagnostics={diagnostics}
        participants={participants}
      />

      <EndInterviewModal
        isOpen={isEndModalOpen}
        onClose={() => setIsEndModalOpen(false)}
        onConfirmEnd={handleConfirmEnd}
        isSubmitting={isSubmittingAction}
      />
    </div>
  );
}
