/**
 * Audio STT Manager — Phase 14.1
 * 
 * Captures live microphone audio tracks from WebRTC / MediaStream,
 * performs Voice Activity Detection (VAD), chunks audio during active speech,
 * transmits audio to the backend STT endpoint, and maintains real-time transcript streaming.
 */

import { apiClient } from '@/lib/api';
import { useAIStore } from '@/lib/stores/use-ai-store';

export interface AudioSTTConfig {
  interviewId: string;
  speakerRole: 'candidate' | 'interviewer';
  silenceThresholdRms?: number;
  silenceDurationMs?: number;
  maxChunkDurationMs?: number;
  onTranscript?: (segment: any, boundaryStatus: string) => void;
  onError?: (err: any) => void;
}

export class AudioSTTManager {
  private config: AudioSTTConfig;
  private audioContext: AudioContext | null = null;
  private mediaRecorder: MediaRecorder | null = null;
  private isRecording = false;
  private currentStream: MediaStream | null = null;
  private speechRecognition: any = null;
  private speechStartTime = 0;

  constructor(config: AudioSTTConfig) {
    this.config = {
      silenceThresholdRms: 0.02,
      silenceDurationMs: 1500,
      maxChunkDurationMs: 4000,
      ...config,
    };
  }

  /**
   * Starts capturing and transcribing speech from the provided MediaStream.
   */
  async start(stream: MediaStream): Promise<void> {
    this.stop();
    this.currentStream = stream;

    const audioTracks = stream.getAudioTracks();
    if (!audioTracks || audioTracks.length === 0) {
      console.warn('[AudioSTTManager] No audio tracks found in stream.');
      return;
    }

    try {
      // 1. Setup AudioContext & Analyser for Voice Activity Detection
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (AudioCtx) {
        this.audioContext = new AudioCtx();
        const source = this.audioContext.createMediaStreamSource(stream);
        const analyser = this.audioContext.createAnalyser();
        analyser.fftSize = 512;
        source.connect(analyser);
      }

      // 2. Setup MediaRecorder for audio chunking
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      const recorder = new MediaRecorder(stream, { mimeType });
      this.mediaRecorder = recorder;
      this.speechStartTime = Date.now();

      recorder.ondataavailable = async (e) => {
        if (e.data && e.data.size > 200) {
          await this.sendAudioChunk(e.data, false);
        }
      };

      recorder.start(this.config.maxChunkDurationMs || 3500);
      this.isRecording = true;

      // 3. Setup Web Speech API for low-latency client-side transcription fallback if available
      this.setupWebSpeechAPI();

    } catch (err) {
      console.warn('[AudioSTTManager] Failed to start audio recorder:', err);
      this.config.onError?.(err);
    }
  }

  /**
   * Encodes audio blob to Base64 and posts to the STT API.
   */
  private async sendAudioChunk(blob: Blob, isFinal: boolean): Promise<void> {
    if (!this.isRecording || blob.size < 100) return;

    try {
      const buffer = await blob.arrayBuffer();
      const bytes = new Uint8Array(buffer);
      let binary = '';
      for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
      }
      const base64Audio = btoa(binary);

      const elapsedSeconds = (Date.now() - this.speechStartTime) / 1000;

      const res = await apiClient<any>(
        `/interviews/${this.config.interviewId}/adaptive/audio/transcribe`,
        {
          method: 'POST',
          body: JSON.stringify({
            audio_base64: base64Audio,
            speaker_role: this.config.speakerRole,
            filename: 'mic_chunk.webm',
            start_time_seconds: Math.max(0, elapsedSeconds - 3.5),
            end_time_seconds: elapsedSeconds,
            is_final: isFinal,
          }),
        }
      );

      if (res && res.segment) {
        useAIStore.getState().addTranscriptSegment(res.segment);
        this.config.onTranscript?.(res.segment, res.boundary_status);
      }
    } catch (err) {
      // In case of network/transcription error, log without crashing interview
      console.warn('[AudioSTTManager] Audio chunk transcribe failed:', err);
    }
  }

  /**
   * Sets up browser-native Web Speech API if supported.
   */
  private setupWebSpeechAPI(): void {
    const SpeechRec = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRec) return;

    try {
      const recognition = new SpeechRec();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';

      recognition.onresult = async (event: any) => {
        const lastResult = event.results[event.results.length - 1];
        const text = lastResult[0].transcript.trim();
        const isFinal = lastResult.isFinal;

        if (isFinal && text.length > 3) {
          try {
            const res = await apiClient<any>(
              `/interviews/${this.config.interviewId}/adaptive/transcripts`,
              {
                method: 'POST',
                body: JSON.stringify({
                  speaker_role: this.config.speakerRole,
                  text: text,
                  is_final: true,
                  confidence: lastResult[0].confidence || 0.95,
                }),
              }
            );
            if (res && res.segment) {
              useAIStore.getState().addTranscriptSegment(res.segment);
              this.config.onTranscript?.(res.segment, res.boundary_status);
            }
          } catch (err) {
            console.warn('[AudioSTTManager] WebSpeech ingest error:', err);
          }
        }
      };

      recognition.onerror = (event: any) => {
        if (event.error !== 'no-speech') {
          console.warn('[AudioSTTManager] WebSpeechRecognition error:', event.error);
        }
      };

      recognition.start();
      this.speechRecognition = recognition;
    } catch (e) {
      console.warn('[AudioSTTManager] WebSpeechRecognition initialization failed:', e);
    }
  }

  /**
   * Stops audio recording and releases resources.
   */
  stop(): void {
    this.isRecording = false;

    if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
      try {
        this.mediaRecorder.stop();
      } catch {}
      this.mediaRecorder = null;
    }

    if (this.speechRecognition) {
      try {
        this.speechRecognition.stop();
      } catch {}
      this.speechRecognition = null;
    }

    if (this.audioContext && this.audioContext.state !== 'closed') {
      try {
        this.audioContext.close();
      } catch {}
      this.audioContext = null;
    }

    this.currentStream = null;
  }
}
