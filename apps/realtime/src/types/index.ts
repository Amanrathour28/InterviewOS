export interface SocketUser {
  userId: string;
  userName: string;
  userEmail: string;
  sessionId: string;
  interviewId: string;
  workspaceId: string;
  role: string;
  isInterviewer: boolean;
}

export type RealtimeEventType =
  | 'SESSION_CREATED'
  | 'SESSION_STARTED'
  | 'SESSION_PAUSED'
  | 'SESSION_RESUMED'
  | 'SESSION_ENDED'
  | 'STAGE_CHANGED'
  | 'PARTICIPANT_JOINED'
  | 'PARTICIPANT_LEFT'
  | 'PARTICIPANT_STATUS_CHANGED'
  | 'CAMERA_ENABLED'
  | 'CAMERA_DISABLED'
  | 'MICROPHONE_ENABLED'
  | 'MICROPHONE_DISABLED'
  | 'SCREEN_SHARE_STARTED'
  | 'SCREEN_SHARE_STOPPED'
  | 'MEDIA_DEVICE_CHANGED'
  | 'ACTIVE_SPEAKER_CHANGED'
  | 'CHAT_MESSAGE_CREATED'
  | 'CHAT_MESSAGE_UPDATED'
  | 'CHAT_MESSAGE_DELETED'
  | 'CHAT_THREAD_REPLY_CREATED'
  | 'CHAT_REACTION_ADDED'
  | 'CHAT_REACTION_REMOVED'
  | 'CHAT_READ_UPDATED'
  | 'CHAT_TYPING_STARTED'
  | 'CHAT_TYPING_STOPPED'
  | 'CODE_SESSION_CREATED'
  | 'CODE_FILE_CREATED'
  | 'CODE_FILE_UPDATED'
  | 'CODE_FILE_DELETED'
  | 'CODE_EDITOR_LOCKED'
  | 'CODE_EDITOR_UNLOCKED'
  | 'CODE_EXECUTION_QUEUED'
  | 'CODE_EXECUTION_STARTED'
  | 'CODE_EXECUTION_TESTING'
  | 'CODE_EXECUTION_COMPLETED'
  | 'CODE_EXECUTION_FAILED'
  | 'CODE_EXECUTION_TIMED_OUT'
  | 'CODE_EXECUTION_CANCELLED'
  | 'CODING_PROBLEM_ASSIGNED'
  | 'CODING_PROBLEM_STARTED'
  | 'CODING_PROBLEM_COMPLETED'
  | 'CODING_SUBMISSION_CREATED'
  | 'CODING_ASSESSMENT_UPDATED'
  | 'WHITEBOARD_INITIALIZED'
  | 'WHITEBOARD_PATCH'
  | 'WHITEBOARD_PRIVATE_PATCH'
  | 'WHITEBOARD_LOCKED'
  | 'WHITEBOARD_UNLOCKED'
  | 'WHITEBOARD_CLEARED'
  | 'WHITEBOARD_SNAPSHOT_CREATED'
  | 'WHITEBOARD_RESTORED'
  | 'WHITEBOARD_CURSOR'
  | 'CANDIDATE_READY'
  | 'SESSION_HEALTH_CHANGED'
  | 'NOTE_CREATED'
  | 'NOTE_DELETED'
  | 'ROOM_STATE'
  | 'ROOM_STATE_REQUEST'
  | 'PRIVATE_INTERVIEWER_NOTE'
  | 'AI_PROCESSING'
  | 'AI_SUGGESTION_CREATED'
  | 'AI_INSIGHT_CREATED'
  | 'AI_PROCESSING_FAILED'
  | 'AI_INTERVIEWER_PROCESSING'
  | 'AI_RESPONSE_ANALYZED'
  | 'AI_RECOMMENDATION_CREATED'
  | 'AI_RECOMMENDATION_ACCEPTED'
  | 'AI_RECOMMENDATION_REJECTED'
  | 'AI_RECOMMENDATION_EDITED'
  | 'AI_RECOMMENDATION_SKIPPED'
  | 'AI_RECOMMENDATION_STALE'
  | 'AI_COVERAGE_UPDATED'
  | 'TRANSCRIPT_SEGMENT_RECEIVED'
  | 'TRANSCRIPT_BOUNDARY_DETECTED'
  | 'EVALUATION_GENERATION_STARTED'
  | 'EVALUATION_DRAFT_CREATED'
  | 'EVALUATION_UPDATED'
  | 'EVALUATION_APPROVED'
  | 'EVALUATION_FINALIZED'
  | 'EVALUATION_CONTRADICTION_FOUND'
  | 'PING'
  | 'PONG'
  | 'ERROR';

export type WebRTCSignalType =
  | 'offer'
  | 'answer'
  | 'candidate'
  | 'renegotiate'
  | 'ice-restart';

export interface WebRTCSignalPayload {
  signalType: WebRTCSignalType;
  targetUserId: string;
  senderUserId: string;
  senderName?: string;
  senderRole?: string;
  sdp?: any;
  candidate?: any;
}

export interface ChatTypingPayload {
  channelId: string;
  channelType: 'public' | 'interviewer_private';
  isTyping: boolean;
  userId?: string;
  userName?: string;
}

export interface EventEnvelope<T = any> {
  event_id: string;
  session_id: string;
  event_type: RealtimeEventType;
  actor_id: string;
  actor_role: string;
  sequence: number;
  timestamp: string;
  payload: T;
}

export interface ParticipantPresence {
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

export interface RoomState {
  sessionId: string;
  interviewId: string;
  workspaceId: string;
  status: string;
  currentStage: string;
  stageStartedAt?: string;
  startedAt?: string;
  elapsedSeconds: number;
  lastSequence: number;
  participants: ParticipantPresence[];
}
