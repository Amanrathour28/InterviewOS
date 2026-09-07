import { RealtimeClient } from '../realtime/realtime-client';
import { PeerConnectionManager } from './peer-connection-manager';
import { SignalingMessage } from './types';

export class SignalingManager {
  private realtimeClient: RealtimeClient;
  private peerManager: PeerConnectionManager;

  constructor(realtimeClient: RealtimeClient, peerManager: PeerConnectionManager) {
    this.realtimeClient = realtimeClient;
    this.peerManager = peerManager;
  }

  initialize() {
    // 1. Forward peer manager's outgoing signals to realtime gateway
    this.peerManager.setCallbacks({
      onSendSignal: (msg: SignalingMessage) => {
        this.realtimeClient.sendSignaling(msg);
      },
    });

    // 2. Listen for incoming WebRTC signals from gateway
    this.realtimeClient.onSignaling((msg: SignalingMessage) => {
      this.peerManager.handleSignalingMessage(msg);
    });
  }
}
