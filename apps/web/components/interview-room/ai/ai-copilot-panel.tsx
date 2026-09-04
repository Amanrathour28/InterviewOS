'use client';

import React, { useState } from 'react';
import {
  Sparkles,
  X,
  RefreshCw,
  Copy,
  Check,
  Brain,
  HelpCircle,
  FileText,
  Code,
  Layout,
  Activity,
  AlertCircle,
  CheckCircle2,
  Clock,
  Shield,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { useAIStore, AICopilotTab } from '@/lib/stores/use-ai-store';

interface AICopilotPanelProps {
  interviewId: string;
  workspaceId: string;
  sessionId?: string;
  currentStage?: string;
  onClose: () => void;
  onInsertNote?: (text: string, category: string) => void;
}

export const AICopilotPanel: React.FC<AICopilotPanelProps> = ({
  interviewId,
  workspaceId,
  sessionId,
  currentStage,
  onClose,
  onInsertNote,
}) => {
  const {
    activeTab,
    setActiveTab,
    isLoading,
    error,
    clearError,
    lastMetadata,
    adaptiveRecommendation,
    recommendationHistory,
    coverageMatrix,
    liveTranscript,
    fetchAdaptiveState,
    generateAdaptiveRecommendation,
    acceptAdaptiveRecommendation,
    editAdaptiveRecommendation,
    rejectAdaptiveRecommendation,
    skipAdaptiveRecommendation,
    currentQuestion,
    generateQuestion,
    currentFollowUp,
    generateFollowUp,
    resumeAnalysis,
    analyzeResume,
    codingAnalysis,
    analyzeCoding,
    systemDesignAnalysis,
    analyzeSystemDesign,
    logs,
    fetchLogs,
  } = useAIStore();

  // Load adaptive state on mount
  React.useEffect(() => {
    fetchAdaptiveState(interviewId);
  }, [interviewId, fetchAdaptiveState]);

  // Adaptive recommendation editing state
  const [isEditingRec, setIsEditingRec] = useState(false);
  const [editedText, setEditedText] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [isRejecting, setIsRejecting] = useState(false);

  // Question generator inputs
  const [difficulty, setDifficulty] = useState('medium');
  const [questionType, setQuestionType] = useState('technical');
  const [topicFocus, setTopicFocus] = useState('');

  // Follow-up inputs
  const [questionAsked, setQuestionAsked] = useState('');
  const [candidateAnswer, setCandidateAnswer] = useState('');

  // Copy feedback state
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  const handleCopy = (key: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleGenerateQuestion = () => {
    clearError();
    generateQuestion({
      interview_id: interviewId,
      workspace_id: workspaceId,
      difficulty,
      question_type: questionType,
      topic_focus: topicFocus.trim() || undefined,
      current_stage: currentStage,
    });
  };

  const handleGenerateFollowUp = () => {
    if (!questionAsked.trim() || !candidateAnswer.trim()) return;
    clearError();
    generateFollowUp({
      interview_id: interviewId,
      workspace_id: workspaceId,
      question_asked: questionAsked,
      candidate_answer: candidateAnswer,
      difficulty,
    });
  };

  const handleLoadLogs = () => {
    fetchLogs(workspaceId, interviewId);
  };

  return (
    <div className="flex flex-col h-full w-full bg-slate-950 text-slate-100 border-l border-slate-800 select-none">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-800 bg-slate-900/90 backdrop-blur">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-violet-600/20 text-violet-400 border border-violet-500/30">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-sm">AI Interview Copilot</span>
              <Badge variant="outline" className="text-[10px] px-1.5 py-0 border-violet-500/40 text-violet-300 bg-violet-500/10">
                Interviewer Only
              </Badge>
            </div>
            <p className="text-[11px] text-slate-400">Deterministic advisory & context intelligence</p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={onClose}
            className="p-1.5 rounded-md hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-slate-800 bg-slate-900/50 px-2 py-1 gap-1 overflow-x-auto scrollbar-none text-xs">
        <button
          onClick={() => setActiveTab('adaptive')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md transition-colors ${
            activeTab === 'adaptive'
              ? 'bg-violet-600 text-white font-medium'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Zap className="w-3.5 h-3.5" /> Adaptive Copilot
        </button>

        <button
          onClick={() => setActiveTab('questions')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md transition-colors ${
            activeTab === 'questions'
              ? 'bg-violet-600 text-white font-medium'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <HelpCircle className="w-3.5 h-3.5" /> Questions
        </button>

        <button
          onClick={() => setActiveTab('followups')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md transition-colors ${
            activeTab === 'followups'
              ? 'bg-violet-600 text-white font-medium'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Brain className="w-3.5 h-3.5" /> Follow-ups
        </button>

        <button
          onClick={() => setActiveTab('resume')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md transition-colors ${
            activeTab === 'resume'
              ? 'bg-violet-600 text-white font-medium'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <FileText className="w-3.5 h-3.5" /> Resume
        </button>

        <button
          onClick={() => setActiveTab('coding')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md transition-colors ${
            activeTab === 'coding'
              ? 'bg-violet-600 text-white font-medium'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Code className="w-3.5 h-3.5" /> Code Review
        </button>

        <button
          onClick={() => setActiveTab('whiteboard')}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md transition-colors ${
            activeTab === 'whiteboard'
              ? 'bg-violet-600 text-white font-medium'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Layout className="w-3.5 h-3.5" /> Architecture
        </button>

        <button
          onClick={() => {
            setActiveTab('logs');
            handleLoadLogs();
          }}
          className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md transition-colors ${
            activeTab === 'logs'
              ? 'bg-violet-600 text-white font-medium'
              : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
          }`}
        >
          <Activity className="w-3.5 h-3.5" /> Telemetry
        </button>
      </div>

      {/* Metadata bar */}
      {lastMetadata && (
        <div className="flex items-center justify-between px-3 py-1 bg-slate-900/70 border-b border-slate-800/60 text-[11px] text-slate-400">
          <div className="flex items-center gap-2">
            <span>
              Provider: <strong className="text-slate-300">{lastMetadata.provider}</strong>
            </span>
            <span>•</span>
            <span className="font-mono text-slate-300">{lastMetadata.model}</span>
            {lastMetadata.is_fallback && (
              <Badge className="text-[9px] bg-amber-500/20 text-amber-300 border-amber-500/30 px-1 py-0">
                Fallback
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 font-mono text-[10px]">
            <span>{lastMetadata.latency_ms}ms</span>
            {lastMetadata.tokens ? <span>{lastMetadata.tokens} tok</span> : null}
          </div>
        </div>
      )}

      {/* Error Alert */}
      {error && (
        <div className="m-3 p-2.5 rounded-md bg-rose-500/10 border border-rose-500/30 flex items-start gap-2 text-rose-300 text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div className="flex-1">{error}</div>
          <button onClick={clearError} className="hover:text-white">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Panel Body */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 text-xs select-text">
        {/* ================= Adaptive Copilot Tab (Phase 14) ================= */}
        {activeTab === 'adaptive' && (
          <div className="space-y-4">
            {/* Live AI Recommendation Card */}
            <div className="p-3.5 rounded-xl border border-violet-500/30 bg-gradient-to-b from-violet-950/20 to-slate-900/80 space-y-3 relative shadow-lg shadow-violet-950/20">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="font-semibold text-slate-200">AI Live Recommendation</span>
                  <Badge variant="outline" className="text-[10px] uppercase font-mono border-violet-500/40 text-violet-300 bg-violet-500/10">
                    {adaptiveRecommendation?.action?.replace(/_/g, ' ') || 'Watching Stream'}
                  </Badge>
                </div>
                {adaptiveRecommendation && (
                  <span className="text-[10px] text-slate-400 font-mono">
                    {Math.round(adaptiveRecommendation.confidence * 100)}% confidence
                  </span>
                )}
              </div>

              {adaptiveRecommendation?.status === 'stale' && (
                <div className="p-2 rounded bg-amber-500/10 border border-amber-500/30 text-amber-300 text-[11px] flex items-center gap-2">
                  <AlertCircle className="w-3.5 h-3.5 shrink-0" />
                  <span>Recommendation is stale due to new interview events. Generate a fresh probe.</span>
                </div>
              )}

              {adaptiveRecommendation ? (
                <div className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] bg-slate-800 text-slate-300 border-slate-700">
                      {adaptiveRecommendation.competency || 'Core Competency'}
                    </Badge>
                    <Badge variant="outline" className="text-[10px] bg-slate-800 text-slate-400 uppercase border-slate-700">
                      {adaptiveRecommendation.difficulty}
                    </Badge>
                    {adaptiveRecommendation.status === 'accepted' && (
                      <Badge className="text-[10px] bg-emerald-500/20 text-emerald-300 border-emerald-500/30">
                        <Check className="w-3 h-3 mr-1" /> Accepted
                      </Badge>
                    )}
                    {adaptiveRecommendation.status === 'edited' && (
                      <Badge className="text-[10px] bg-blue-500/20 text-blue-300 border-blue-500/30">
                        Edited & Asked
                      </Badge>
                    )}
                  </div>

                  {isEditingRec ? (
                    <div className="space-y-2">
                      <textarea
                        value={editedText}
                        onChange={(e) => setEditedText(e.target.value)}
                        rows={3}
                        className="w-full bg-slate-950 border border-violet-500 rounded p-2 text-xs text-slate-100 focus:outline-none focus:ring-1 focus:ring-violet-500"
                        placeholder="Edit question text before asking..."
                      />
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setIsEditingRec(false)}
                          className="h-7 text-xs text-slate-400 hover:text-white"
                        >
                          Cancel
                        </Button>
                        <Button
                          size="sm"
                          onClick={async () => {
                            if (!editedText.trim()) return;
                            await editAdaptiveRecommendation(interviewId, adaptiveRecommendation.id, editedText);
                            if (onInsertNote) onInsertNote(editedText, 'question');
                            setIsEditingRec(false);
                          }}
                          className="h-7 text-xs bg-violet-600 hover:bg-violet-500 text-white"
                        >
                          Save & Ask
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 text-slate-100 font-medium text-xs leading-relaxed">
                      &ldquo;{adaptiveRecommendation.recommended_question}&rdquo;
                    </div>
                  )}

                  <div className="space-y-1.5 text-[11px] text-slate-400 bg-slate-900/50 p-2.5 rounded-lg border border-slate-800/60">
                    <div>
                      <strong className="text-slate-300">Why: </strong>
                      {adaptiveRecommendation.reason}
                    </div>
                    {adaptiveRecommendation.evidence_target && (
                      <div>
                        <strong className="text-slate-300">Target Signal: </strong>
                        {adaptiveRecommendation.evidence_target}
                      </div>
                    )}
                  </div>

                  {/* Action Buttons */}
                  {adaptiveRecommendation.status !== 'accepted' && adaptiveRecommendation.status !== 'edited' && !isEditingRec && (
                    <div className="flex items-center gap-2 pt-1">
                      <Button
                        size="sm"
                        disabled={adaptiveRecommendation.status === 'stale'}
                        onClick={async () => {
                          await acceptAdaptiveRecommendation(interviewId, adaptiveRecommendation.id);
                          if (onInsertNote) onInsertNote(adaptiveRecommendation.recommended_question, 'question');
                          handleCopy('rec_copy', adaptiveRecommendation.recommended_question);
                        }}
                        className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white text-xs h-8 font-medium shadow-sm shadow-emerald-900/40"
                      >
                        <Check className="w-3.5 h-3.5 mr-1" /> Ask Follow-up
                      </Button>

                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          setEditedText(adaptiveRecommendation.recommended_question);
                          setIsEditingRec(true);
                        }}
                        className="border-slate-700 bg-slate-900 hover:bg-slate-800 text-slate-200 text-xs h-8"
                      >
                        Edit
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => skipAdaptiveRecommendation(interviewId, adaptiveRecommendation.id)}
                        className="text-slate-400 hover:text-slate-200 text-xs h-8"
                      >
                        Skip
                      </Button>

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => rejectAdaptiveRecommendation(interviewId, adaptiveRecommendation.id)}
                        className="text-rose-400 hover:text-rose-300 hover:bg-rose-500/10 text-xs h-8"
                      >
                        Reject
                      </Button>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-6 text-slate-400 space-y-2">
                  <Brain className="w-8 h-8 mx-auto text-slate-600 animate-pulse" />
                  <p className="text-xs">AI Interviewer is observing candidate audio & workspace signals.</p>
                </div>
              )}

              {/* Generate New Recommendation Trigger */}
              <div className="pt-2 border-t border-slate-800/60">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => generateAdaptiveRecommendation(interviewId, { competency_focus: topicFocus.trim() || undefined })}
                  disabled={isLoading}
                  className="w-full border-slate-800 bg-slate-900/90 hover:bg-slate-800 text-violet-300 text-xs h-8 font-medium"
                >
                  {isLoading ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Analyzing Context...
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-3.5 h-3.5 mr-1.5 text-violet-400" /> Trigger Adaptive Probe
                    </>
                  )}
                </Button>
              </div>
            </div>

            {/* Live Competency Coverage Tracker */}
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-slate-200">Competency Coverage</span>
                <span className="text-xs text-violet-400 font-mono font-semibold">
                  {coverageMatrix?.coverage_percentage || 0}%
                </span>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-violet-600 to-emerald-500 h-full transition-all duration-500 rounded-full"
                  style={{ width: `${coverageMatrix?.coverage_percentage || 0}%` }}
                />
              </div>

              <div className="space-y-1.5 pt-1">
                {coverageMatrix?.competencies && coverageMatrix.competencies.length > 0 ? (
                  coverageMatrix.competencies.map((c) => (
                    <div
                      key={c.id || c.competency}
                      className="flex items-center justify-between p-2 rounded-lg bg-slate-950/60 border border-slate-800/60 text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-slate-200">{c.competency}</span>
                        <span className="text-[10px] text-slate-500">({c.questions_asked_count} asked)</span>
                      </div>
                      <Badge
                        className={`text-[10px] px-1.5 py-0 capitalize ${
                          c.status === 'covered' || c.status === 'strong'
                            ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
                            : c.status === 'partial'
                            ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
                            : 'bg-slate-800 text-slate-400'
                        }`}
                      >
                        {c.status}
                      </Badge>
                    </div>
                  ))
                ) : (
                  <div className="text-[11px] text-slate-500 py-1 text-center">
                    Approved Question Plan competencies will track here in real time.
                  </div>
                )}
              </div>
            </div>

            {/* Live Transcript Stream */}
            <div className="p-3.5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-slate-400" />
                  <span className="font-semibold text-slate-200">Live Transcript Stream</span>
                </div>
                <span className="text-[10px] text-slate-400 font-mono">
                  {liveTranscript.length} segments
                </span>
              </div>

              <div className="space-y-2 max-h-48 overflow-y-auto pr-1 text-xs">
                {liveTranscript.length > 0 ? (
                  liveTranscript.map((t, idx) => (
                    <div
                      key={t.id || idx}
                      className={`p-2 rounded-lg border text-[11px] leading-relaxed ${
                        t.speaker_role === 'candidate'
                          ? 'bg-slate-950/80 border-slate-800 text-slate-200'
                          : 'bg-violet-950/20 border-violet-800/40 text-violet-200'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[9px] text-slate-500 font-mono mb-1">
                        <span className="uppercase font-semibold text-slate-400">{t.speaker_name || t.speaker_role}</span>
                        <span>{t.is_final ? 'Final' : 'Interim'}</span>
                      </div>
                      <p>{t.text}</p>
                    </div>
                  ))
                ) : (
                  <div className="text-[11px] text-slate-500 py-3 text-center">
                    Real-time speech transcript segments appear here as speech is detected.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ================= Questions Tab ================= */}
        {activeTab === 'questions' && (
          <div className="space-y-4">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 space-y-3">
              <div className="text-xs font-semibold text-slate-300">Question Generation Settings</div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] text-slate-400 uppercase font-medium">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    className="w-full mt-1 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:border-violet-500 focus:outline-none"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>
                <div>
                  <label className="text-[10px] text-slate-400 uppercase font-medium">Type</label>
                  <select
                    value={questionType}
                    onChange={(e) => setQuestionType(e.target.value)}
                    className="w-full mt-1 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 focus:border-violet-500 focus:outline-none"
                  >
                    <option value="technical">Technical</option>
                    <option value="system_design">System Design</option>
                    <option value="behavioral">Behavioral</option>
                    <option value="coding">Coding & Algorithms</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="text-[10px] text-slate-400 uppercase font-medium">Topic Focus (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. distributed caches, concurrency, SQL optimization"
                  value={topicFocus}
                  onChange={(e) => setTopicFocus(e.target.value)}
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 placeholder:text-slate-600 focus:border-violet-500 focus:outline-none"
                />
              </div>

              <Button
                onClick={handleGenerateQuestion}
                disabled={isLoading}
                className="w-full bg-violet-600 hover:bg-violet-500 text-white font-medium text-xs h-8"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Generating Question...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-3.5 h-3.5 mr-1.5" /> Generate Context-Aware Question
                  </>
                )}
              </Button>
            </div>

            {/* Generated Question Display */}
            {currentQuestion && (
              <div className="p-3.5 rounded-lg border border-violet-500/30 bg-violet-950/20 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="bg-violet-500/20 text-violet-300 border-violet-500/40 text-[10px]">
                      {currentQuestion.difficulty.toUpperCase()}
                    </Badge>
                    <Badge variant="outline" className="text-slate-300 border-slate-700 text-[10px]">
                      {currentQuestion.question_type}
                    </Badge>
                    <span className="text-[11px] text-slate-400 flex items-center gap-1">
                      <Clock className="w-3 h-3" /> ~{currentQuestion.suggested_time_minutes}m
                    </span>
                  </div>

                  <div className="flex items-center gap-1">
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleCopy('q', currentQuestion.question_text)}
                      className="h-6 px-2 text-[10px] text-slate-300 hover:text-white"
                    >
                      {copiedKey === 'q' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                    </Button>
                    {onInsertNote && (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => onInsertNote(currentQuestion.question_text, 'rubric')}
                        className="h-6 px-2 text-[10px] text-violet-400 hover:text-violet-300"
                        title="Add to Interviewer Notes"
                      >
                        + Note
                      </Button>
                    )}
                  </div>
                </div>

                <div className="font-medium text-sm text-slate-100 leading-snug">
                  {currentQuestion.question_text}
                </div>

                {/* Target Skills */}
                {currentQuestion.target_skills?.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {currentQuestion.target_skills.map((skill, idx) => (
                      <span key={idx} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px]">
                        {skill}
                      </span>
                    ))}
                  </div>
                )}

                {/* Rubric */}
                {currentQuestion.rubric && currentQuestion.rubric.length > 0 && (
                  <div className="space-y-1.5 pt-2 border-t border-slate-800/80">
                    <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                      Evaluation Rubric
                    </div>
                    {currentQuestion.rubric.map((r, idx) => (
                      <div key={idx} className="p-2 rounded bg-slate-900/80 border border-slate-800 text-[11px] space-y-1">
                        <strong className="text-violet-300">{r.criteria}</strong>
                        <div className="grid grid-cols-2 gap-1 text-[10px]">
                          <div className="text-emerald-300/90">
                            <strong>Exemplary:</strong> {r.level_4_exemplary}
                          </div>
                          <div className="text-blue-300/90">
                            <strong>Competent:</strong> {r.level_3_competent}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Follow-up Hooks */}
                {currentQuestion.follow_up_hooks?.length > 0 && (
                  <div className="space-y-1 pt-2 border-t border-slate-800/80">
                    <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                      Follow-Up Hooks to Watch For
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-300">
                      {currentQuestion.follow_up_hooks.map((hook, idx) => (
                        <li key={idx}>{hook}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ================= Follow-ups Tab ================= */}
        {activeTab === 'followups' && (
          <div className="space-y-4">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 space-y-3">
              <div className="text-xs font-semibold text-slate-300">Live Follow-Up Assistant</div>
              <div>
                <label className="text-[10px] text-slate-400 uppercase font-medium">Question Asked</label>
                <input
                  type="text"
                  placeholder="e.g. How does garbage collection work in V8?"
                  value={questionAsked}
                  onChange={(e) => setQuestionAsked(e.target.value)}
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 placeholder:text-slate-600 focus:border-violet-500 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] text-slate-400 uppercase font-medium">Candidate&apos;s Answer / Notes</label>
                <textarea
                  rows={3}
                  placeholder="Paste or summarize candidate's key points or vague areas..."
                  value={candidateAnswer}
                  onChange={(e) => setCandidateAnswer(e.target.value)}
                  className="w-full mt-1 bg-slate-950 border border-slate-800 rounded px-2 py-1 text-xs text-slate-200 placeholder:text-slate-600 focus:border-violet-500 focus:outline-none"
                />
              </div>

              <Button
                onClick={handleGenerateFollowUp}
                disabled={isLoading || !questionAsked.trim() || !candidateAnswer.trim()}
                className="w-full bg-violet-600 hover:bg-violet-500 text-white font-medium text-xs h-8"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Suggesting Follow-Ups...
                  </>
                ) : (
                  <>
                    <Brain className="w-3.5 h-3.5 mr-1.5" /> Suggest Drill-Down Follow-Up
                  </>
                )}
              </Button>
            </div>

            {/* Follow-Up Result */}
            {currentFollowUp && (
              <div className="p-3.5 rounded-lg border border-violet-500/30 bg-violet-950/20 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="bg-emerald-500/20 text-emerald-300 border-emerald-500/40 text-[10px]">
                      Recommended Drill-Down
                    </Badge>
                    <span className="text-[10px] text-slate-400">Target: {currentFollowUp.skill_targeted}</span>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleCopy('fu', currentFollowUp.primary_follow_up)}
                    className="h-6 px-2 text-[10px] text-slate-300"
                  >
                    {copiedKey === 'fu' ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                  </Button>
                </div>

                <div className="font-semibold text-sm text-slate-100">
                  {currentFollowUp.primary_follow_up}
                </div>

                <div className="text-[11px] text-slate-300 bg-slate-900/60 p-2 rounded border border-slate-800">
                  <strong className="text-violet-300">Why probe this:</strong> {currentFollowUp.purpose}
                </div>

                {currentFollowUp.alternative_angles?.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase tracking-wider font-semibold text-slate-400">
                      Alternative Probing Angles
                    </div>
                    <ul className="list-disc list-inside space-y-1 text-[11px] text-slate-300">
                      {currentFollowUp.alternative_angles.map((alt, idx) => (
                        <li key={idx}>{alt}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ================= Resume Tab ================= */}
        {activeTab === 'resume' && (
          <div className="space-y-3">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold text-slate-300">Resume & Experience Intelligence</div>
                <Button
                  size="sm"
                  onClick={() => analyzeResume({ interview_id: interviewId, workspace_id: workspaceId })}
                  disabled={isLoading}
                  className="bg-violet-600 hover:bg-violet-500 text-white text-[11px] h-7"
                >
                  <Sparkles className="w-3 h-3 mr-1" /> Analyze Profile
                </Button>
              </div>
              <p className="text-[11px] text-slate-400">
                Identifies claim verification questions, project deep-dives, and potential skill gaps.
              </p>
            </div>

            {resumeAnalysis && (
              <div className="space-y-3">
                {/* Verification Questions */}
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/50 space-y-2">
                  <div className="text-xs font-semibold text-violet-400 flex items-center gap-1.5">
                    <Shield className="w-3.5 h-3.5" /> Claim Depth Verification Questions
                  </div>
                  <div className="space-y-2">
                    {resumeAnalysis.depth_verification_questions?.map((item, idx) => (
                      <div key={idx} className="p-2 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                        <Badge variant="outline" className="text-[9px] px-1 text-slate-300 border-slate-700">
                          {item.topic}
                        </Badge>
                        <div className="text-xs font-medium text-slate-200">{item.question}</div>
                        <div className="text-[10px] text-slate-400">
                          <strong className="text-violet-300">Look for:</strong> {item.look_for}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Project Probes */}
                {resumeAnalysis.project_deep_dives?.length > 0 && (
                  <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/50 space-y-2">
                    <div className="text-xs font-semibold text-slate-300">Project Drill-Downs</div>
                    {resumeAnalysis.project_deep_dives.map((proj, idx) => (
                      <div key={idx} className="p-2 rounded bg-slate-950/60 border border-slate-800 space-y-1">
                        <strong className="text-violet-300 text-xs">{proj.project_name}</strong>
                        <p className="text-[11px] text-slate-300">{proj.suggested_scenario}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ================= Coding Tab ================= */}
        {activeTab === 'coding' && (
          <div className="space-y-3">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold text-slate-300">Automated Coding Analysis</div>
                <Button
                  size="sm"
                  onClick={() =>
                    analyzeCoding({
                      interview_id: interviewId,
                      workspace_id: workspaceId,
                      session_id: sessionId,
                    })
                  }
                  disabled={isLoading}
                  className="bg-violet-600 hover:bg-violet-500 text-white text-[11px] h-7"
                >
                  <Code className="w-3 h-3 mr-1" /> Review Code
                </Button>
              </div>
              <p className="text-[11px] text-slate-400">
                Evaluates time/space complexity, edge cases, code smells, and hints. Authoritative sandbox execution results are preserved.
              </p>
            </div>

            {codingAnalysis && (
              <div className="p-3.5 rounded-lg border border-violet-500/30 bg-violet-950/20 space-y-3">
                <div className="grid grid-cols-2 gap-2">
                  <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Time Complexity</div>
                    <div className="font-mono text-sm text-emerald-400 font-semibold">
                      {codingAnalysis.time_complexity}
                    </div>
                  </div>
                  <div className="p-2 rounded bg-slate-900/80 border border-slate-800">
                    <div className="text-[10px] text-slate-400 uppercase">Space Complexity</div>
                    <div className="font-mono text-sm text-cyan-400 font-semibold">
                      {codingAnalysis.space_complexity}
                    </div>
                  </div>
                </div>

                {codingAnalysis.edge_cases_unhandled?.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase font-semibold text-amber-400 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> Unhandled Edge Cases
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-300">
                      {codingAnalysis.edge_cases_unhandled.map((ec, idx) => (
                        <li key={idx}>{ec}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {codingAnalysis.suggested_hints?.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase font-semibold text-violet-300 flex items-center gap-1">
                      <Zap className="w-3 h-3" /> Progressive Hints for Candidate
                    </div>
                    <div className="space-y-1">
                      {codingAnalysis.suggested_hints.map((hint, idx) => (
                        <div key={idx} className="p-1.5 rounded bg-slate-900/90 border border-slate-800 text-[11px] text-slate-200">
                          <strong>Hint {idx + 1}:</strong> {hint}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ================= Whiteboard Tab ================= */}
        {activeTab === 'whiteboard' && (
          <div className="space-y-3">
            <div className="p-3 rounded-lg border border-slate-800 bg-slate-900/60 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-xs font-semibold text-slate-300">System Design Whiteboard Review</div>
                <Button
                  size="sm"
                  onClick={() =>
                    analyzeSystemDesign({
                      interview_id: interviewId,
                      workspace_id: workspaceId,
                      session_id: sessionId,
                    })
                  }
                  disabled={isLoading}
                  className="bg-violet-600 hover:bg-violet-500 text-white text-[11px] h-7"
                >
                  <Layout className="w-3 h-3 mr-1" /> Analyze Design
                </Button>
              </div>
              <p className="text-[11px] text-slate-400">
                Inspects canvas elements, single points of failure, scaling bottlenecks, and drill-down critiques.
              </p>
            </div>

            {systemDesignAnalysis && (
              <div className="p-3.5 rounded-lg border border-violet-500/30 bg-violet-950/20 space-y-3">
                <div className="flex items-center gap-2">
                  <Badge variant="outline" className="border-violet-500/40 text-violet-300 bg-violet-500/10">
                    Style: {systemDesignAnalysis.architecture_style}
                  </Badge>
                </div>

                {systemDesignAnalysis.single_points_of_failure?.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase font-semibold text-rose-400 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" /> Single Points of Failure
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-300">
                      {systemDesignAnalysis.single_points_of_failure.map((spof, idx) => (
                        <li key={idx}>{spof}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {systemDesignAnalysis.targeted_critique_questions?.length > 0 && (
                  <div className="space-y-1">
                    <div className="text-[10px] uppercase font-semibold text-violet-300">
                      Targeted Architecture Critiques
                    </div>
                    <ul className="list-disc list-inside space-y-0.5 text-[11px] text-slate-200">
                      {systemDesignAnalysis.targeted_critique_questions.map((q, idx) => (
                        <li key={idx}>{q}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ================= Telemetry Logs Tab ================= */}
        {activeTab === 'logs' && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs font-semibold text-slate-300">AI Request Audit Log</div>
              <Button
                size="sm"
                variant="ghost"
                onClick={handleLoadLogs}
                className="text-xs h-7 text-slate-400 hover:text-white"
              >
                <RefreshCw className="w-3 h-3 mr-1" /> Refresh
              </Button>
            </div>

            <div className="space-y-1.5">
              {logs.length === 0 ? (
                <div className="text-center py-6 text-slate-500 text-xs">No AI requests logged yet</div>
              ) : (
                logs.map((log) => (
                  <div
                    key={log.id}
                    className="p-2 rounded bg-slate-900/80 border border-slate-800 text-[11px] space-y-1 font-mono"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1.5">
                        {log.success ? (
                          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                        ) : (
                          <AlertCircle className="w-3 h-3 text-rose-400" />
                        )}
                        <span className="text-slate-200 font-sans font-medium">{log.task_type || log.agent_name}</span>
                        {log.is_fallback && (
                          <Badge className="text-[9px] bg-amber-500/20 text-amber-300 border-amber-500/30 px-1 py-0">
                            fallback
                          </Badge>
                        )}
                      </div>
                      <span className="text-slate-400 text-[10px]">{log.latency_ms}ms</span>
                    </div>
                    <div className="text-[10px] text-slate-400 flex items-center justify-between">
                      <span>
                        {log.provider} • {log.model}
                      </span>
                      <span>{log.total_tokens} tokens</span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
