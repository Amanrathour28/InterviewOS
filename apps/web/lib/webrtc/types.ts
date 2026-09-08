export type WebRTCSignalType =
  | 'offer'
  | 'answer'
  | 'candidate'
  | 'renegotiate'
  | 'ice-restart';

export interface SignalingMessage {
  signalType: WebRTCSignalType;
  targetUserId: string;
  senderUserId: string;
  senderName?: string;
  senderRole?: string;
  sdp?: RTCSessionDescriptionInit;
  candidate?: RTCIceCandidateInit;
}

export type NetworkQuality = 'excellent' | 'good' | 'fair' | 'poor' | 'unknown';

export interface ParticipantMedia {
  userId: string;
  userName: string;
  role: string;
  stream: MediaStream | null;
  cameraEnabled: boolean;
  microphoneEnabled: boolean;
  screenSharing: boolean;
  connectionState: RTCPeerConnectionState;
  iceConnectionState: RTCIceConnectionState;
  activeSpeaker: boolean;
  audioLevel: number;
  networkQuality: NetworkQuality;
}

export interface MediaDeviceSettings {
  selectedCameraId: string;
  selectedMicId: string;
  selectedSpeakerId: string;
  availableCameras: MediaDeviceInfo[];
  availableMics: MediaDeviceInfo[];
  availableSpeakers: MediaDeviceInfo[];
}

export interface NetworkDiagnostics {
  rttMs: number;
  packetLossPercent: number;
  bytesSent: number;
  bytesReceived: number;
  frameWidth?: number;
  frameHeight?: number;
  framesPerSecond?: number;
  iceCandidateType?: string;
  connectionState: string;
}

export interface WebRTCConfiguration {
  iceServers: RTCIceServer[];
  iceTransportPolicy?: RTCIceTransportPolicy;
  sessionId: string;
  localUserId: string;
  localUserName: string;
  localUserRole: string;
}
