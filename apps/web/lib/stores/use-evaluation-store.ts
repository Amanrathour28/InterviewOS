/**
 * Evaluation Zustand Store — Phase 15.
 */

import { create } from 'zustand';
import {
  EvaluationData,
  EvaluationEvidenceData,
  EvaluationReportData,
} from '@interviewos/types';
import { evaluationApi } from '../api/evaluation';

interface EvaluationStoreState {
  evaluation: EvaluationData | null;
  evidenceItems: EvaluationEvidenceData[];
  report: EvaluationReportData | null;
  isLoading: boolean;
  isGenerating: boolean;
  error: string | null;
  selectedEvidenceId: string | null;
  isEvidenceDrawerOpen: boolean;
  activeEvidenceFilter: string;

  // Actions
  fetchEvaluation: (interviewId: string) => Promise<void>;
  generateEvaluation: (interviewId: string, sessionId?: string) => Promise<void>;
  fetchEvidence: (interviewId: string) => Promise<void>;
  overrideScore: (
    interviewId: string,
    competencyScoreId: string,
    newRubricLevel: number,
    rationale: string
  ) => Promise<void>;
  approveEvaluation: (interviewId: string) => Promise<void>;
  finalizeEvaluation: (interviewId: string) => Promise<void>;
  fetchReport: (interviewId: string) => Promise<void>;
  setSelectedEvidenceId: (id: string | null) => void;
  setIsEvidenceDrawerOpen: (open: boolean) => void;
  setActiveEvidenceFilter: (filter: string) => void;
  clearError: () => void;
}

export const useEvaluationStore = create<EvaluationStoreState>((set, get) => ({
  evaluation: null,
  evidenceItems: [],
  report: null,
  isLoading: false,
  isGenerating: false,
  error: null,
  selectedEvidenceId: null,
  isEvidenceDrawerOpen: false,
  activeEvidenceFilter: 'all',

  fetchEvaluation: async (interviewId: string) => {
    set({ isLoading: true, error: null });
    try {
      const evaluation = await evaluationApi.getEvaluation(interviewId);
      set({ evaluation, isLoading: false });
    } catch (err: any) {
      set({ error: err?.message || 'Failed to fetch evaluation', isLoading: false });
    }
  },

  generateEvaluation: async (interviewId: string, sessionId?: string) => {
    set({ isGenerating: true, error: null });
    try {
      const evaluation = await evaluationApi.generateEvaluation(interviewId, sessionId);
      const evidence = await evaluationApi.getEvaluationEvidence(interviewId);
      set({ evaluation, evidenceItems: evidence, isGenerating: false });
    } catch (err: any) {
      set({ error: err?.message || 'Failed to generate evaluation', isGenerating: false });
    }
  },

  fetchEvidence: async (interviewId: string) => {
    try {
      const evidence = await evaluationApi.getEvaluationEvidence(interviewId);
      set({ evidenceItems: evidence });
    } catch (err: any) {
      console.error('Failed to fetch evidence items', err);
    }
  },

  overrideScore: async (interviewId, competencyScoreId, newRubricLevel, rationale) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await evaluationApi.overrideScore(
        interviewId,
        competencyScoreId,
        newRubricLevel,
        rationale
      );
      set({ evaluation: updated, isLoading: false });
    } catch (err: any) {
      set({ error: err?.message || 'Failed to override score', isLoading: false });
    }
  },

  approveEvaluation: async (interviewId: string) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await evaluationApi.approveEvaluation(interviewId);
      set({ evaluation: updated, isLoading: false });
    } catch (err: any) {
      set({ error: err?.message || 'Failed to approve evaluation', isLoading: false });
    }
  },

  finalizeEvaluation: async (interviewId: string) => {
    set({ isLoading: true, error: null });
    try {
      const finalized = await evaluationApi.finalizeEvaluation(interviewId);
      set({ evaluation: finalized, isLoading: false });
    } catch (err: any) {
      set({ error: err?.message || 'Failed to finalize evaluation', isLoading: false });
    }
  },

  fetchReport: async (interviewId: string) => {
    set({ isLoading: true, error: null });
    try {
      const report = await evaluationApi.getEvaluationReport(interviewId);
      set({ report, evaluation: report.evaluation, evidenceItems: report.evidence_items, isLoading: false });
    } catch (err: any) {
      set({ error: err?.message || 'Failed to load report', isLoading: false });
    }
  },

  setSelectedEvidenceId: (id) => set({ selectedEvidenceId: id, isEvidenceDrawerOpen: Boolean(id) }),
  setIsEvidenceDrawerOpen: (open) => set({ isEvidenceDrawerOpen: open }),
  setActiveEvidenceFilter: (filter) => set({ activeEvidenceFilter: filter }),
  clearError: () => set({ error: null }),
}));
