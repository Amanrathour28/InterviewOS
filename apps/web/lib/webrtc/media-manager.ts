export class MediaManager {
  private localStream: MediaStream | null = null;
  private screenStream: MediaStream | null = null;
  private onTrackReplaced?: (kind: 'video' | 'audio', newTrack: MediaStreamTrack | null) => void;

  setTrackReplacementCallback(callback: (kind: 'video' | 'audio', newTrack: MediaStreamTrack | null) => void) {
    this.onTrackReplaced = callback;
  }

  async startLocalStream(cameraId?: string, micId?: string): Promise<MediaStream> {
    this.stopAllTracks();

    const videoConstraints: MediaTrackConstraints = {
      width: { ideal: 1280, max: 1920 },
      height: { ideal: 720, max: 1080 },
      frameRate: { ideal: 30, max: 30 },
      facingMode: 'user',
    };
    if (cameraId) {
      videoConstraints.deviceId = { exact: cameraId };
    }

    const audioConstraints: MediaTrackConstraints = {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
    };
    if (micId) {
      audioConstraints.deviceId = { exact: micId };
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: videoConstraints,
        audio: audioConstraints,
      });

      this.localStream = stream;
      return stream;
    } catch (err: any) {
      // Fallback: If camera fails, attempt audio-only
      if (err.name === 'NotAllowedError' || err.name === 'NotFoundError') {
        try {
          const audioOnly = await navigator.mediaDevices.getUserMedia({ audio: audioConstraints });
          this.localStream = audioOnly;
          return audioOnly;
        } catch {
          throw err;
        }
      }
      throw err;
    }
  }

  setLocalStream(stream: MediaStream | null) {
    this.localStream = stream;
  }

  getLocalStream(): MediaStream | null {
    return this.localStream;
  }

  getScreenStream(): MediaStream | null {
    return this.screenStream;
  }

  getVideoTrack(): MediaStreamTrack | null {
    return this.localStream?.getVideoTracks()[0] || null;
  }

  getAudioTrack(): MediaStreamTrack | null {
    return this.localStream?.getAudioTracks()[0] || null;
  }

  toggleCamera(enabled: boolean): boolean {
    const track = this.getVideoTrack();
    if (track) {
      track.enabled = enabled;
      return track.enabled;
    }
    return false;
  }

  toggleMicrophone(enabled: boolean): boolean {
    const track = this.getAudioTrack();
    if (track) {
      track.enabled = enabled;
      return track.enabled;
    }
    return false;
  }

  async switchCamera(cameraId: string): Promise<MediaStreamTrack | null> {
    if (!this.localStream) return null;

    try {
      const newStream = await navigator.mediaDevices.getUserMedia({
        video: {
          deviceId: { exact: cameraId },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
      });

      const oldTrack = this.getVideoTrack();
      const newTrack = newStream.getVideoTracks()[0];

      if (oldTrack) {
        this.localStream.removeTrack(oldTrack);
        oldTrack.stop();
      }

      this.localStream.addTrack(newTrack);
      this.onTrackReplaced?.('video', newTrack);

      return newTrack;
    } catch (err) {
      console.warn('[MediaManager] Failed to switch camera device:', err);
      return null;
    }
  }

  async switchMicrophone(micId: string): Promise<MediaStreamTrack | null> {
    if (!this.localStream) return null;

    try {
      const newStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          deviceId: { exact: micId },
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      const oldTrack = this.getAudioTrack();
      const newTrack = newStream.getAudioTracks()[0];

      if (oldTrack) {
        this.localStream.removeTrack(oldTrack);
        oldTrack.stop();
      }

      this.localStream.addTrack(newTrack);
      this.onTrackReplaced?.('audio', newTrack);

      return newTrack;
    } catch (err) {
      console.warn('[MediaManager] Failed to switch microphone device:', err);
      return null;
    }
  }

  async startScreenShare(onEnded?: () => void): Promise<MediaStreamTrack> {
    if (this.screenStream) {
      this.stopScreenShare();
    }

    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          cursor: 'always',
          displaySurface: 'monitor',
        } as any,
        audio: false,
      });

      this.screenStream = stream;
      const screenTrack = stream.getVideoTracks()[0];

      // Handle browser-level stop button (e.g. user clicks Chrome "Stop sharing")
      screenTrack.onended = () => {
        this.stopScreenShare();
        onEnded?.();
      };

      // Replace outgoing video track with screen track on WebRTC senders
      this.onTrackReplaced?.('video', screenTrack);

      return screenTrack;
    } catch (err) {
      console.warn('[MediaManager] Screen share request cancelled or failed:', err);
      throw err;
    }
  }

  stopScreenShare(): void {
    if (this.screenStream) {
      this.screenStream.getTracks().forEach((track) => track.stop());
      this.screenStream = null;

      // Restore camera track to WebRTC senders
      const cameraTrack = this.getVideoTrack();
      this.onTrackReplaced?.('video', cameraTrack);
    }
  }

  stopAllTracks(): void {
    if (this.localStream) {
      this.localStream.getTracks().forEach((track) => track.stop());
      this.localStream = null;
    }
    if (this.screenStream) {
      this.screenStream.getTracks().forEach((track) => track.stop());
      this.screenStream = null;
    }
  }
}
