import http from 'http';
import express from 'express';
import cors from 'cors';
import { Server, Socket } from 'socket.io';
import { config } from './config/index.js';
import { createRedisAdapter, checkRedisHealth } from './redis/client.js';
import { authenticateSocket } from './auth/jwt-auth.js';
import { RoomManager } from './rooms/room-manager.js';
import { presenceTracker } from './presence/presence-tracker.js';
import { eventRouter } from './events/event-router.js';
import { SocketUser } from './types/index.js';

const app = express();
app.use(cors({ origin: config.corsOrigins, credentials: true }));
app.use(express.json());

// 1. Health check endpoint
app.get('/health', async (_req, res) => {
  const redisHealthy = await checkRedisHealth();
  res.json({
    status: 'ok',
    service: 'interviewos-realtime',
    uptime_seconds: process.uptime(),
    timestamp: new Date().toISOString(),
    redis_connected: redisHealthy,
  });
});

const server = http.createServer(app);

// 2. Initialize Socket.IO server
const io = new Server(server, {
  cors: {
    origin: config.corsOrigins,
    methods: ['GET', 'POST'],
    credentials: true,
  },
  pingInterval: config.heartbeatIntervalMs,
  pingTimeout: config.heartbeatTimeoutMs,
});

async function bootstrap() {
  // Attach Redis adapter for horizontal scaling if available
  const adapter = await createRedisAdapter();
  if (adapter) {
    io.adapter(adapter);
    console.log('[Realtime] Redis Pub/Sub Adapter initialized for multi-instance clustering');
  } else {
    console.log('[Realtime] Running with local In-Memory Socket.IO Adapter');
  }

  // Socket authentication middleware
  io.use(authenticateSocket);

  // Socket connection lifecycle
  io.on('connection', async (socket: Socket) => {
    const user = socket.data.user as SocketUser;
    if (!user) {
      socket.disconnect(true);
      return;
    }

    console.log(`[Socket Connected] ID: ${socket.id} | User: ${user.userName} (${user.role}) | Session: ${user.sessionId}`);

    // Join isolated public/interviewer rooms
    await RoomManager.joinRooms(socket, user);

    // Track presence
    const { presence, isNewJoin } = presenceTracker.addConnection(user.sessionId, socket.id, user);

    // Broadcast PARTICIPANT_JOINED if first tab/connection
    if (isNewJoin) {
      const joinEvent = eventRouter.createCanonicalEvent(
        user.sessionId,
        'PARTICIPANT_JOINED',
        user.userId,
        user.role,
        {
          user_id: user.userId,
          user_name: user.userName,
          role: user.role,
          online: true,
        }
      );
      eventRouter.broadcastEvent(io, joinEvent, false);
    }

    // Send immediate sync state to joining socket
    socket.emit('room_sync', {
      session_id: user.sessionId,
      user_id: user.userId,
      role: user.role,
      is_interviewer: user.isInterviewer,
      participants: presenceTracker.getParticipants(user.sessionId),
      timestamp: new Date().toISOString(),
    });

    // Handle heartbeat ping
    socket.on('heartbeat', () => {
      presenceTracker.updateHeartbeat(user.sessionId, user.userId);
      socket.emit('heartbeat_ack', { timestamp: new Date().toISOString() });
    });

    // Handle room state request
    socket.on('request_room_state', () => {
      socket.emit('room_sync', {
        session_id: user.sessionId,
        participants: presenceTracker.getParticipants(user.sessionId),
        timestamp: new Date().toISOString(),
      });
    });

    // Handle WebRTC Peer-to-Peer Signaling (offer, answer, candidate, renegotiate, ice-restart)
    socket.on('webrtc_signal', (payload: any) => {
      if (!payload || !payload.targetUserId || !payload.signalType) {
        socket.emit('error', { code: 'BAD_REQUEST', message: 'Invalid WebRTC signal payload' });
        return;
      }

      // Direct ephemeral signaling routed strictly to target participant in this session
      const targetRoom = RoomManager.getUserRoom(user.sessionId, payload.targetUserId);

      const outgoingSignal = {
        signalType: payload.signalType,
        targetUserId: payload.targetUserId,
        senderUserId: user.userId,
        senderName: user.userName,
        senderRole: user.role,
        sdp: payload.sdp,
        candidate: payload.candidate,
      };

      socket.to(targetRoom).emit('webrtc_signal', outgoingSignal);
    });

    // Handle Media State Updates (camera, microphone, screen share status)
    socket.on('media_state_change', (data: { camera?: boolean; microphone?: boolean; screenShare?: boolean }) => {
      if (!data) return;

      const mediaEvent = eventRouter.createCanonicalEvent(
        user.sessionId,
        'PARTICIPANT_STATUS_CHANGED',
        user.userId,
        user.role,
        {
          user_id: user.userId,
          deviceState: data,
        }
      );
      eventRouter.broadcastEvent(io, mediaEvent, false);
    });

    // Handle Chat Ephemeral Typing State
    socket.on('chat_typing', (data: { channelId: string; channelType: string; isTyping: boolean }) => {
      if (!data || !data.channelId) return;

      // Reject candidates from emitting typing events to private interviewer channel
      if (data.channelType === 'interviewer_private' && !user.isInterviewer) {
        return;
      }

      const typingPayload = {
        channelId: data.channelId,
        channelType: data.channelType,
        userId: user.userId,
        userName: user.userName,
        isTyping: Boolean(data.isTyping),
      };

      if (data.channelType === 'interviewer_private') {
        socket.to(RoomManager.getInterviewerRoom(user.sessionId)).emit('chat_typing', typingPayload);
      } else {
        socket.to(RoomManager.getPublicRoom(user.sessionId)).emit('chat_typing', typingPayload);
      }
    });

    // Handle Yjs CRDT Collaboration Updates
    socket.on('coding_yjs_update', (data: { fileId: string; update: string | Uint8Array; isLocked?: boolean }) => {
      if (!data || !data.fileId) return;

      // Server-side lock check: if locked and sender is candidate, drop update
      if (data.isLocked && !user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot edit when workspace is locked' });
        return;
      }

      // Broadcast Yjs CRDT binary/base64 update to all other room participants
      socket.to(RoomManager.getPublicRoom(user.sessionId)).emit('coding_yjs_update', {
        fileId: data.fileId,
        update: data.update,
        senderUserId: user.userId,
      });
    });

    // Handle Monaco Cursor Awareness / Collaborator Presence
    socket.on('coding_awareness_update', (data: { fileId: string; awareness: any }) => {
      if (!data || !data.fileId) return;

      socket.to(RoomManager.getPublicRoom(user.sessionId)).emit('coding_awareness_update', {
        fileId: data.fileId,
        awareness: data.awareness,
        user: {
          id: user.userId,
          name: user.userName,
          role: user.role,
        },
      });
    });

    // Handle Whiteboard Realtime Mutations (Phase 10)
    socket.on('whiteboard_patch', (data: { changes: any; isLocked?: boolean }) => {
      if (!data) return;

      // Server-side lock check: if locked and sender is candidate, drop mutation
      if (data.isLocked && !user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot edit when whiteboard is locked' });
        return;
      }

      socket.to(RoomManager.getPublicRoom(user.sessionId)).emit('whiteboard_patch', {
        changes: data.changes,
        senderUserId: user.userId,
        senderName: user.userName,
      });
    });

    // Handle Whiteboard Private Interviewer Layer (Phase 10)
    socket.on('whiteboard_private_patch', (data: { changes: any }) => {
      if (!data || !user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot broadcast private layer changes' });
        return;
      }

      // Broadcast exclusively to interviewer room channel
      socket.to(RoomManager.getInterviewerRoom(user.sessionId)).emit('whiteboard_private_patch', {
        changes: data.changes,
        senderUserId: user.userId,
      });
    });

    // Handle Whiteboard Ephemeral Presence & Cursors (Phase 10)
    socket.on('whiteboard_cursor', (data: { x: number; y: number; selectedShapeIds?: string[] }) => {
      if (!data) return;

      socket.to(RoomManager.getPublicRoom(user.sessionId)).emit('whiteboard_cursor', {
        userId: user.userId,
        userName: user.userName,
        userRole: user.role,
        x: data.x,
        y: data.y,
        selectedShapeIds: data.selectedShapeIds || [],
      });
    });

    // Handle Whiteboard Lock State Broadcast (Phase 10)
    socket.on('whiteboard_lock_state', (data: { is_locked: boolean }) => {
      if (!user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot toggle whiteboard lock state' });
        return;
      }

      socket.to(RoomManager.getPublicRoom(user.sessionId)).emit('whiteboard_lock_state', {
        is_locked: data.is_locked,
        senderUserId: user.userId,
      });
    });

    // Handle Whiteboard Clear (Phase 10)
    socket.on('whiteboard_clear', () => {
      if (!user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot clear whiteboard' });
        return;
      }

      socket.to(RoomManager.getPublicRoom(user.sessionId)).emit('whiteboard_clear', {
        senderUserId: user.userId,
      });
    });

    // Handle Whiteboard Restore Snapshot (Phase 10)
    socket.on('whiteboard_restore', (data: { snapshot_id: string; document: any }) => {
      if (!user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot restore whiteboard snapshots' });
        return;
      }

      socket.to(RoomManager.getPublicRoom(user.sessionId)).emit('whiteboard_restore', {
        snapshot_id: data.snapshot_id,
        document: data.document,
        senderUserId: user.userId,
      });
    });

    // Handle Candidate Waiting Room Readiness (Phase 11)
    socket.on('candidate_ready', (data: { candidate_name?: string }) => {
      const readyEvent = eventRouter.createCanonicalEvent(
        user.sessionId,
        'CANDIDATE_READY',
        user.userId,
        user.role,
        {
          user_id: user.userId,
          user_name: user.userName,
          candidate_name: data?.candidate_name || user.userName,
          timestamp: new Date().toISOString(),
        }
      );
      eventRouter.broadcastEvent(io, readyEvent, false);
    });

    // Handle Stage Transition Broadcast (Phase 11)
    socket.on('stage_transition', (data: { stage: string; stage_name?: string }) => {
      if (!user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot transition stages' });
        return;
      }

      const stageEvent = eventRouter.createCanonicalEvent(
        user.sessionId,
        'STAGE_CHANGED',
        user.userId,
        user.role,
        {
          new_stage: data.stage,
          stage_name: data.stage_name || data.stage,
          started_at: new Date().toISOString(),
        }
      );
      eventRouter.broadcastEvent(io, stageEvent, false);
    });

    // Handle generic interview event from client
    socket.on('dispatch_event', (data: { event_type: string; payload: any; interviewer_only?: boolean }) => {
      if (!data || !data.event_type) return;

      // Restrict candidates from sending private interviewer events
      if (data.interviewer_only && !user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot dispatch interviewer-only events' });
        return;
      }

      const canonicalEvent = eventRouter.createCanonicalEvent(
        user.sessionId,
        data.event_type as any,
        user.userId,
        user.role,
        data.payload || {}
      );

      eventRouter.broadcastEvent(io, canonicalEvent, Boolean(data.interviewer_only));
    });

    // Handle AI Copilot events (Phase 12: Interviewer-only)
    socket.on('ai_event', (data: { event_type: string; payload: any }) => {
      if (!user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot access AI events' });
        return;
      }

      const aiEvent = eventRouter.createCanonicalEvent(
        user.sessionId,
        (data.event_type as any) || 'AI_SUGGESTION_CREATED',
        user.userId,
        user.role,
        data.payload || {}
      );

      // Broadcast exclusively to interviewer room — candidates never receive AI events
      eventRouter.broadcastEvent(io, aiEvent, true);
    });

    // Handle Transcript Segment Streaming (Phase 14)
    socket.on('transcript_segment', (data: { segment: any; boundary_status?: string }) => {
      const transEvent = eventRouter.createCanonicalEvent(
        user.sessionId,
        'TRANSCRIPT_SEGMENT_RECEIVED',
        user.userId,
        user.role,
        {
          segment: data.segment,
          boundary_status: data.boundary_status,
          senderUserId: user.userId,
          timestamp: new Date().toISOString(),
        }
      );
      eventRouter.broadcastEvent(io, transEvent, false);
    });

    // Handle Adaptive AI Recommendations (Phase 14: Interviewer-only)
    socket.on('adaptive_recommendation', (data: { recommendation: any; action_type?: string }) => {
      if (!user.isInterviewer) {
        socket.emit('error', { code: 'FORBIDDEN', message: 'Candidate cannot access adaptive recommendations' });
        return;
      }

      const recEvent = eventRouter.createCanonicalEvent(
        user.sessionId,
        'AI_RECOMMENDATION_CREATED',
        user.userId,
        user.role,
        {
          recommendation: data.recommendation,
          action_type: data.action_type || 'recommendation_created',
          timestamp: new Date().toISOString(),
        }
      );
      eventRouter.broadcastEvent(io, recEvent, true);
    });

    // Handle disconnection
    socket.on('disconnect', (reason) => {
      console.log(`[Socket Disconnected] ID: ${socket.id} | Reason: ${reason}`);
      const { presence: updatedPresence, isTotalLeave } = presenceTracker.removeConnection(
        user.sessionId,
        socket.id,
        user.userId
      );

      if (isTotalLeave && updatedPresence) {
        const leaveEvent = eventRouter.createCanonicalEvent(
          user.sessionId,
          'PARTICIPANT_LEFT',
          user.userId,
          user.role,
          {
            user_id: user.userId,
            user_name: user.userName,
            role: user.role,
            online: false,
          }
        );
        eventRouter.broadcastEvent(io, leaveEvent, false);
      }
    });
  });

  server.listen(config.port, '0.0.0.0', () => {
    console.log(`🚀 InterviewOS Realtime Gateway running on port ${config.port} (0.0.0.0)`);
    console.log(`📡 Health check available at http://0.0.0.0:${config.port}/health`);
  });
}

bootstrap().catch((err) => {
  console.error('[Realtime Startup Error]:', err);
  process.exit(1);
});
