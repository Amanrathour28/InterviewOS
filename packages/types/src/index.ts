/**
 * Core User & Role Types
 */
export type UserRole =
  | 'candidate'
  | 'interviewer'
  | 'recruiter'
  | 'organization_admin'
  | 'platform_admin';

export interface User {
  id: string;
  email: string;
  fullName: string;
  role: UserRole;
  avatarUrl?: string;
  organizationId?: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * Interview Types & Statuses
 */
export type InterviewType =
  | 'human'
  | 'ai'
  | 'ai_assisted'
  | 'mock'
  | 'coding'
  | 'system_design'
  | 'panel';

export type InterviewStatus =
  | 'draft'
  | 'scheduled'
  | 'in_progress'
  | 'paused'
  | 'completed'
  | 'cancelled';

export interface Interview {
  id: string;
  title: string;
  type: InterviewType;
  status: InterviewStatus;
  scheduledAt: string;
  durationMinutes: number;
  candidateId: string;
  interviewerIds: string[];
  organizationId: string;
  createdAt: string;
  updatedAt: string;
}

/**
 * Interview Session Statuses & Stages (Phase 5)
 */
export type InterviewSessionStatus =
  | 'waiting'
  | 'active'
  | 'paused'
  | 'completed'
  | 'cancelled'
  | 'expired';

export type InterviewStage =
  | 'introduction'
  | 'behavioral'
  | 'technical'
  | 'coding'
  | 'system_design'
  | 'closing'
  | 'completed';

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

/**
 * Chat Domain Types (Phase 7)
 */
export type ChatChannelType = 'public' | 'interviewer_private';

export type ChatMessageType = 'text' | 'code' | 'system';

export interface ChatReaction {
  id: string;
  message_id: string;
  user_id: string;
  emoji: string;
  reaction?: string;
  created_at: string;
}

export interface ChatChannel {
  id: string;
  interview_id?: string;
  session_id?: string;
  name: string;
  type?: ChatChannelType;
  channel_type?: ChatChannelType;
  created_at?: string;
  unread_count: number;
}

export interface ChatMessage {
  id: string;
  channel_id: string;
  workspace_id?: string;
  session_id?: string;
  client_message_id?: string;
  sender_id: string;
  sender_name?: string;
  sender_role?: string;
  message_type: ChatMessageType;
  content: string;
  metadata?: Record<string, any>;
  code_snippet?: {
    code: string;
    language: string;
    title?: string;
  };
  parent_id?: string | null;
  parent_message_id?: string | null;
  thread_count?: number;
  reply_count?: number;
  reactions?: ChatReaction[];
  is_edited?: boolean;
  is_deleted?: boolean;
  created_at: string;
  updated_at?: string;
}

export type ChatMessageData = ChatMessage;

/**
 * Realtime Event Types
 */
export type RealtimeEventType =
  | 'PRESENCE_JOIN'
  | 'PRESENCE_LEAVE'
  | 'PRESENCE_UPDATE'
  | 'HEARTBEAT'
  | 'SIGNALING_OFFER'
  | 'SIGNALING_ANSWER'
  | 'SIGNALING_ICE_CANDIDATE'
  | 'SESSION_START'
  | 'SESSION_PAUSE'
  | 'SESSION_RESUME'
  | 'SESSION_END'
  | 'STAGE_CHANGE'
  | 'CHAT_MESSAGE'
  | 'CHAT_TYPING'
  | 'CHAT_REACTION'
  | 'CODE_UPDATE'
  | 'CODE_LOCK_ACQUIRE'
  | 'CODE_LOCK_RELEASE'
  | 'CODE_CURSOR'
  | 'EXECUTION_START'
  | 'EXECUTION_RESULT'
  | 'PROBLEM_SWITCH'
  | 'WHITEBOARD_UPDATE'
  | 'WHITEBOARD_LOCK'
  | 'WHITEBOARD_UNLOCK'
  | 'WHITEBOARD_SNAPSHOT'
  | 'NOTE_CREATE'
  | 'NOTE_UPDATE'
  | 'NOTE_DELETE'
  | 'AI_COPILOT_SUGGESTION'
  | 'AI_COPILOT_INSIGHT'
  | 'AI_COPILOT_STATUS'
  | 'DISCONNECT'
  | 'RECONNECT';

export interface ProblemLibraryItem {
  id: string;
  workspace_id?: string | null;
  title: string;
  slug: string;
  difficulty: 'easy' | 'medium' | 'hard';
  category: string;
  description: string;
  starter_templates: Record<string, string>;
  is_template: boolean;
  is_system: boolean;
  current_version_id?: string | null;
  created_at: string;
  updated_at: string;
}

export * from './languages';

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

export interface RealtimeEvent<T = unknown> {
  id: string;
  interviewId: string;
  type: RealtimeEventType;
  actorId: string;
  actorRole: UserRole;
  timestamp: string;
  payload: T;
}

export interface WhiteboardSnapshotSummary {
  id: string;
  whiteboard_id: string;
  created_by?: string | null;
  snapshot_number: number;
  label: string;
  source: string;
  document: Record<string, any>;
  private_layer?: Record<string, any> | null;
  created_at: string;
}

export interface WhiteboardData {
  id: string;
  interview_session_id: string;
  workspace_id: string;
  name: string;
  is_locked: boolean;
  document: Record<string, any>;
  private_layer?: Record<string, any> | null;
  created_by?: string | null;
  snapshots: WhiteboardSnapshotSummary[];
  created_at: string;
  updated_at: string;
}

export type NoteCategoryType = 'general' | 'rubric' | 'coding' | 'system_design' | 'behavioral';

export interface InterviewerNoteData {
  id: string;
  session_id: string;
  user_id: string;
  author_name?: string | null;
  category: NoteCategoryType;
  stage?: string | null;
  content: string;
  rating?: number | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface TimelineEventData {
  id: string;
  event_type: string;
  category: 'lifecycle' | 'stages' | 'coding' | 'whiteboard' | 'chat' | 'participants';
  title: string;
  actor_name: string;
  actor_role: string;
  timestamp: string;
  sequence: number;
  payload: Record<string, any>;
}

export interface SessionHealthData {
  session_id: string;
  status: string;
  is_operational: boolean;
  active_participants_count: number;
  websocket_healthy: boolean;
  webrtc_healthy: boolean;
  system_warnings: string[];
}

export interface TelemetryEventEnvelope {
  domain: 'INTERVIEW' | 'PARTICIPANT' | 'QUESTION' | 'CODING' | 'WHITEBOARD' | 'CHAT' | 'STAGE' | 'SYSTEM';
  eventType: RealtimeEventType;
  sessionId: string;
  timestamp: string;
  actorId?: string;
  actorRole: string;
  payload: Record<string, any>;
}

/**
 * Phase 13: Intelligence, Matching & Planning Types
 */

export interface ResumeVersionSummary {
  id: string;
  candidate_id: string;
  workspace_id: string;
  version_number: number;
  file_name: string;
  mime_type: string;
  file_size: number;
  is_active: boolean;
  parsing_status: 'pending' | 'processing' | 'completed' | 'failed';
  created_at: string;
}

export interface ResumeClaimData {
  id: string;
  claim: string;
  category: string;
  status: 'explicit' | 'inferred' | 'unverified';
  confidence: number;
  verification_priority: 'high' | 'medium' | 'low';
  evidence: {
    source?: string;
    page?: number;
    text?: string;
  };
  suggested_probes: string[];
}

export interface StructuredResumeProfile {
  summary: string;
  experience_years?: number;
  skills: Array<{ name: string; proficiency?: string; confidence?: number; evidence?: string }>;
  projects: Array<{ title: string; description: string; technologies: string[] }>;
  education?: any[];
  certifications?: any[];
  confidence: number;
}

export interface JobRequirementData {
  id: string;
  skill: string;
  canonical_skill: string;
  category: string;
  requirement_type: 'required' | 'preferred' | 'inferred';
  importance: number;
  confidence: number;
  evidence?: string;
}

export interface JobIntelligenceData {
  job_id: string;
  seniority: string;
  technical_domains: string[];
  responsibilities: string[];
  interview_focus: string[];
  suggested_rounds: string[];
  requirements: JobRequirementData[];
}

export interface CandidateJobMatchData {
  id: string;
  job_id: string;
  candidate_id: string;
  overall_score: number;
  required_skill_coverage: number;
  preferred_skill_coverage: number;
  experience_fit: number;
  project_relevance: number;
  seniority_fit: number;
  domain_fit: number;
  scoring_weights: Record<string, number>;
  strengths: Array<{ skill: string; category?: string; importance?: string; evidence: string; confidence?: number }>;
  gaps: Array<{ skill: string; category?: string; importance?: string; reason: string }>;
  verification_areas: Array<{ topic?: string; claim?: string; reason?: string; probes?: string[] }>;
  explanation?: string;
}

export interface BlueprintRoundData {
  id?: string;
  name: string;
  round_type: string;
  sequence: number;
  duration_minutes: number;
  difficulty: string;
  objectives: string[];
  competencies: string[];
  topics: string[];
  suggested_question_count: number;
  scoring_weight: number;
}

export interface InterviewBlueprintData {
  id: string;
  workspace_id: string;
  interview_id?: string;
  job_id?: string;
  candidate_id: string;
  version_number: number;
  title: string;
  status: 'draft' | 'reviewed' | 'approved' | 'applied' | 'archived';
  total_duration_minutes: number;
  target_seniority: string;
  candidate_focus_areas: string[];
  job_focus_areas: string[];
  verification_priorities: string[];
  rounds: BlueprintRoundData[];
  approved_at?: string;
  applied_at?: string;
  created_at: string;
}

export interface QuestionPlanItemData {
  id?: string;
  sequence: number;
  title: string;
  prompt: string;
  competency: string;
  difficulty: 'easy' | 'medium' | 'hard';
  progression_stage: 'warmup' | 'fundamental' | 'practical' | 'deep_dive' | 'verification';
  expected_signal?: string;
  candidate_evidence_tested?: string;
  job_requirement_tested?: string;
  suggested_followups: string[];
  is_ai_generated?: boolean;
}

export interface RequirementCoverageMatrixRow {
  job_requirement: string;
  canonical_skill: string;
  requirement_type: string;
  candidate_evidence_level: string;
  evidence_description: string;
  interview_coverage: string;
  status: 'Covered' | 'Needs Verification' | 'Uncovered' | 'Optional';
}

export interface QuestionPlanData {
  id: string;
  workspace_id: string;
  interview_id?: string;
  candidate_id: string;
  job_id?: string;
  version_number: number;
  title: string;
  status: 'draft' | 'reviewed' | 'approved' | 'applied' | 'archived';
  items: QuestionPlanItemData[];
  coverage_summary?: {
    total_requirements: number;
    covered_count: number;
    needs_verification_count: number;
    coverage_percentage: number;
    matrix: RequirementCoverageMatrixRow[];
  };
  approved_at?: string;
  created_at: string;
}

/**
 * Phase 14: AI Interviewer & Adaptive Questioning Types
 */
export type RecommendationAction =
  | 'ask_approved_question'
  | 'generate_follow_up'
  | 'increase_difficulty'
  | 'decrease_difficulty'
  | 'probe_weak_evidence'
  | 'probe_resume_claim'
  | 'move_to_next_competency'
  | 'revisit_competency'
  | 'skip_low_value_question'
  | 'no_action';

export type RecommendationStatus =
  | 'generating'
  | 'generated'
  | 'validated'
  | 'presented'
  | 'accepted'
  | 'rejected'
  | 'edited'
  | 'skipped'
  | 'stale'
  | 'expired'
  | 'failed';

export type EvidenceStrength = 'none' | 'weak' | 'moderate' | 'strong';

export type CompetencyStatus =
  | 'not_started'
  | 'partial'
  | 'covered'
  | 'strong'
  | 'insufficient';

export type ResponseBoundaryStatus =
  | 'response_started'
  | 'response_continuing'
  | 'response_complete'
  | 'response_interrupted';

export interface TranscriptSegmentData {
  id: string;
  interview_id: string;
  session_id?: string;
  workspace_id: string;
  speaker_id?: string;
  speaker_role: 'candidate' | 'interviewer' | 'system';
  speaker_name?: string;
  start_time_seconds: number;
  end_time_seconds: number;
  text: string;
  confidence: number;
  is_final: boolean;
  detected_topics: string[];
  created_at: string;
}

export interface AIRecommendationData {
  id: string;
  interview_id: string;
  session_id?: string;
  workspace_id: string;
  action: RecommendationAction;
  status: RecommendationStatus;
  recommended_question: string;
  original_question?: string;
  edited_question?: string;
  competency?: string;
  difficulty: 'easy' | 'medium' | 'hard';
  reason: string;
  evidence_target?: string;
  time_cost_estimate_seconds: number;
  confidence: number;
  source_question_id?: string;
  source_claim_id?: string;
  context_revision: number;
  requires_interviewer_approval: boolean;
  reviewed_by?: string;
  reviewed_at?: string;
  reject_reason?: string;
  created_at: string;
}

export interface CompetencyEvidenceData {
  id: string;
  interview_id: string;
  session_id?: string;
  workspace_id: string;
  competency: string;
  evidence_strength: EvidenceStrength;
  status: CompetencyStatus;
  questions_asked_count: number;
  demonstrated_concepts: string[];
  missing_concepts: string[];
  notes?: string;
}

export interface LiveCoverageMatrix {
  total_competencies: number;
  covered_competencies: number;
  coverage_percentage: number;
  competencies: CompetencyEvidenceData[];
}

/**
 * Phase 15: Evidence-Based Evaluation, Scoring & Reporting Types
 */

export type EvaluationStatusType = 'draft' | 'in_review' | 'approved' | 'finalized';

export type HiringRecommendationType =
  | 'strong_hire'
  | 'hire'
  | 'lean_hire'
  | 'lean_no_hire'
  | 'no_hire'
  | 'insufficient_evidence';

export type EvidenceSourceType =
  | 'transcript'
  | 'coding'
  | 'code_execution'
  | 'whiteboard'
  | 'chat'
  | 'interviewer_note'
  | 'resume_claim'
  | 'adaptive_recommendation';

export type ContradictionSeverityType = 'low' | 'medium' | 'high' | 'critical';

export interface EvaluationCompetencyData {
  id: string;
  workspace_id: string;
  name: string;
  category: string;
  description?: string;
  default_weight: number;
  is_required: boolean;
  rubrics?: CompetencyRubricData[];
}

export interface CompetencyRubricData {
  id: string;
  competency_id: string;
  level: number;
  title: string;
  criteria: string;
  indicators: string[];
}

export interface EvaluationEvidenceData {
  id: string;
  workspace_id: string;
  interview_id: string;
  session_id?: string;
  candidate_id: string;
  source_type: EvidenceSourceType;
  source_id?: string;
  competency_name?: string;
  question_text?: string;
  content: string;
  structured_payload: Record<string, any>;
  evidence_timestamp_seconds: number;
  quality_score: number;
  confidence: number;
  is_candidate_evidence: boolean;
  is_interviewer_observation: boolean;
  metadata_json?: Record<string, any>;
  created_at: string;
}

export interface EvaluationCompetencyScoreData {
  id: string;
  evaluation_id: string;
  competency_name: string;
  rubric_level: number;
  calculated_score: number;
  weight: number;
  confidence: number;
  status: 'assessed' | 'not_assessed' | 'insufficient_evidence';
  rationale: string;
  observed_facts: string[];
  inferences: string[];
  evidence_ids: string[];
  is_overridden: boolean;
  original_ai_rubric_level?: number;
  override_reason?: string;
  overridden_by?: string;
  overridden_at?: string;
}

export interface EvaluationContradictionData {
  id: string;
  evaluation_id: string;
  type: string;
  severity: ContradictionSeverityType;
  source_a_type: string;
  source_a_id?: string;
  source_a_description: string;
  source_b_type: string;
  source_b_id?: string;
  source_b_description: string;
  description: string;
  resolution?: string;
  is_resolved: boolean;
  resolved_by?: string;
  resolved_at?: string;
  created_at: string;
}

export interface EvaluationScoreInputData {
  id: string;
  evaluation_id: string;
  scoring_formula: string;
  competency_weights: Record<string, number>;
  competency_rubric_levels: Record<string, number>;
  calculated_overall_score: number;
  calculated_recommendation: string;
  created_at: string;
}

export interface EvaluationData {
  id: string;
  workspace_id: string;
  interview_id: string;
  candidate_id: string;
  job_id?: string;
  status: EvaluationStatusType;
  version: number;
  overall_score: number;
  overall_rubric_level: number;
  confidence: number;
  recommendation: HiringRecommendationType;
  summary?: string;
  strengths: Array<{ claim: string; evidence_ids: string[] }>;
  development_areas: Array<{ claim: string; evidence_ids: string[] }>;
  evidence_gaps: Array<{ competency: string; reason: string }>;
  reviewed_by?: string;
  reviewed_at?: string;
  finalized_by?: string;
  finalized_at?: string;
  is_locked: boolean;
  competency_scores?: EvaluationCompetencyScoreData[];
  contradictions?: EvaluationContradictionData[];
  score_inputs?: EvaluationScoreInputData[];
  created_at: string;
  updated_at: string;
}

export interface EvaluationReportData {
  evaluation: EvaluationData;
  candidate_name: string;
  candidate_email?: string;
  job_title?: string;
  interview_title: string;
  evidence_items: EvaluationEvidenceData[];
  generated_at: string;
  is_finalized: boolean;
}


