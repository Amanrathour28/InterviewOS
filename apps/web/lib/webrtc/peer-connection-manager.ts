import {
  NetworkDiagnostics,
  NetworkQuality,
  SignalingMessage,
  WebRTCConfiguration,
} from './types';

interface PeerEntry {
  userId: string;
  userName: string;
  role: string;
  pc: RTCPeerConnection;
  isPolite: boolean;
  makingOffer: boolean;
  ignoreOffer: boolean;
  isSettingRemoteAnswerPending: boolean;
  remoteStream: MediaStream;
  candidateBuffer: RTCIceCandidateInit[];
  audioAnalyser?: {
    context: AudioContext;
    analyser: AnalyserNode;
    source: MediaStreamAudioSourceNode;
  };
}

export class PeerConnectionManager {
  private config: WebRTCConfiguration;
  private peers = new Map<string, PeerEntry>();
  private localStream: MediaStream | null = null;
  private statsInterval: NodeJS.Timeout | null = null;
  private audioInterval: NodeJS.Timeout | null = null;

  // Callbacks
  private onSendSignal?: (msg: SignalingMessage) => void;
  private onRemoteStreamAdded?: (userId: string, stream: MediaStream) => void;
  private onPeerConnectionChanged?: (
    userId: string,
    state: RTCPeerConnectionState,
    iceState: RTCIceConnectionState
  ) => void;
  private onActiveSpeakerChanged?: (userId: string, level: number, isActive: boolean) => void;
  private onDiagnosticsUpdated?: (userId: string, diagnostics: NetworkDiagnostics) => void;

  constructor(config: WebRTCConfiguration) {
    this.config = config;
  }

  setCallbacks(callbacks: Partial<{
    onSendSignal: (msg: SignalingMessage) => void;
    onRemoteStreamAdded: (userId: string, stream: MediaStream) => void;
    onPeerConnectionChanged: (
      userId: string,
      state: RTCPeerConnectionState,
      iceState: RTCIceConnectionState
    ) => void;
    onActiveSpeakerChanged: (userId: string, level: number, isActive: boolean) => void;
    onDiagnosticsUpdated: (userId: string, diagnostics: NetworkDiagnostics) => void;
  }>) {
    if (callbacks.onSendSignal !== undefined) this.onSendSignal = callbacks.onSendSignal;
    if (callbacks.onRemoteStreamAdded !== undefined) this.onRemoteStreamAdded = callbacks.onRemoteStreamAdded;
    if (callbacks.onPeerConnectionChanged !== undefined) this.onPeerConnectionChanged = callbacks.onPeerConnectionChanged;
    if (callbacks.onActiveSpeakerChanged !== undefined) this.onActiveSpeakerChanged = callbacks.onActiveSpeakerChanged;
    if (callbacks.onDiagnosticsUpdated !== undefined) this.onDiagnosticsUpdated = callbacks.onDiagnosticsUpdated;
  }

  setLocalStream(stream: MediaStream | null) {
    this.localStream = stream;

    // Attach local tracks to all existing peer connections
    if (stream) {
      for (const peer of Array.from(this.peers.values())) {
        const senders = peer.pc.getSenders();
        stream.getTracks().forEach((track) => {
          const sender = senders.find((s) => s.track?.kind === track.kind);
          if (sender) {
            sender.replaceTrack(track).catch((err) =>
              console.warn('[PeerConnectionManager] Track replace error:', err)
            );
          } else {
            peer.pc.addTrack(track, stream);
          }
        });
      }
    }
  }

  replaceTrack(kind: 'video' | 'audio', newTrack: MediaStreamTrack | null) {
    for (const peer of Array.from(this.peers.values())) {
      const sender = peer.pc.getSenders().find((s) => s.track?.kind === kind);
      if (sender) {
        sender.replaceTrack(newTrack).catch((err) =>
          console.warn('[PeerConnectionManager] Track replace error:', err)
        );
      }
    }
  }

  getOrCreatePeer(userId: string, userName: string, role: string): PeerEntry {
    let peer = this.peers.get(userId);
    if (peer) return peer;

    // Deterministic Perfect Negotiation rule:
    // If local user ID > remote user ID, local peer is polite
    const isPolite = this.config.localUserId > userId;

    const pc = new RTCPeerConnection({
      iceServers: this.config.iceServers || [
        { urls: 'stun:stun.l.google.com:19302' },
      ],
      iceTransportPolicy: this.config.iceTransportPolicy || 'all',
      bundlePolicy: 'max-bundle',
    });

    const remoteStream = new MediaStream();

    peer = {
      userId,
      userName,
      role,
      pc,
      isPolite,
      makingOffer: false,
      ignoreOffer: false,
      isSettingRemoteAnswerPending: false,
      remoteStream,
      candidateBuffer: [],
    };

    this.peers.set(userId, peer);
    this.setupPeerHandlers(peer);

    // Add local tracks to new peer connection
    if (this.localStream) {
      this.localStream.getTracks().forEach((track) => {
        pc.addTrack(track, this.localStream!);
      });
    }

    this.startMonitoring();
    return peer;
  }

