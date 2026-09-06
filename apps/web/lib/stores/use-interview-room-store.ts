import { create } from 'zustand';
import { MediaDeviceSettings, NetworkDiagnostics, ParticipantMedia } from '../webrtc/types';

export type WorkspaceTab = 'video' | 'code' | 'whiteboard' | 'chat' | 'notes' | 'ai';
export type ConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export interface Participant {
  userId: string;
  userName: string;
  role: string;
  online: boolean;
  connectionCount: number;
  lastSeenAt: string;
  deviceState?: {
    camera?: boolean;
    microphone?: boolean;
    screenShare?: boolean;
  };
}

interface InterviewRoomState {
  session: any | null;
  participants: Participant[];
  connectionState: ConnectionStatus;
  activeTab: WorkspaceTab;
  currentStage: string;
  elapsedSeconds: number;
  isInterviewer: boolean;
  events: any[];
  privateNotes: string;

  // WebRTC & Media State (Phase 6)
  isPreJoinDone: boolean;
  localStream: MediaStream | null;
  isCameraEnabled: boolean;
  isMicEnabled: boolean;
  isScreenSharing: boolean;
  activeSpeakerId: string | null;
  remoteStreams: Record<string, ParticipantMedia>;
  deviceSettings: MediaDeviceSettings;
  diagnostics: Record<string, NetworkDiagnostics>;
  isSettingsModalOpen: boolean;
  isDiagnosticsModalOpen: boolean;

  // Actions
  setSession: (session: any) => void;
  setParticipants: (participants: Participant[]) => void;
  updateParticipantPresence: (userId: string, online: boolean, role?: string, userName?: string, deviceState?: any) => void;
  setConnectionState: (status: ConnectionStatus) => void;
  setActiveTab: (tab: WorkspaceTab) => void;
  setCurrentStage: (stage: string) => void;
  setElapsedSeconds: (seconds: number) => void;
  addEvent: (event: any) => void;
  setPrivateNotes: (notes: string) => void;

  // Media Actions
  setIsPreJoinDone: (done: boolean) => void;
  setLocalStream: (stream: MediaStream | null) => void;
  setIsCameraEnabled: (enabled: boolean) => void;
  setIsMicEnabled: (enabled: boolean) => void;
  setIsScreenSharing: (sharing: boolean) => void;
  setActiveSpeakerId: (id: string | null) => void;
  setRemoteStream: (userId: string, media: Partial<ParticipantMedia>) => void;
  removeRemoteStream: (userId: string) => void;
  setDeviceSettings: (settings: Partial<MediaDeviceSettings>) => void;
  setDiagnostics: (userId: string, diag: NetworkDiagnostics) => void;
  setIsSettingsModalOpen: (open: boolean) => void;
  setIsDiagnosticsModalOpen: (open: boolean) => void;
  reset: () => void;
}

export const useInterviewRoomStore = create<InterviewRoomState>((set) => ({
  session: null,
  participants: [],
  connectionState: 'connecting',
  activeTab: 'video',
  currentStage: 'introduction',
  elapsedSeconds: 0,
  isInterviewer: false,
  events: [],
  privateNotes: '',

  // WebRTC default state
  isPreJoinDone: false,
  localStream: null,
  isCameraEnabled: true,
  isMicEnabled: true,
  isScreenSharing: false,
  activeSpeakerId: null,
  remoteStreams: {},
  deviceSettings: {
    selectedCameraId: '',
    selectedMicId: '',
    selectedSpeakerId: '',
    availableCameras: [],
    availableMics: [],
    availableSpeakers: [],
  },
  diagnostics: {},
  isSettingsModalOpen: false,
  isDiagnosticsModalOpen: false,

  setSession: (session) =>
    set({
      session,
      currentStage: session?.current_stage || 'introduction',
      isInterviewer: Boolean(session?.is_interviewer),
    }),

  setParticipants: (participants) => set({ participants }),

  updateParticipantPresence: (userId, online, role, userName, deviceState) =>
    set((state) => {
      const idx = state.participants.findIndex((p) => p.userId === userId);
      if (idx >= 0) {
        const updated = [...state.participants];
        updated[idx] = {
          ...updated[idx],
          online,
          lastSeenAt: new Date().toISOString(),
          deviceState: deviceState ? { ...updated[idx].deviceState, ...deviceState } : updated[idx].deviceState,
        };
        return { participants: updated };
      }
      return {
        participants: [
          ...state.participants,
          {
            userId,
            userName: userName || 'Participant',
            role: role || 'participant',
            online,
            connectionCount: 1,
            lastSeenAt: new Date().toISOString(),
            deviceState: deviceState || { camera: true, microphone: true, screenShare: false },
          },
        ],
      };
    }),

  setConnectionState: (connectionState) => set({ connectionState }),
  setActiveTab: (activeTab) => set({ activeTab }),
  setCurrentStage: (currentStage) => set({ currentStage }),
  setElapsedSeconds: (elapsedSeconds) => set({ elapsedSeconds }),
  addEvent: (event) => set((state) => ({ events: [event, ...state.events].slice(0, 100) })),
  setPrivateNotes: (privateNotes) => set({ privateNotes }),

  setIsPreJoinDone: (isPreJoinDone) => set({ isPreJoinDone }),
  setLocalStream: (localStream) => set({ localStream }),
  setIsCameraEnabled: (isCameraEnabled) => set({ isCameraEnabled }),
  setIsMicEnabled: (isMicEnabled) => set({ isMicEnabled }),
  setIsScreenSharing: (isScreenSharing) => set({ isScreenSharing }),
  setActiveSpeakerId: (activeSpeakerId) => set({ activeSpeakerId }),

  setRemoteStream: (userId, media) =>
    set((state) => ({
      remoteStreams: {
        ...state.remoteStreams,
        [userId]: {
          ...(state.remoteStreams[userId] || {
            userId,
            userName: 'Participant',
            role: 'participant',
            stream: null,
            cameraEnabled: true,
            microphoneEnabled: true,
            screenSharing: false,
            connectionState: 'new',
            iceConnectionState: 'new',
            activeSpeaker: false,
            audioLevel: 0,
            networkQuality: 'unknown',
          }),
          ...media,
        },
      },
    })),

  removeRemoteStream: (userId) =>
    set((state) => {
      const copy = { ...state.remoteStreams };
      delete copy[userId];
      return { remoteStreams: copy };
    }),

  setDeviceSettings: (settings) =>
    set((state) => ({
      deviceSettings: { ...state.deviceSettings, ...settings },
    })),

  setDiagnostics: (userId, diag) =>
    set((state) => ({
      diagnostics: { ...state.diagnostics, [userId]: diag },
    })),

  setIsSettingsModalOpen: (isSettingsModalOpen) => set({ isSettingsModalOpen }),
  setIsDiagnosticsModalOpen: (isDiagnosticsModalOpen) => set({ isDiagnosticsModalOpen }),

  reset: () =>
    set({
      session: null,
      participants: [],
      connectionState: 'connecting',
      activeTab: 'video',
      currentStage: 'introduction',
      elapsedSeconds: 0,
      isInterviewer: false,
      events: [],
      privateNotes: '',
      isPreJoinDone: false,
      localStream: null,
      isCameraEnabled: true,
      isMicEnabled: true,
      isScreenSharing: false,
      activeSpeakerId: null,
      remoteStreams: {},
      diagnostics: {},
      isSettingsModalOpen: false,
      isDiagnosticsModalOpen: false,
    }),
}));
