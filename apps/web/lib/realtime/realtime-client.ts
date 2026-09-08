import { io, Socket } from 'socket.io-client';

export type ConnectionState = 'connecting' | 'connected' | 'reconnecting' | 'disconnected';

export interface RealtimeClientOptions {
  url: string;
  token: string;
  onSync?: (data: any) => void;
  onEvent?: (event: any) => void;
  onConnectionChange?: (state: ConnectionState) => void;
  onError?: (err: any) => void;
}

export function resolveRealtimeUrl(serverUrl?: string): string {
  // 1. Explicit env variable overrides
  if (process.env.NEXT_PUBLIC_REALTIME_URL) {
    return process.env.NEXT_PUBLIC_REALTIME_URL;
  }
  // 2. If provided by backend join-token or room-session response
  if (serverUrl && serverUrl.trim()) {
    const isLocalhost = serverUrl.includes('localhost') || serverUrl.includes('127.0.0.1');
    const isProdBrowser =
      typeof window !== 'undefined' &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1';
    if (!isProdBrowser || !isLocalhost) {
      return serverUrl;
    }
  }
  // 3. Localhost fallback allowed strictly during local browser development
  if (
    typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')
  ) {
    return 'http://localhost:4000';
  }
  // 4. In production without configured realtime URL, return empty string so we don't spam localhost
  return '';
}

export interface RealtimeDiagnostics {
  realtimeUrl: string;
  transport: string;
  connectionState: ConnectionState;
  socketId: string | null;
  reconnectAttempts: number;
  disconnectReason: string | null;
  lastError: string | null;
}

export class RealtimeClient {
  private socket: Socket | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private options: RealtimeClientOptions;
  private listeners = new Map<string, Set<Function>>();
  private connectionState: ConnectionState = 'disconnected';
  private reconnectAttempts = 0;
  private disconnectReason: string | null = null;
  private lastError: string | null = null;
  private signalingHandler?: (msg: any) => void;
  private chatTypingHandler?: (data: any) => void;

  constructor(options: RealtimeClientOptions) {
    this.options = options;
  }

  on(event: string, handler: (...args: any[]) => void): () => void {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);

    if (this.socket) {
      this.socket.on(event, handler as any);
    }

