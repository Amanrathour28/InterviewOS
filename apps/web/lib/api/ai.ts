import { apiClient } from '../api';

export interface GeneratedQuestionResponse {
  request_id: string;
  task_type: string;
  output?: {
    question_text: string;
    question_type: string;
    difficulty: string;
    target_skills: string[];
    rubric: Array<{
      criteria: string;
      level_4_exemplary: string;
      level_3_competent: string;
      level_2_developing: string;
      level_1_unsatisfactory: string;
    }>;
    follow_up_hooks: string[];
    suggested_time_minutes: number;
    expected_key_points: string[];
  };
  metadata?: {
    model: string;
    provider: string;
    tokens: number;
    latency_ms: number;
    is_fallback: boolean;
  };
  status?: string;
  error_message?: string;
}

export interface FollowUpResponse {
  request_id: string;
  task_type: string;
  output?: {
    primary_follow_up: string;
    alternative_angles: string[];
    difficulty: string;
    skill_targeted: string;
    purpose: string;
    time_budget_minutes: number;
  };
  metadata?: {
    model: string;
    provider: string;
    tokens: number;
    latency_ms: number;
    is_fallback: boolean;
  };
  status?: string;
  error_message?: string;
}

export interface ResumeAnalysisResponse {
  request_id: string;
  task_type: string;
  output?: {
    skills_claimed: string[];
    key_experience_themes: string[];
    depth_verification_questions: Array<{
      topic: string;
      question: string;
      look_for: string;
    }>;
    project_deep_dives: Array<{
      project_name: string;
      key_challenges_to_probe: string[];
      suggested_scenario: string;
    }>;
    skill_gaps_or_red_flags: string[];
    seniority_assessment: string;
  };
  metadata?: {
    model: string;
    provider: string;
    tokens: number;
    latency_ms: number;
    is_fallback: boolean;
  };
  status?: string;
  error_message?: string;
}

export interface CodingAnalysisResponse {
  request_id: string;
  task_type: string;
  output?: {
    approach_classification: string;
    time_complexity: string;
    space_complexity: string;
    edge_cases_unhandled: string[];
    code_smells: string[];
    suggested_hints: string[];
    follow_up_optimizations: string[];
    sandbox_result_summary: string;
  };
  metadata?: {
    model: string;
    provider: string;
    tokens: number;
    latency_ms: number;
    is_fallback: boolean;
  };
  status?: string;
  error_message?: string;
}

export interface SystemDesignAnalysisResponse {
  request_id: string;
  task_type: string;
  output?: {
    components_identified: string[];
    architecture_style: string;
    single_points_of_failure: string[];
    scalability_concerns: string[];
    missing_elements: string[];
    targeted_critique_questions: string[];
    next_drill_down: string;
  };
  metadata?: {
    model: string;
    provider: string;
    tokens: number;
    latency_ms: number;
    is_fallback: boolean;
  };
  status?: string;
  error_message?: string;
}

export interface AILogEntry {
  id: string;
  request_id: string;
  workspace_id: string;
  interview_id?: string;
  agent_name?: string;
  task_type?: string;
  provider: string;
  model: string;
  is_fallback: boolean;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  latency_ms: number;
  success: boolean;
  error_type?: string;
  created_at: string;
}

export const aiApi = {
  generateQuestion: (data: {
    interview_id: string;
    workspace_id: string;
    session_id?: string;
    difficulty?: string;
    question_type?: string;
    topic_focus?: string;
    topics_covered?: string[];
    candidate?: any;
    job?: any;
    previous_questions?: string[];
    current_stage?: string;
  }) => {
    return apiClient<GeneratedQuestionResponse>('/ai/generate-question', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  generateFollowUp: (data: {
    interview_id: string;
    workspace_id: string;
    question_asked: string;
    candidate_answer: string;
    session_id?: string;
    target_skill?: string;
    difficulty?: string;
    remaining_seconds?: number;
  }) => {
    return apiClient<FollowUpResponse>('/ai/generate-follow-up', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  analyzeResume: (data: {
    interview_id: string;
    workspace_id: string;
    resume_text?: string;
    candidate_profile?: any;
    job?: any;
  }) => {
    return apiClient<ResumeAnalysisResponse>('/ai/analyze-resume', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  analyzeCoding: (data: {
    interview_id: string;
    workspace_id: string;
    session_id?: string;
    problem?: any;
    candidate_code?: string;
    execution_result?: any;
    submission_history?: any[];
  }) => {
    return apiClient<CodingAnalysisResponse>('/ai/analyze-coding', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  analyzeSystemDesign: (data: {
    interview_id: string;
    workspace_id: string;
    session_id?: string;
    whiteboard_state?: any;
    candidate_explanation?: string;
    problem_statement?: string;
  }) => {
    return apiClient<SystemDesignAnalysisResponse>('/ai/analyze-system-design', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getHealth: () => {
    return apiClient<{ status: string; service: string; providers?: any }>('/ai/health', {
      method: 'GET',
    });
  },

  getLogs: (workspaceId: string, interviewId?: string, limit: number = 50) => {
    const params: Record<string, string> = {
      workspace_id: workspaceId,
      limit: limit.toString(),
    };
    if (interviewId) {
      params.interview_id = interviewId;
    }
    return apiClient<AILogEntry[]>('/ai/logs', {
      method: 'GET',
      params,
    });
  },

  // Phase 14 Adaptive Endpoints
  ingestTranscriptSegment: (interviewId: string, data: {
    speaker_role?: string;
    text: string;
    start_time_seconds?: number;
    end_time_seconds?: number;
    confidence?: number;
    is_final?: boolean;
    detected_topics?: string[];
  }) => {
    return apiClient<any>(`/interviews/${interviewId}/adaptive/transcripts`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getTranscripts: (interviewId: string) => {
    return apiClient<any[]>(`/interviews/${interviewId}/adaptive/transcripts`, {
      method: 'GET',
    });
  },

  generateAdaptiveRecommendation: (interviewId: string, data: {
    session_id?: string;
    current_question?: string;
    candidate_response?: string;
    competency_focus?: string;
    difficulty?: string;
  }) => {
    return apiClient<any>(`/interviews/${interviewId}/adaptive/recommendations/generate`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  getAdaptiveRecommendations: (interviewId: string) => {
    return apiClient<any[]>(`/interviews/${interviewId}/adaptive/recommendations`, {
      method: 'GET',
    });
  },

  acceptAdaptiveRecommendation: (interviewId: string, recId: string) => {
    return apiClient<any>(`/interviews/${interviewId}/adaptive/recommendations/${recId}/accept`, {
      method: 'POST',
    });
  },

  editAdaptiveRecommendation: (interviewId: string, recId: string, editedQuestion: string) => {
    return apiClient<any>(`/interviews/${interviewId}/adaptive/recommendations/${recId}/edit`, {
      method: 'POST',
      body: JSON.stringify({ edited_question: editedQuestion }),
    });
  },

  rejectAdaptiveRecommendation: (interviewId: string, recId: string, reason?: string) => {
    return apiClient<any>(`/interviews/${interviewId}/adaptive/recommendations/${recId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  },

  skipAdaptiveRecommendation: (interviewId: string, recId: string) => {
    return apiClient<any>(`/interviews/${interviewId}/adaptive/recommendations/${recId}/skip`, {
      method: 'POST',
    });
  },

  getLiveCoverage: (interviewId: string) => {
    return apiClient<any>(`/interviews/${interviewId}/adaptive/coverage`, {
      method: 'GET',
    });
  },
};

