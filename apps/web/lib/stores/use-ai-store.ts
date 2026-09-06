import { create } from 'zustand';
import {
  aiApi,
  GeneratedQuestionResponse,
  FollowUpResponse,
  ResumeAnalysisResponse,
  CodingAnalysisResponse,
  SystemDesignAnalysisResponse,
  AILogEntry,
} from '../api/ai';
import { AIRecommendationData, CompetencyEvidenceData, TranscriptSegmentData } from '@interviewos/types';

export type AICopilotTab = 'adaptive' | 'questions' | 'followups' | 'resume' | 'coding' | 'whiteboard' | 'logs';

interface AIStoreState {
  isOpen: boolean;
  activeTab: AICopilotTab;
  isLoading: boolean;
  error: string | null;
  
  // Model info from last request
  lastMetadata: {
    model?: string;
    provider?: string;
    tokens?: number;
    latency_ms?: number;
    is_fallback?: boolean;
  } | null;

  // Phase 14: Adaptive Questioning & Live Intelligence
  adaptiveRecommendation: AIRecommendationData | null;
  recommendationHistory: AIRecommendationData[];
  coverageMatrix: {
    total_competencies: number;
    covered_competencies: number;
    coverage_percentage: number;
    competencies: CompetencyEvidenceData[];
  } | null;
  liveTranscript: TranscriptSegmentData[];
  contextRevision: number;

  // Generated artifacts
  currentQuestion: GeneratedQuestionResponse['output'] | null;
  questionHistory: Array<NonNullable<GeneratedQuestionResponse['output']>>;
  
  currentFollowUp: FollowUpResponse['output'] | null;
  followUpHistory: Array<NonNullable<FollowUpResponse['output']>>;
  
  resumeAnalysis: ResumeAnalysisResponse['output'] | null;
  codingAnalysis: CodingAnalysisResponse['output'] | null;
  systemDesignAnalysis: SystemDesignAnalysisResponse['output'] | null;
  
  logs: AILogEntry[];

  // Actions
  setIsOpen: (open: boolean) => void;
  toggleIsOpen: () => void;
  setActiveTab: (tab: AICopilotTab) => void;
  clearError: () => void;

  // Adaptive actions
  fetchAdaptiveState: (interviewId: string) => Promise<void>;
  generateAdaptiveRecommendation: (interviewId: string, params: {
    session_id?: string;
    current_question?: string;
    candidate_response?: string;
    competency_focus?: string;
    difficulty?: string;
  }) => Promise<void>;
  acceptAdaptiveRecommendation: (interviewId: string, recId: string) => Promise<void>;
  editAdaptiveRecommendation: (interviewId: string, recId: string, editedQuestion: string) => Promise<void>;
  rejectAdaptiveRecommendation: (interviewId: string, recId: string, reason?: string) => Promise<void>;
  skipAdaptiveRecommendation: (interviewId: string, recId: string) => Promise<void>;
  addTranscriptSegment: (segment: TranscriptSegmentData) => void;

  generateQuestion: (params: {
    interview_id: string;
    workspace_id: string;
    difficulty?: string;
    question_type?: string;
    topic_focus?: string;
    topics_covered?: string[];
    current_stage?: string;
  }) => Promise<void>;

  generateFollowUp: (params: {
    interview_id: string;
    workspace_id: string;
    question_asked: string;
    candidate_answer: string;
    target_skill?: string;
    difficulty?: string;
  }) => Promise<void>;

  analyzeResume: (params: {
    interview_id: string;
    workspace_id: string;
    resume_text?: string;
    candidate_profile?: any;
    job?: any;
  }) => Promise<void>;

  analyzeCoding: (params: {
    interview_id: string;
    workspace_id: string;
    session_id?: string;
    problem?: any;
    candidate_code?: string;
    execution_result?: any;
    submission_history?: any[];
  }) => Promise<void>;

  analyzeSystemDesign: (params: {
    interview_id: string;
    workspace_id: string;
    session_id?: string;
    whiteboard_state?: any;
    candidate_explanation?: string;
    problem_statement?: string;
  }) => Promise<void>;

  fetchLogs: (workspaceId: string, interviewId?: string) => Promise<void>;
}

