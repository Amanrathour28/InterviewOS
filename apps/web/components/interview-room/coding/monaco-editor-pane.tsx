'use client';

import React, { useRef, useEffect } from 'react';
import Editor, { OnMount, OnChange } from '@monaco-editor/react';
import { Lock, FileQuestion } from 'lucide-react';
import { getLanguageConfig } from '@interviewos/types';
import { useCodingStore } from '@/lib/stores/use-coding-store';

interface MonacoEditorPaneProps {
  isInterviewer: boolean;
  onContentChange: (fileId: string, content: string) => void;
  onCursorChange?: (fileId: string, cursor: any) => void;
}

export const MonacoEditorPane: React.FC<MonacoEditorPaneProps> = ({
  isInterviewer,
  onContentChange,
  onCursorChange,
}) => {
  const { files, activeFileId, isEditorLocked, selectedLanguage } = useCodingStore();
  const editorRef = useRef<any>(null);

  const activeFile = files.find((f) => f.id === activeFileId) || files[0];

  const langConfig = getLanguageConfig(selectedLanguage);
  const monacoLanguage = langConfig.monacoLanguage || 'python';

  const isReadOnly = isEditorLocked && !isInterviewer;

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Track cursor changes
    editor.onDidChangeCursorPosition((e: any) => {
      if (activeFile && onCursorChange) {
        onCursorChange(activeFile.id, {
          lineNumber: e.position.lineNumber,
          column: e.position.column,
        });
      }
    });
  };

  const handleEditorChange: OnChange = (value) => {
    if (activeFile && value !== undefined) {
      onContentChange(activeFile.id, value);
    }
  };

  if (!activeFile) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-500 bg-slate-950 p-6">
        <FileQuestion className="w-10 h-10 mb-2 opacity-50" />
        <p className="text-sm">No active file open</p>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full flex flex-col bg-slate-950">
      {/* Editor Lock Overlay for candidates */}
      {isReadOnly && (
        <div className="absolute top-3 right-4 z-20 flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-950/80 border border-amber-500/30 text-amber-300 text-xs font-medium backdrop-blur shadow-lg pointer-events-none">
          <Lock className="w-3.5 h-3.5 text-amber-400" />
          <span>Editor Locked — Read Only Mode</span>
        </div>
      )}

      {/* Monaco React Editor */}
      <div className="flex-1 w-full h-full">
        <Editor
          height="100%"
          language={monacoLanguage}
          value={activeFile.content}
          theme="vs-dark"
          onMount={handleEditorDidMount}
          onChange={handleEditorChange}
          options={{
            readOnly: isReadOnly,
            fontSize: 14,
            fontFamily: "'JetBrains Mono', 'Fira Code', 'Menlo', 'Monaco', monospace",
            minimap: { enabled: true, scale: 0.75 },
            scrollBeyondLastLine: false,
            automaticLayout: true,
            tabSize: 4,
            wordWrap: 'on',
            lineNumbers: 'on',
            renderLineHighlight: 'all',
            bracketPairColorization: { enabled: true },
            cursorBlinking: 'smooth',
            cursorSmoothCaretAnimation: 'on',
            smoothScrolling: true,
            padding: { top: 12, bottom: 12 },
          }}
          loading={
            <div className="flex items-center justify-center h-full bg-slate-950 text-slate-400 text-xs">
              Initializing Monaco Editor...
            </div>
          }
        />
      </div>
    </div>
  );
};
