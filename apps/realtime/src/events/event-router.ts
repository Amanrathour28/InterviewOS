import crypto from 'crypto';
import { Server, Socket } from 'socket.io';
import { EventEnvelope, RealtimeEventType, SocketUser } from '../types/index.js';
import { RoomManager } from '../rooms/room-manager.js';

class EventRouter {
  // session_id -> sequence counter
  private sequenceCounters = new Map<string, number>();

  initSessionSequence(sessionId: string, initialSequence: number = 0): void {
    if (!this.sequenceCounters.has(sessionId)) {
      this.sequenceCounters.set(sessionId, initialSequence);
    }
  }

  getNextSequence(sessionId: string): number {
    const current = this.sequenceCounters.get(sessionId) || 0;
    const next = current + 1;
    this.sequenceCounters.set(sessionId, next);
    return next;
  }

  createCanonicalEvent<T = any>(
    sessionId: string,
    eventType: RealtimeEventType,
    actorId: string,
    actorRole: string,
    payload: T
  ): EventEnvelope<T> {
    const sequence = this.getNextSequence(sessionId);
    return {
      event_id: crypto.randomUUID(),
      session_id: sessionId,
      event_type: eventType,
      actor_id: actorId,
      actor_role: actorRole,
      sequence,
      timestamp: new Date().toISOString(),
      payload,
    };
  }

  broadcastEvent(io: Server, event: EventEnvelope, isInterviewerOnly: boolean = false): void {
    if (isInterviewerOnly) {
      const room = RoomManager.getInterviewerRoom(event.session_id);
      io.to(room).emit('interview_event', event);
    } else {
      const room = RoomManager.getPublicRoom(event.session_id);
      io.to(room).emit('interview_event', event);
    }
  }
}

export const eventRouter = new EventRouter();