    return () => this.off(event, handler);
  }

  off(event: string, handler: (...args: any[]) => void): void {
    const set = this.listeners.get(event);
    if (set) {
      set.delete(handler);
      if (set.size === 0) {
        this.listeners.delete(event);
      }
    }
    if (this.socket) {
      this.socket.off(event, handler as any);
    }
  }

  getDiagnostics(): RealtimeDiagnostics {
    return {
      realtimeUrl: this.options.url,
      transport: (this.socket?.io?.engine as any)?.transport?.name || 'none',
      connectionState: this.connectionState,
      socketId: this.socket?.id || null,
      reconnectAttempts: this.reconnectAttempts,
      disconnectReason: this.disconnectReason,
      lastError: this.lastError,
    };
  }

  connect(): void {
    if (this.socket) {
      this.socket.disconnect();
    }

    const isLocalhost =
      this.options.url.includes('localhost') || this.options.url.includes('127.0.0.1');
    const isProdBrowser =
      typeof window !== 'undefined' &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1';

    if (!this.options.url || (isProdBrowser && isLocalhost)) {
      console.warn(
        '[RealtimeClient] Realtime gateway is not configured for production or points to localhost. Connection aborted.'
      );
      this.connectionState = 'disconnected';
      this.options.onConnectionChange?.('disconnected');
      return;
    }

    this.connectionState = 'connecting';
    this.options.onConnectionChange?.('connecting');

    this.socket = io(this.options.url, {
      auth: { token: this.options.token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: Infinity,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 4000,
      timeout: 10000,
    });

    if (typeof window !== 'undefined') {
      window.addEventListener('online', () => {
        console.log('[RealtimeClient] Browser online event detected, ensuring socket connection is active...');
        if (!this.socket?.connected) {
          this.socket?.connect();
        }
      });
    }

    // Re-bind all dynamically registered listeners
    this.listeners.forEach((handlers, event) => {
      handlers.forEach((h) => this.socket?.on(event, h as any));
    });

    this.socket.on('connect', () => {
      console.log('[RealtimeClient] Connected to Socket.IO gateway. Socket ID:', this.socket?.id);
      this.connectionState = 'connected';
      this.reconnectAttempts = 0;
      this.disconnectReason = null;
      this.lastError = null;
      this.options.onConnectionChange?.('connected');
      this.startHeartbeat();
    });

    this.socket.on('disconnect', (reason) => {
      this.stopHeartbeat();
      this.disconnectReason = reason;
      if (reason === 'io server disconnect') {
        this.connectionState = 'disconnected';
        this.options.onConnectionChange?.('disconnected');
      } else {
        this.connectionState = 'reconnecting';
        this.options.onConnectionChange?.('reconnecting');
      }
    });

    this.socket.on('connect_error', (err) => {
      console.warn('[RealtimeClient] Connect error:', err.message);
      this.lastError = err.message;
      this.reconnectAttempts += 1;
      this.connectionState = 'reconnecting';
      this.options.onConnectionChange?.('reconnecting');
      this.options.onError?.(err);
    });

    this.socket.io.on('reconnect_failed', () => {
      console.warn('[RealtimeClient] Reconnection attempts failed, marking disconnected');
      this.connectionState = 'disconnected';
      this.options.onConnectionChange?.('disconnected');
    });

    this.socket.on('room_sync', (data) => {
      this.options.onSync?.(data);
    });

    this.socket.on('interview_event', (event) => {
      this.options.onEvent?.(event);
    });

    this.socket.on('webrtc_signal', (data) => {
      this.signalingHandler?.(data);
    });

    this.socket.on('chat_typing', (data) => {
      this.chatTypingHandler?.(data);
    });

    this.socket.on('error', (err) => {
      this.lastError = typeof err === 'string' ? err : err?.message || 'Unknown error';
      this.options.onError?.(err);
    });
  }

  onSignaling(handler: (msg: any) => void): void {
    this.signalingHandler = handler;
  }

  sendSignaling(message: any): void {
    if (!this.socket || !this.socket.connected) {
      return;
    }
    this.socket.emit('webrtc_signal', message);
  }

  sendMediaStateChange(data: { camera?: boolean; microphone?: boolean; screenShare?: boolean }): void {
    if (!this.socket || !this.socket.connected) {
      return;
    }
    this.socket.emit('media_state_change', data);
  }

  onChatTyping(handler: (data: any) => void): () => void {
    this.chatTypingHandler = handler;
    return () => {
      if (this.chatTypingHandler === handler) {
        this.chatTypingHandler = undefined;
      }
    };
  }

  sendTyping(channelId: string, channelType: string, isTyping: boolean): void {
    if (!this.socket || !this.socket.connected) {
      return;
    }
    this.socket.emit('chat_typing', {
      channelId,
      channelType,
      isTyping,
    });
  }

  dispatchEvent(eventType: string, payload: any, interviewerOnly: boolean = false): void {
    if (!this.socket || !this.socket.connected) {
      console.warn('[RealtimeClient] Cannot dispatch event: socket not connected');
      return;
    }
    this.socket.emit('dispatch_event', {
      event_type: eventType,
      payload,
      interviewer_only: interviewerOnly,
    });
  }

  sendMediaState(data: { camera?: boolean; microphone?: boolean; screenShare?: boolean }): void {
    this.sendMediaStateChange(data);
  }

  emit(event: string, data?: any): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit(event, data);
    } else {
      console.warn(`[RealtimeClient] Cannot emit event "${event}": socket not connected`);
    }
  }

  getSocket(): Socket | null {
    return this.socket;
  }

  requestRoomState(): void {
    if (this.socket && this.socket.connected) {
      this.socket.emit('request_room_state');
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.socket && this.socket.connected) {
        this.socket.emit('heartbeat');
      }
    }, 25000);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  disconnect(): void {
    this.stopHeartbeat();
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    this.connectionState = 'disconnected';
    this.options.onConnectionChange?.('disconnected');
  }
}
