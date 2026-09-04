'use client';

import React, { useEffect, useState, useCallback } from 'react';
import { useCodingStore, CodingFile, CodingSnapshot } from '@/lib/stores/use-coding-store';
import { CodingToolbar } from './coding-toolbar';
import { FileTabs } from './file-tabs';
import { MonacoEditorPane } from './monaco-editor-pane';
import { ExecutionTerminal } from './execution-terminal';
import { SnapshotsDrawer } from './snapshots-drawer';
import { ProblemDescriptionPanel } from './problem-description-panel';
import { InterviewerProblemDrawer } from './interviewer-problem-drawer';
import { InterviewerAssessmentPanel } from './interviewer-assessment-panel';
import { RealtimeClient } from '@/lib/realtime/realtime-client';
import { getLanguageConfig } from '@interviewos/types';
import { apiClient } from '@/lib/api';
import { ChevronLeft, ChevronRight, BookOpen } from 'lucide-react';

interface CodingWorkspaceProps {
  sessionId: string;
  interviewId: string;
  isInterviewer: boolean;
  token?: string;
  realtimeClient: RealtimeClient | null;
}

export const CodingWorkspace: React.FC<CodingWorkspaceProps> = ({
  sessionId,
  interviewId,
  isInterviewer,
  token,
  realtimeClient,
}) => {
  const {
    codingSession,
    files,
    activeFileId,
    selectedLanguage,
    isEditorLocked,
    customInput,
    activeProblem,
    submissions,
    isProblemDrawerOpen,
    isInterviewerAssessmentOpen,
    setCodingSession,
    setIsEditorLocked,
    addFile,
    updateFileContent,
    deleteFile,
    setIsRunning,
    setExecutionJob,
    setSnapshots,
    setIsSnapshotsDrawerOpen,
    setSelectedLanguage,
    setActiveProblem,
    setSubmissions,
    addSubmission,
    setIsProblemDrawerOpen,
    setIsInterviewerAssessmentOpen,
    setTerminalTab,
  } = useCodingStore();

  const [isLoading, setIsLoading] = useState(true);
  const [terminalHeight, setTerminalHeight] = useState(220);
  const [isProblemPaneCollapsed, setIsProblemPaneCollapsed] = useState(false);

  // 1. Fetch or initialize coding session
  const fetchCodingSession = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiClient<any>(`/sessions/${sessionId}/coding`);
      setCodingSession(data);

      // Fetch active problem if assigned
      if (data.problem_id) {
        try {
          const probData = await apiClient<any>(`/coding/problems/${data.problem_id}`);
          setActiveProblem(probData);
        } catch (pErr) {
          console.error('Failed to fetch assigned problem:', pErr);
        }
      }

      // Fetch submission history
      try {
        const subsData = await apiClient<any[]>(`/coding/sessions/${data.id}/problems/submissions`);
        setSubmissions(subsData || []);
      } catch (sErr) {
        console.error('Failed to fetch submissions:', sErr);
      }
    } catch (err) {
      console.error('Failed to fetch coding session:', err);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, setCodingSession, setActiveProblem, setSubmissions]);

  // 2. Fetch snapshots
  const fetchSnapshots = useCallback(async () => {
    if (!codingSession) return;
    try {
      const data = await apiClient<any[]>(`/coding/sessions/${codingSession.id}/snapshots`);
      setSnapshots(data);
    } catch (err) {
      console.error('Failed to fetch snapshots:', err);
    }
  }, [codingSession, setSnapshots]);

  useEffect(() => {
    fetchCodingSession();
  }, [fetchCodingSession]);

  // 3. Setup realtime Socket.IO listener for live CRDT & events
  useEffect(() => {
    if (!realtimeClient) return;

    const socket = realtimeClient.getSocket();
    if (!socket) return;

    const handleYjsUpdate = (data: { fileId: string; update: string; senderUserId: string }) => {
      if (data.update && typeof data.update === 'string') {
        updateFileContent(data.fileId, data.update);
      }
    };

    const handleLockEvent = (data: { is_locked: boolean }) => {
      setIsEditorLocked(data.is_locked);
    };

    const handleProblemAssigned = async (data: { problem_id: string }) => {
      if (data.problem_id) {
        try {
          const probData = await apiClient<any>(`/coding/problems/${data.problem_id}`);
          setActiveProblem(probData);
          fetchCodingSession();
        } catch (err) {
          console.error('Failed to reload assigned problem:', err);
        }
      }
    };

    const handleSubmissionCreated = async () => {
      if (codingSession) {
        try {
          const subsData = await apiClient<any[]>(`/coding/sessions/${codingSession.id}/problems/submissions`);
          setSubmissions(subsData || []);
        } catch (err) {
          console.error('Failed to reload submissions:', err);
        }
      }
    };

    socket.on('coding_yjs_update', handleYjsUpdate);
    socket.on('coding_lock_state', handleLockEvent);
    socket.on('CODING_PROBLEM_ASSIGNED', handleProblemAssigned);
    socket.on('CODING_SUBMISSION_CREATED', handleSubmissionCreated);

    return () => {
      socket.off('coding_yjs_update', handleYjsUpdate);
      socket.off('coding_lock_state', handleLockEvent);
      socket.off('CODING_PROBLEM_ASSIGNED', handleProblemAssigned);
      socket.off('CODING_SUBMISSION_CREATED', handleSubmissionCreated);
    };
  }, [realtimeClient, codingSession, updateFileContent, setIsEditorLocked, setActiveProblem, fetchCodingSession, setSubmissions]);

  // 4. Handle code content edits
  const handleContentChange = (fileId: string, content: string) => {
    updateFileContent(fileId, content);

    // Emit live update over socket
    if (realtimeClient) {
      const socket = realtimeClient.getSocket();
      if (socket) {
        socket.emit('coding_yjs_update', {
          fileId,
          update: content,
          isLocked: isEditorLocked,
        });
      }
    }
  };

  // 5. Handle lock / unlock toggle
  const handleToggleLock = async () => {
    if (!codingSession || !isInterviewer) return;
    try {
      const newLocked = !isEditorLocked;
      await apiClient(`/coding/sessions/${codingSession.id}/lock`, {
        method: 'POST',
        body: JSON.stringify({ is_locked: newLocked }),
      });
      setIsEditorLocked(newLocked);
      realtimeClient?.getSocket()?.emit('dispatch_event', {
        event_type: newLocked ? 'CODE_EDITOR_LOCKED' : 'CODE_EDITOR_UNLOCKED',
        payload: { is_locked: newLocked },
      });
    } catch (err) {
      console.error('Failed to toggle lock:', err);
    }
  };

  // 6. Handle File CRUD
  const handleAddFile = async (path: string, name: string) => {
    if (!codingSession) return;
    try {
      const newFile = await apiClient<CodingFile>(`/coding/sessions/${codingSession.id}/files`, {
        method: 'POST',
        body: JSON.stringify({
          path,
          name,
          language: selectedLanguage,
          content: '',
        }),
      });
      addFile(newFile);
    } catch (err: any) {
      throw new Error(err.message || 'Failed to create file');
    }
  };

  const handleDeleteFile = async (fileId: string) => {
    try {
      await apiClient(`/coding/files/${fileId}`, {
        method: 'DELETE',
      });
      deleteFile(fileId);
    } catch (err) {
      console.error('Failed to delete file:', err);
    }
  };

  // 7. Handle Code Execution (Run)
  const handleRun = async () => {
    if (!codingSession) return;
    try {
      setIsRunning(true);
      setTerminalTab('console');
      const job = await apiClient<any>(`/coding/sessions/${codingSession.id}/execute`, {
        method: 'POST',
        body: JSON.stringify({
          language: selectedLanguage,
          files: files.map((f) => ({ path: f.path, name: f.name, language: f.language, content: f.content })),
          is_submission: false,
          custom_input: customInput || null,
        }),
      });
      setExecutionJob(job);
    } catch (err) {
      console.error('Execution failed:', err);
    } finally {
      setIsRunning(false);
    }
  };

  // 8. Handle Submission Submit
  const handleSubmit = async () => {
    if (!codingSession) return;
    try {
      setIsRunning(true);
      const sub = await apiClient<any>(`/coding/sessions/${codingSession.id}/problems/submit`, {
        method: 'POST',
        body: JSON.stringify({
          language: selectedLanguage,
          files: files.map((f) => ({ path: f.path, name: f.name, language: f.language, content: f.content })),
        }),
      });
      addSubmission(sub);
      setTerminalTab('submissions');

      realtimeClient?.dispatchEvent('CODING_SUBMISSION_CREATED', {
        session_id: codingSession.id,
        submission_id: sub.id,
        status: sub.status,
        score: sub.score,
      });
    } catch (err) {
      console.error('Submission failed:', err);
    } finally {
      setIsRunning(false);
    }
  };

  // 9. Reset starter code
  const handleResetStarter = () => {
    if (activeFileId) {
      const langConfig = getLanguageConfig(selectedLanguage);
      handleContentChange(activeFileId, langConfig.starterCode);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-slate-950 text-slate-400 text-xs">
        Loading Collaborative Workspace & Assessment...
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-slate-950 overflow-hidden select-none">
      {/* Top Toolbar */}
      <CodingToolbar
        isInterviewer={isInterviewer}
        onRunCode={handleRun}
        onSubmitCode={handleSubmit}
        onToggleLock={handleToggleLock}
        onOpenSnapshots={() => {
          fetchSnapshots();
          setIsSnapshotsDrawerOpen(true);
        }}
        onResetCode={handleResetStarter}
        onOpenProblemDrawer={() => setIsProblemDrawerOpen(true)}
        onOpenAssessment={() => setIsInterviewerAssessmentOpen(true)}
      />

      {/* Main Split Body: Left Problem Description / Right Monaco Editor */}
      <div className="flex-1 flex overflow-hidden">
        {/* Problem Description Pane */}
        <div
          className={`border-r border-slate-800 bg-slate-950/80 transition-all duration-200 flex flex-col ${
            isProblemPaneCollapsed ? 'w-10' : 'w-80 lg:w-96'
          }`}
        >
          <div className="p-2 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
            {!isProblemPaneCollapsed && (
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-300">
                <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
                <span>Problem Statement</span>
              </div>
            )}
            <button
              onClick={() => setIsProblemPaneCollapsed(!isProblemPaneCollapsed)}
              className="p-1 text-slate-400 hover:text-white rounded ml-auto"
              title={isProblemPaneCollapsed ? 'Expand Problem' : 'Collapse Problem'}
            >
              {isProblemPaneCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>

          {!isProblemPaneCollapsed && (
            <div className="flex-1 overflow-hidden">
              <ProblemDescriptionPanel problem={activeProblem} />
            </div>
          )}
        </div>

        {/* Center & Terminal Workspace */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Multi-file Tab Strip */}
          <FileTabs
            isLocked={isEditorLocked && !isInterviewer}
            onAddFile={handleAddFile}
            onDeleteFile={handleDeleteFile}
          />

          {/* Monaco Editor Pane */}
          <div className="flex-1 relative overflow-hidden">
            <MonacoEditorPane
              isInterviewer={isInterviewer}
              onContentChange={handleContentChange}
            />
          </div>

          {/* Bottom Terminal & Assessment Tab */}
          <div style={{ height: `${terminalHeight}px` }} className="shrink-0">
            <ExecutionTerminal />
          </div>
        </div>
      </div>

      {/* Slide-over Drawers */}
      <SnapshotsDrawer />

      {codingSession && (
        <InterviewerProblemDrawer
          isOpen={isProblemDrawerOpen}
          onClose={() => setIsProblemDrawerOpen(false)}
          sessionId={codingSession.id}
          realtimeClient={realtimeClient}
          onProblemAssigned={fetchCodingSession}
        />
      )}

      <InterviewerAssessmentPanel
        isOpen={isInterviewerAssessmentOpen}
        onClose={() => setIsInterviewerAssessmentOpen(false)}
        problem={activeProblem}
        submissions={submissions}
      />
    </div>
  );
};