  private setupPeerHandlers(peer: PeerEntry) {
    const { pc, userId } = peer;

    // 1. Negotiation needed (Perfect Negotiation pattern)
    pc.onnegotiationneeded = async () => {
      try {
        if (pc.signalingState !== 'stable') return;
        const offer = await pc.createOffer();
        if (pc.signalingState !== 'stable') return;
        await pc.setLocalDescription(offer);

        this.onSendSignal?.({
          signalType: 'offer',
          targetUserId: userId,
          senderUserId: this.config.localUserId,
          senderName: this.config.localUserName,
          senderRole: this.config.localUserRole,
          sdp: pc.localDescription ? { type: pc.localDescription.type, sdp: pc.localDescription.sdp } : offer,
        });
      } catch (err) {
        console.warn(`[WebRTC Peer ${userId}] Negotiation offer error:`, err);
      } finally {
        peer.makingOffer = false;
      }
    };

    // 2. ICE candidate generation
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        console.log(`[WebRTC Peer ${userId}] ICE candidate generated: type=${event.candidate.type}, protocol=${event.candidate.protocol}`);
        this.onSendSignal?.({
          signalType: 'candidate',
          targetUserId: userId,
          senderUserId: this.config.localUserId,
          candidate: event.candidate.toJSON(),
        });
      }
    };

    // 3. Track received from remote peer
    pc.ontrack = (event) => {
      console.log(`[WebRTC Peer ${userId}] Remote track received: kind=${event.track.kind}, id=${event.track.id}, readyState=${event.track.readyState}`);
      if (event.streams && event.streams[0]) {
        event.streams[0].getTracks().forEach((track) => {
          if (!peer.remoteStream.getTracks().some((t) => t.id === track.id)) {
            peer.remoteStream.addTrack(track);
          }
        });
      }
      if (event.track && !peer.remoteStream.getTracks().some((t) => t.id === event.track.id)) {
        peer.remoteStream.addTrack(event.track);
      }

      this.setupAudioAnalysis(peer);
      this.onRemoteStreamAdded?.(userId, peer.remoteStream);
    };

    // 4. Connection State change
    pc.onconnectionstatechange = () => {
      console.log(`[WebRTC Peer ${userId}] pc.connectionState changed to: ${pc.connectionState}`);
      this.onPeerConnectionChanged?.(userId, pc.connectionState, pc.iceConnectionState);
      if (pc.connectionState === 'failed') {
        this.restartIce(userId);
      }
    };

    // 5. ICE Connection State change
    pc.oniceconnectionstatechange = () => {
      console.log(`[WebRTC Peer ${userId}] pc.iceConnectionState changed to: ${pc.iceConnectionState}`);
      this.onPeerConnectionChanged?.(userId, pc.connectionState, pc.iceConnectionState);
      if (pc.iceConnectionState === 'failed') {
        this.restartIce(userId);
      }
    };
  }

  async handleSignalingMessage(msg: SignalingMessage) {
    const peer = this.getOrCreatePeer(msg.senderUserId, msg.senderName || 'Peer', msg.senderRole || 'participant');
    const { pc } = peer;

    try {
      if (msg.signalType === 'offer' && msg.sdp) {
        const offerCollision =
          peer.makingOffer || pc.signalingState !== 'stable';

        peer.ignoreOffer = !peer.isPolite && offerCollision;
        if (peer.ignoreOffer) {
          console.warn(`[WebRTC Peer ${peer.userId}] Glare detected, ignoring offer (impolite peer)`);
          return;
        }

        if (offerCollision) {
          try {
            console.log(`[WebRTC Peer ${peer.userId}] Polite peer rolling back local offer due to glare`);
            await pc.setLocalDescription({ type: 'rollback' });
          } catch (rollbackErr) {
            console.warn(`[WebRTC Peer ${peer.userId}] Rollback error:`, rollbackErr);
          }
        }

        peer.isSettingRemoteAnswerPending = false;
        await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));

        // Flush buffered ICE candidates
        await this.flushCandidateBuffer(peer);

        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);

        this.onSendSignal?.({
          targetUserId: peer.userId,
          signalType: 'answer',
          senderUserId: this.config.localUserId,
          senderName: this.config.localUserName,
          senderRole: this.config.localUserRole,
          sdp: pc.localDescription ? { type: pc.localDescription.type, sdp: pc.localDescription.sdp } : answer,
        });
        await this.flushCandidateBuffer(peer);
      } else if (msg.signalType === 'answer' && msg.sdp) {
        if (pc.signalingState !== 'have-local-offer') {
          console.warn(`[WebRTC Peer ${peer.userId}] Ignoring answer in unexpected state: ${pc.signalingState}`);
          return;
        }
        peer.isSettingRemoteAnswerPending = false;
        await pc.setRemoteDescription(new RTCSessionDescription(msg.sdp));
        await this.flushCandidateBuffer(peer);
      } else if (msg.signalType === 'candidate' && msg.candidate) {
        if (pc.remoteDescription && pc.remoteDescription.type) {
          await pc.addIceCandidate(new RTCIceCandidate(msg.candidate));
        } else {
          peer.candidateBuffer.push(msg.candidate);
        }
      } else if (msg.signalType === 'ice-restart') {
        this.restartIce(peer.userId);
      }
    } catch (err) {
      console.warn(`[WebRTC Peer ${peer.userId}] Error processing signal ${msg.signalType}:`, err);
    }
  }

  private async flushCandidateBuffer(peer: PeerEntry) {
    while (peer.candidateBuffer.length > 0) {
      const candidate = peer.candidateBuffer.shift();
      if (candidate) {
        try {
          await peer.pc.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (err) {
          console.warn('[WebRTC] Buffered candidate add error:', err);
        }
      }
    }
  }

  async restartIce(userId: string) {
    const peer = this.peers.get(userId);
    if (!peer) return;

    try {
      const offer = await peer.pc.createOffer({ iceRestart: true });
      await peer.pc.setLocalDescription(offer);

      this.onSendSignal?.({
        signalType: 'offer',
        targetUserId: userId,
        senderUserId: this.config.localUserId,
        sdp: peer.pc.localDescription || undefined,
      });
    } catch (err) {
      console.warn(`[WebRTC Peer ${userId}] ICE restart failed:`, err);
    }
  }

  private setupAudioAnalysis(peer: PeerEntry) {
    if (peer.audioAnalyser || typeof window === 'undefined') return;

    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;

      const audioTrack = peer.remoteStream.getAudioTracks()[0];
      if (!audioTrack) return;

      const context = new AudioCtx();
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.5;

      const source = context.createMediaStreamSource(new MediaStream([audioTrack]));
      source.connect(analyser);

      peer.audioAnalyser = { context, analyser, source };
    } catch (err) {
      console.warn('[WebRTC] Audio analysis setup skipped:', err);
    }
  }

  private startMonitoring() {
    if (!this.statsInterval) {
      this.statsInterval = setInterval(() => this.collectStats(), 2000);
    }
    if (!this.audioInterval) {
      this.audioInterval = setInterval(() => this.analyzeAudioLevels(), 200);
    }
  }

  private async collectStats() {
    for (const peer of Array.from(this.peers.values())) {
      if (peer.pc.connectionState !== 'connected') continue;

      try {
        const stats = await peer.pc.getStats();
        let rttMs = 0;
        let packetLossPercent = 0;
        let bytesSent = 0;
        let bytesReceived = 0;
        let frameWidth: number | undefined;
        let frameHeight: number | undefined;
        let framesPerSecond: number | undefined;
        let candidateType = 'unknown';

        stats.forEach((report) => {
          if (report.type === 'candidate-pair' && report.state === 'succeeded') {
            rttMs = report.currentRoundTripTime ? Math.round(report.currentRoundTripTime * 1000) : 0;
          }
          if (report.type === 'inbound-rtp' && report.kind === 'video') {
            bytesReceived = report.bytesReceived || 0;
            frameWidth = report.frameWidth;
            frameHeight = report.frameHeight;
            framesPerSecond = report.framesPerSecond;

            const totalPackets = (report.packetsReceived || 0) + (report.packetsLost || 0);
            if (totalPackets > 0) {
              packetLossPercent = Math.round(((report.packetsLost || 0) / totalPackets) * 100);
            }
          }
          if (report.type === 'outbound-rtp') {
            bytesSent += report.bytesSent || 0;
          }
          if (report.type === 'remote-candidate') {
            candidateType = report.candidateType || candidateType;
          }
        });

        const diagnostics: NetworkDiagnostics = {
          rttMs,
          packetLossPercent,
          bytesSent,
          bytesReceived,
          frameWidth,
          frameHeight,
          framesPerSecond,
          iceCandidateType: candidateType,
          connectionState: peer.pc.connectionState,
        };

        this.onDiagnosticsUpdated?.(peer.userId, diagnostics);
      } catch {
        // Peer stats unavailable
      }
    }
  }

  private analyzeAudioLevels() {
    const dataArray = new Uint8Array(128);

    for (const peer of Array.from(this.peers.values())) {
      if (!peer.audioAnalyser) continue;

      peer.audioAnalyser.analyser.getByteFrequencyData(dataArray);
      let sum = 0;
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i];
      }
      const average = sum / dataArray.length;
      const normalizedLevel = Math.min(1, average / 100);
      const isActive = normalizedLevel > 0.15;

      this.onActiveSpeakerChanged?.(peer.userId, normalizedLevel, isActive);
    }
  }

  removePeer(userId: string) {
    const peer = this.peers.get(userId);
    if (peer) {
      peer.audioAnalyser?.context.close().catch(() => {});
      peer.pc.close();
      this.peers.delete(userId);
    }
  }

  closeAll() {
    if (this.statsInterval) {
      clearInterval(this.statsInterval);
      this.statsInterval = null;
    }
    if (this.audioInterval) {
      clearInterval(this.audioInterval);
      this.audioInterval = null;
    }

    for (const peer of Array.from(this.peers.values())) {
      peer.audioAnalyser?.context.close().catch(() => {});
      peer.pc.close();
    }
    this.peers.clear();
  }
}
