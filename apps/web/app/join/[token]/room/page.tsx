'use client';

/**
 * Candidate Interview Room — Phase 17.3
 *
 * Full Realtime, WebRTC, and Collaboration for Candidates:
 * - Obtains room session & candidate join token via POST /api/v1/interviews/join/{token}/room-session
 * - Connects persistent RealtimeClient (Socket.IO) for presence, events, code, whiteboard, and chat
 * - Initializes PeerConnectionManager & SignalingManager for bidirectional WebRTC video & audio
 * - Passes active realtimeClient to CodingWorkspace, WhiteboardWorkspace, and ChatPanel
 * - Dynamically renders remote interviewer video once negotiated
 * - Strictly hides interviewer-only UI (evaluations, AI copilot, private notes, hiring decision)
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
  Wifi,
  WifiOff,
} from 'lucide-react';
import { getCandidateSession, clearCandidateSession } from '@/lib/candidate-session';
import { setApiAuthToken } from '@/lib/api';
import { RealtimeClient, ConnectionState, resolveRealtimeUrl } from '@/lib/realtime/realtime-client';
import { PeerConnectionManager } from '@/lib/webrtc/peer-connection-manager';
import { SignalingManager } from '@/lib/webrtc/signaling-manager';
import { useChatStore } from '@/lib/stores/use-chat-store';
import { ChatPanel } from '@/components/interview-room/chat/chat-panel';
import { CodingWorkspace } from '@/components/interview-room/coding/coding-workspace';
import { WhiteboardWorkspace } from '@/components/interview-room/whiteboard/whiteboard-workspace';
import { VideoTile } from '@/components/interview-room/video-tile';
import { SessionHealthIndicator } from '@/components/interview-room/control-center/session-health-indicator';

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== 'undefined' ? '/api/v1' : 'http://127.0.0.1:8000/api/v1');

type CandidateTab = 'video' | 'code' | 'whiteboard' | 'chat';

interface RemotePeer {
  userId: string;
  userName: string;
  role: string;
  stream: MediaStream | null;
  connState?: RTCPeerConnectionState;
  iceState?: RTCIceConnectionState;
  cameraEnabled?: boolean;
  microphoneEnabled?: boolean;
}

export default function CandidateRoomPage() {
  const params = useParams();
  const router = useRouter();
  const token = params?.token as string;

  const [activeTab, setActiveTab] = useState<CandidateTab>('video');
  const [sessionMissing, setSessionMissing] = useState(false);
  const [interviewId, setInterviewId] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [candidateUserId, setCandidateUserId] = useState<string>('');
  const [candidateName, setCandidateName] = useState('');
  const [isMicEnabled, setIsMicEnabled] = useState(true);
  const [isCameraEnabled, setIsCameraEnabled] = useState(true);
  const [localStream, setLocalStream] = useState<MediaStream | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [connectionState, setConnectionState] = useState<ConnectionState>('connecting');
  const [remotePeers, setRemotePeers] = useState<Record<string, RemotePeer>>({});
  const [currentStage, setCurrentStage] = useState<string>('introduction');
  const [isInterviewEnded, setIsInterviewEnded] = useState(false);

  const [localMediaError, setLocalMediaError] = useState<string | null>(null);

  // References for cleanup and signaling
  const streamRef = useRef<MediaStream | null>(null);
  const realtimeClientRef = useRef<RealtimeClient | null>(null);
  const peerManagerRef = useRef<PeerConnectionManager | null>(null);
  const signalingManagerRef = useRef<SignalingManager | null>(null);
  const [, setRerender] = useState(0);

  // 1. Validate candidate session from localStorage/sessionStorage
  useEffect(() => {
    if (!token) return;
    const session = getCandidateSession(token);
    if (!session) {
      setSessionMissing(true);
      setIsLoading(false);
      return;
    }
    setInterviewId(session.interviewId);
    setCandidateName(session.candidateName);
  }, [token]);

  // 2. Independent local media lifecycle: candidate camera preview never depends on room session or socket
  useEffect(() => {
    let isMounted = true;
    console.log('[Media] requesting camera/microphone for CandidateRoom');

    if (!navigator.mediaDevices?.getUserMedia) {
      console.warn('[Media] navigator.mediaDevices.getUserMedia not supported');
      setLocalMediaError('Media devices not supported');
      return;
    }

    navigator.mediaDevices
      .getUserMedia({
        video: {
          width: { ideal: 1280, max: 1920 },
          height: { ideal: 720, max: 1080 },
          frameRate: { ideal: 30, max: 30 },
          facingMode: 'user',
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      .then((stream) => {
        if (!isMounted) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        console.log('[Media] getUserMedia success for CandidateRoom');
        const vTracks = stream.getVideoTracks();
        const aTracks = stream.getAudioTracks();
        console.log(`[Media] video tracks count: ${vTracks.length}, audio tracks count: ${aTracks.length}`);
        if (vTracks.length > 0) {
          console.log(`[Media] video track readyState: ${vTracks[0].readyState}, enabled: ${vTracks[0].enabled}`);
        }

        streamRef.current = stream;
        setLocalStream(stream);
        setLocalMediaError(null);

        if (peerManagerRef.current) {
          peerManagerRef.current.setLocalStream(stream);
        }
      })
      .catch((err: any) => {
        console.warn('[Media] Candidate media error:', err);
        if (!isMounted) return;
        if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
          setLocalMediaError('Camera permission denied');
        } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
          setLocalMediaError('No camera detected');
        } else {
          setLocalMediaError('Camera unavailable');
        }
      });

    return () => {
      isMounted = false;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // 3. Establish candidate room session, WebRTC, and Realtime Socket.IO
  useEffect(() => {
    if (!interviewId || !token) return;
    const session = getCandidateSession(token);
    if (!session) return;

    let isSubscribed = true;

    (async () => {
      try {
        setIsLoading(true);

        // Fetch candidate-scoped room session & join token
        const res = await fetch(`${API_BASE}/interviews/join/${token}/room-session`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.candidateSessionToken}`,
            'Content-Type': 'application/json',
          },
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Failed to join room session (HTTP ${res.status})`);
        }

        const roomData = await res.json();
        if (!isSubscribed) return;

        const sessId = String(roomData.session_id);
        const candId = String(roomData.user_id || `candidate-${token}`);
        const candDisplayName = roomData.user_name || session.candidateName || 'Candidate';

        setSessionId(sessId);
        setCandidateUserId(candId);
        setCandidateName(candDisplayName);

        // Set auth token for apiClient requests (coding, whiteboard, chat)
        if (roomData.candidate_join_token) {
          setApiAuthToken(roomData.candidate_join_token);
        }

        // Initialize WebRTC PeerConnectionManager
        const peerManager = new PeerConnectionManager({
          iceServers: roomData.ice_servers || [{ urls: 'stun:stun.l.google.com:19302' }],
          sessionId: sessId,
          localUserId: candId,
          localUserName: candDisplayName,
          localUserRole: 'candidate',
        });
        peerManagerRef.current = peerManager;

        if (streamRef.current) {
          peerManager.setLocalStream(streamRef.current);
        }

        // Determine correct realtime URL
        const realtimeUrl = resolveRealtimeUrl(roomData.realtime_url);

        // Initialize RealtimeClient
        const realtimeClient = new RealtimeClient({
          url: realtimeUrl,
          token: roomData.candidate_join_token,
          onConnectionChange: (state: ConnectionState) => {
            if (isSubscribed) {
              setConnectionState(state);
            }
          },
          onSync: (syncData: any) => {
            if (!isSubscribed) return;
            if (syncData.participants && Array.isArray(syncData.participants)) {
              syncData.participants.forEach((p: any) => {
                if (p.userId !== candId && p.online) {
                  peerManager.getOrCreatePeer(p.userId, p.userName, p.role);
                  setRemotePeers((prev) => ({
                    ...prev,
                    [p.userId]: {
                      userId: p.userId,
                      userName: p.userName || 'Interviewer',
                      role: p.role || 'interviewer',
                      stream: prev[p.userId]?.stream || null,
                      cameraEnabled: p.deviceState?.camera !== false,
                      microphoneEnabled: p.deviceState?.microphone !== false,
                    },
                  }));
                }
              });
            }
          },
          onEvent: (event: any) => {
            if (!isSubscribed) return;

            if (event.event_type === 'PARTICIPANT_JOINED') {
              const p = event.payload;
              if (p.user_id && p.user_id !== candId) {
                peerManager.getOrCreatePeer(p.user_id, p.user_name || 'Interviewer', p.role || 'interviewer');
                setRemotePeers((prev) => ({
                  ...prev,
                  [p.user_id]: {
                    userId: p.user_id,
                    userName: p.user_name || 'Interviewer',
                    role: p.role || 'interviewer',
                    stream: prev[p.user_id]?.stream || null,
                  },
                }));
              }
            } else if (event.event_type === 'PARTICIPANT_LEFT') {
              const leftUserId = event.payload?.user_id;
              if (leftUserId) {
                peerManager.removePeer(leftUserId);
                setRemotePeers((prev) => {
                  const updated = { ...prev };
                  delete updated[leftUserId];
                  return updated;
                });
              }
            } else if (event.event_type === 'PARTICIPANT_STATUS_CHANGED') {
              const pUserId = event.payload?.user_id;
              const dState = event.payload?.deviceState;
              if (pUserId && dState) {
                setRemotePeers((prev) => {
                  if (!prev[pUserId]) return prev;
                  return {
                    ...prev,
                    [pUserId]: {
                      ...prev[pUserId],
                      cameraEnabled: dState.camera !== false,
                      microphoneEnabled: dState.microphone !== false,
                    },
                  };
                });
              }
            } else if (event.event_type === 'STAGE_CHANGED') {
              const newStage = event.payload?.new_stage || event.payload?.stage;
              if (newStage) {
                setCurrentStage(newStage);
              }
            } else if (event.event_type === 'INTERVIEW_ENDED') {
              setIsInterviewEnded(true);
            } else if (event.event_type === 'CHAT_MESSAGE_CREATED') {
              const channelId = event.payload?.channel_id;
              if (channelId && event.payload?.message) {
                useChatStore.getState().addMessage(channelId, event.payload.message);
              }
            }
          },
          onError: (err: any) => {
            console.warn('[Candidate Realtime Error]:', err);
          },
        });
        realtimeClientRef.current = realtimeClient;

        // Initialize WebRTC Signaling Manager
        const signalingManager = new SignalingManager(realtimeClient, peerManager);
        signalingManagerRef.current = signalingManager;
        signalingManager.initialize();

        // Wire PeerConnectionManager Callbacks
        peerManager.setCallbacks({
          onSendSignal: (msg) => {
            realtimeClient.sendSignaling(msg);
          },
          onRemoteStreamAdded: (userId, rStream) => {
            if (!isSubscribed) return;
            setRemotePeers((prev) => ({
              ...prev,
              [userId]: {
                ...(prev[userId] || { userId, userName: 'Interviewer', role: 'interviewer' }),
                stream: rStream,
              },
            }));
          },
          onPeerConnectionChanged: (userId, connState, iceState) => {
            if (!isSubscribed) return;
            setRemotePeers((prev) => {
              if (!prev[userId]) return prev;
              return {
                ...prev,
                [userId]: {
                  ...prev[userId],
                  connState,
                  iceState,
                },
              };
            });
          },
          onActiveSpeakerChanged: () => {},
          onDiagnosticsUpdated: () => {},
        });

        // Connect Candidate Realtime Socket
        realtimeClient.connect();

        // Broadcast candidate ready status to interviewer
        realtimeClient.emit('candidate_ready', { candidate_name: candDisplayName });

        // Trigger component re-render so child workspaces get realtimeClientRef.current
        setRerender((v) => v + 1);
      } catch (err: any) {
        console.error('[CandidateRoom Init Error]:', err);
        if (isSubscribed) {
          setErrorMessage(err.message || 'Failed to initialize interview room');
        }
      } finally {
        if (isSubscribed) {
          setIsLoading(false);
        }
      }
    })();

    return () => {
      isSubscribed = false;
      peerManagerRef.current?.closeAll();
      realtimeClientRef.current?.disconnect();
      setApiAuthToken(null);
    };
  }, [interviewId, token]);

  // Toggle Microphone
  const toggleMic = () => {
    const tracks = streamRef.current?.getAudioTracks() || [];
    const newState = !isMicEnabled;
    tracks.forEach((t) => {
      t.enabled = newState;
    });
    setIsMicEnabled(newState);
    realtimeClientRef.current?.sendMediaState({
      microphone: newState,
      camera: isCameraEnabled,
    });
  };

  // Toggle Camera
  const toggleCamera = () => {
    const tracks = streamRef.current?.getVideoTracks() || [];
    const newState = !isCameraEnabled;
    tracks.forEach((t) => {
      t.enabled = newState;
    });
    setIsCameraEnabled(newState);
    realtimeClientRef.current?.sendMediaState({
      camera: newState,
      microphone: isMicEnabled,
    });
  };

  // Leave room
  const handleLeave = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    peerManagerRef.current?.closeAll();
    realtimeClientRef.current?.disconnect();
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
            className="text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
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
          <p className="text-xs text-zinc-400 font-medium">Connecting to interview room & media…</p>
        </div>
      </div>
    );
  }

  if (errorMessage) {
    return (
      <div className="min-h-screen bg-[#07080c] text-white flex items-center justify-center p-4">
        <div className="max-w-md w-full rounded-2xl border border-rose-900/40 bg-[#0d0e14] p-8 text-center space-y-4">
          <AlertCircle className="h-10 w-10 text-rose-400 mx-auto" />
          <h1 className="text-lg font-bold text-rose-200">Unable to Join Interview</h1>
          <p className="text-sm text-zinc-400">{errorMessage}</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-semibold text-white transition-colors"
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const remotePeerList = Object.values(remotePeers);

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
          <span className="text-xs text-indigo-400 font-mono hidden sm:inline truncate capitalize">
            {currentStage.replace('_', ' ')}
          </span>
        </div>

        {/* Realtime Connection Status & Diagnostics */}
        <div className="flex items-center gap-2">
          <SessionHealthIndicator
            connectionState={connectionState}
            activeParticipantsCount={remotePeerList.length + 1}
            webrtcState={remotePeerList[0]?.connState}
            remoteVideoReceived={remotePeerList.some((p) => Boolean(p.stream))}
          />

          {candidateName && (
            <div className="min-w-0 max-w-[120px] sm:max-w-[180px] text-center hidden md:block">
              <span className="text-xs text-zinc-300 font-medium truncate block">{candidateName}</span>
            </div>
          )}
        </div>

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
                userId={candidateUserId || `candidate-${token}`}
                userName={candidateName || 'You (Candidate)'}
                role="candidate"
                stream={localStream}
                isLocal
                cameraEnabled={isCameraEnabled}
                microphoneEnabled={isMicEnabled}
                mediaError={localMediaError}
              />

              {/* Remote (interviewer) video or waiting state */}
              {remotePeerList.length > 0 ? (
                remotePeerList.map((peer) => (
                  <VideoTile
                    key={peer.userId}
                    userId={peer.userId}
                    userName={peer.userName || 'Interviewer'}
                    role={peer.role || 'interviewer'}
                    stream={peer.stream}
                    isLocal={false}
                    cameraEnabled={peer.cameraEnabled ?? true}
                    microphoneEnabled={peer.microphoneEnabled ?? true}
                    connectionState={peer.connState}
                  />
                ))
              ) : (
                <div className="aspect-video w-full h-full min-h-[160px] sm:min-h-[200px] rounded-2xl border border-zinc-800 bg-zinc-900/70 backdrop-blur-sm flex items-center justify-center">
                  <div className="text-center space-y-2.5 p-4">
                    <div className="h-10 w-10 rounded-full bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center mx-auto">
                      <Video className="h-5 w-5 text-indigo-400 animate-pulse" />
                    </div>
                    <p className="text-xs text-zinc-200 font-semibold">Interviewer</p>
                    <p className="text-[11px] text-zinc-500 max-w-[220px] leading-relaxed">
                      Live video stream connects automatically when the interviewer joins.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'code' && interviewId && sessionId && (
          <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
            <CodingWorkspace
              sessionId={sessionId}
              interviewId={interviewId}
              isInterviewer={false}
              realtimeClient={realtimeClientRef.current}
            />
          </div>
        )}

        {activeTab === 'whiteboard' && interviewId && sessionId && (
          <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
            <WhiteboardWorkspace
              sessionId={sessionId}
              interviewId={interviewId}
              isInterviewer={false}
              realtimeClient={realtimeClientRef.current}
            />
          </div>
        )}

        {activeTab === 'chat' && interviewId && sessionId && (
          <div className="flex-1 min-h-0 min-w-0 overflow-hidden">
            <ChatPanel
              sessionId={sessionId}
              currentUserId={candidateUserId || `candidate-${token}`}
              isInterviewer={false}
              realtimeClient={realtimeClientRef.current}
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