export const useAIStore = create<AIStoreState>((set, get) => ({
  isOpen: false,
  activeTab: 'adaptive',
  isLoading: false,
  error: null,
  lastMetadata: null,

  adaptiveRecommendation: null,
  recommendationHistory: [],
  coverageMatrix: null,
  liveTranscript: [],
  contextRevision: 1,

  currentQuestion: null,
  questionHistory: [],
  currentFollowUp: null,
  followUpHistory: [],
  resumeAnalysis: null,
  codingAnalysis: null,
  systemDesignAnalysis: null,
  logs: [],

  setIsOpen: (open) => set({ isOpen: open }),
  toggleIsOpen: () => set((state) => ({ isOpen: !state.isOpen })),
  setActiveTab: (tab) => set({ activeTab: tab }),
  clearError: () => set({ error: null }),

  fetchAdaptiveState: async (interviewId: string) => {
    try {
      const [recs, cov, trans] = await Promise.all([
        aiApi.getAdaptiveRecommendations(interviewId).catch(() => []),
        aiApi.getLiveCoverage(interviewId).catch(() => null),
        aiApi.getTranscripts(interviewId).catch(() => []),
      ]);

      set({
        recommendationHistory: recs || [],
        adaptiveRecommendation: recs && recs.length > 0 ? recs[0] : null,
        coverageMatrix: cov,
        liveTranscript: trans || [],
      });
    } catch (err) {
      console.error('Failed to fetch adaptive state', err);
    }
  },

  generateAdaptiveRecommendation: async (interviewId, params) => {
    set({ isLoading: true, error: null });
    try {
      const rec = await aiApi.generateAdaptiveRecommendation(interviewId, params);
      set((state) => ({
        adaptiveRecommendation: rec,
        recommendationHistory: [rec, ...state.recommendationHistory],
        isLoading: false,
      }));
    } catch (err: any) {
      set({
        error: err?.message || 'Error generating adaptive recommendation',
        isLoading: false,
      });
    }
  },

  acceptAdaptiveRecommendation: async (interviewId, recId) => {
    try {
      const updated = await aiApi.acceptAdaptiveRecommendation(interviewId, recId);
      set((state) => ({
        adaptiveRecommendation: updated,
        recommendationHistory: state.recommendationHistory.map((r) =>
          r.id === recId ? updated : r
        ),
      }));
    } catch (err: any) {
      set({ error: err?.message || 'Error accepting recommendation' });
    }
  },

  editAdaptiveRecommendation: async (interviewId, recId, editedQuestion) => {
    try {
      const updated = await aiApi.editAdaptiveRecommendation(interviewId, recId, editedQuestion);
      set((state) => ({
        adaptiveRecommendation: updated,
        recommendationHistory: state.recommendationHistory.map((r) =>
          r.id === recId ? updated : r
        ),
      }));
    } catch (err: any) {
      set({ error: err?.message || 'Error editing recommendation' });
    }
  },

  rejectAdaptiveRecommendation: async (interviewId, recId, reason) => {
    try {
      const updated = await aiApi.rejectAdaptiveRecommendation(interviewId, recId, reason);
      set((state) => ({
        adaptiveRecommendation: updated,
        recommendationHistory: state.recommendationHistory.map((r) =>
          r.id === recId ? updated : r
        ),
      }));
    } catch (err: any) {
      set({ error: err?.message || 'Error rejecting recommendation' });
    }
  },

  skipAdaptiveRecommendation: async (interviewId, recId) => {
    try {
      const updated = await aiApi.skipAdaptiveRecommendation(interviewId, recId);
      set((state) => ({
        adaptiveRecommendation: updated,
        recommendationHistory: state.recommendationHistory.map((r) =>
          r.id === recId ? updated : r
        ),
      }));
    } catch (err: any) {
      set({ error: err?.message || 'Error skipping recommendation' });
    }
  },

  addTranscriptSegment: (segment) => {
    set((state) => ({
      liveTranscript: [...state.liveTranscript, segment],
    }));
  },


  generateQuestion: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const res = await aiApi.generateQuestion(params);
      if (res.output) {
        set((state) => ({
          currentQuestion: res.output,
          questionHistory: [res.output!, ...state.questionHistory],
          lastMetadata: res.metadata || null,
          isLoading: false,
        }));
      } else {
        set({
          error: res.error_message || 'Failed to generate question',
          isLoading: false,
        });
      }
    } catch (err: any) {
      set({
        error: err?.message || 'Error communicating with AI service',
        isLoading: false,
      });
    }
  },

  generateFollowUp: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const res = await aiApi.generateFollowUp(params);
      if (res.output) {
        set((state) => ({
          currentFollowUp: res.output,
          followUpHistory: [res.output!, ...state.followUpHistory],
          lastMetadata: res.metadata || null,
          isLoading: false,
        }));
      } else {
        set({
          error: res.error_message || 'Failed to generate follow-up',
          isLoading: false,
        });
      }
    } catch (err: any) {
      set({
        error: err?.message || 'Error communicating with AI service',
        isLoading: false,
      });
    }
  },

  analyzeResume: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const res = await aiApi.analyzeResume(params);
      if (res.output) {
        set({
          resumeAnalysis: res.output,
          lastMetadata: res.metadata || null,
          isLoading: false,
        });
      } else {
        set({
          error: res.error_message || 'Failed to analyze resume',
          isLoading: false,
        });
      }
    } catch (err: any) {
      set({
        error: err?.message || 'Error analyzing resume',
        isLoading: false,
      });
    }
  },

  analyzeCoding: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const res = await aiApi.analyzeCoding(params);
      if (res.output) {
        set({
          codingAnalysis: res.output,
          lastMetadata: res.metadata || null,
          isLoading: false,
        });
      } else {
        set({
          error: res.error_message || 'Failed to analyze coding',
          isLoading: false,
        });
      }
    } catch (err: any) {
      set({
        error: err?.message || 'Error analyzing code',
        isLoading: false,
      });
    }
  },

  analyzeSystemDesign: async (params) => {
    set({ isLoading: true, error: null });
    try {
      const res = await aiApi.analyzeSystemDesign(params);
      if (res.output) {
        set({
          systemDesignAnalysis: res.output,
          lastMetadata: res.metadata || null,
          isLoading: false,
        });
      } else {
        set({
          error: res.error_message || 'Failed to analyze system design',
          isLoading: false,
        });
      }
    } catch (err: any) {
      set({
        error: err?.message || 'Error analyzing whiteboard design',
        isLoading: false,
      });
    }
  },

  fetchLogs: async (workspaceId, interviewId) => {
    try {
      const logs = await aiApi.getLogs(workspaceId, interviewId);
      set({ logs });
    } catch (err: any) {
      console.error('Failed to fetch AI telemetry logs', err);
    }
  },
}));
