/**
 * Evaluation API Client — Phase 15.
 */

import { apiClient } from '@/lib/api';
import {
  EvaluationData,
  EvaluationEvidenceData,
  EvaluationReportData,
} from '@interviewos/types';

export const evaluationApi = {
  /**
   * Generates or regenerates an AI evidence-grounded evaluation.
   */
  generateEvaluation: (interviewId: string, sessionId?: string): Promise<EvaluationData> => {
    return apiClient<EvaluationData>(`/interviews/${interviewId}/evaluation/generate`, {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId }),
    });
  },

  /**
   * Fetches the current evaluation for an interview.
   */
  getEvaluation: (interviewId: string): Promise<EvaluationData> => {
    return apiClient<EvaluationData>(`/interviews/${interviewId}/evaluation`, {
      method: 'GET',
    });
  },

  /**
   * Fetches all aggregated evidence items for an interview.
   */
  getEvaluationEvidence: (interviewId: string): Promise<EvaluationEvidenceData[]> => {
    return apiClient<EvaluationEvidenceData[]>(`/interviews/${interviewId}/evaluation/evidence`, {
      method: 'GET',
    });
  },

  /**
   * Overrides a competency rubric score with mandatory reason.
   */
  overrideScore: (
    interviewId: string,
    competencyScoreId: string,
    newRubricLevel: number,
    rationale: string
  ): Promise<EvaluationData> => {
    return apiClient<EvaluationData>(
      `/interviews/${interviewId}/evaluation/competencies/${competencyScoreId}`,
      {
        method: 'PATCH',
        body: JSON.stringify({
          new_rubric_level: newRubricLevel,
          rationale: rationale,
        }),
      }
    );
  },

  /**
   * Approves the evaluation draft.
   */
  approveEvaluation: (interviewId: string): Promise<EvaluationData> => {
    return apiClient<EvaluationData>(`/interviews/${interviewId}/evaluation/approve`, {
      method: 'POST',
    });
  },

  /**
   * Finalizes and seals the evaluation into an immutable state.
   */
  finalizeEvaluation: (interviewId: string): Promise<EvaluationData> => {
    return apiClient<EvaluationData>(`/interviews/${interviewId}/evaluation/finalize`, {
      method: 'POST',
    });
  },

  /**
   * Fetches the full assembled interview evaluation report.
   */
  getEvaluationReport: (interviewId: string): Promise<EvaluationReportData> => {
    return apiClient<EvaluationReportData>(`/interviews/${interviewId}/evaluation/report`, {
      method: 'GET',
    });
  },
};
