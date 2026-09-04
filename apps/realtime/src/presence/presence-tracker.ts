import { ParticipantPresence, SocketUser } from '../types/index.js';

class PresenceTracker {
  // session_id -> Map<user_id, ParticipantPresence & { socketIds: Set<string> }>
  private sessions = new Map<string, Map<string, ParticipantPresence & { socketIds: Set<string> }>>();

  addConnection(sessionId: string, socketId: string, user: SocketUser): { presence: ParticipantPresence; isNewJoin: boolean } {
    if (!this.sessions.has(sessionId)) {
      this.sessions.set(sessionId, new Map());
    }

    const sessionParticipants = this.sessions.get(sessionId)!;
    const existing = sessionParticipants.get(user.userId);

    const nowIso = new Date().toISOString();

    if (existing) {
      existing.socketIds.add(socketId);
      existing.connectionCount = existing.socketIds.size;
      existing.online = true;
      existing.lastSeenAt = nowIso;
      return { presence: this.cleanPresence(existing), isNewJoin: false };
    }

    const newRecord = {
      userId: user.userId,
      userName: user.userName,
      role: user.role,
      online: true,
      connectionCount: 1,
      lastSeenAt: nowIso,
      socketIds: new Set([socketId]),
      deviceState: {
        camera: false,
        microphone: false,
        screenShare: false,
      },
    };

    sessionParticipants.set(user.userId, newRecord);
    return { presence: this.cleanPresence(newRecord), isNewJoin: true };
  }

  removeConnection(sessionId: string, socketId: string, userId: string): { presence?: ParticipantPresence; isTotalLeave: boolean } {
    const sessionParticipants = this.sessions.get(sessionId);
    if (!sessionParticipants) return { isTotalLeave: false };

    const record = sessionParticipants.get(userId);
    if (!record) return { isTotalLeave: false };

    record.socketIds.delete(socketId);
    record.connectionCount = record.socketIds.size;
    record.lastSeenAt = new Date().toISOString();

    if (record.connectionCount === 0) {
      record.online = false;
      return { presence: this.cleanPresence(record), isTotalLeave: true };
    }

    return { presence: this.cleanPresence(record), isTotalLeave: false };
  }

  updateHeartbeat(sessionId: string, userId: string): boolean {
    const sessionParticipants = this.sessions.get(sessionId);
    if (!sessionParticipants) return false;

    const record = sessionParticipants.get(userId);
    if (!record) return false;

    record.lastSeenAt = new Date().toISOString();
    return true;
  }

  getParticipants(sessionId: string): ParticipantPresence[] {
    const sessionParticipants = this.sessions.get(sessionId);
    if (!sessionParticipants) return [];

    return Array.from(sessionParticipants.values()).map((r) => this.cleanPresence(r));
  }

  private cleanPresence(internal: ParticipantPresence & { socketIds: Set<string> }): ParticipantPresence {
    return {
      userId: internal.userId,
      userName: internal.userName,
      role: internal.role,
      online: internal.online,
      connectionCount: internal.connectionCount,
      lastSeenAt: internal.lastSeenAt,
      deviceState: internal.deviceState,
    };
  }
}

export const presenceTracker = new PresenceTracker();
