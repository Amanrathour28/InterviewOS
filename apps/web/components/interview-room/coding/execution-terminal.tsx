'use client';

import React from 'react';
import {
  Terminal as TerminalIcon,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Trash2,
  Sliders,
  Play,
  Cpu,
  FileText,
} from 'lucide-react';
import { useCodingStore } from '@/lib/stores/use-coding-store';
import { SubmissionHistoryPanel } from './submission-history-panel';

interface ExecutionTerminalProps {
  onRunCustomInput?: () => void;
}

export const ExecutionTerminal: React.FC<ExecutionTerminalProps> = ({ onRunCustomInput }) => {
  const {
    executionJob,
    isRunning,
    terminalTab,
    setTerminalTab,
    customInput,
    setCustomInput,
    setExecutionJob,
    submissions,
  } = useCodingStore();

  const result = executionJob?.result;

  return (
    <div className="flex flex-col h-full bg-slate-950 border-t border-slate-800 text-slate-300 font-mono text-xs">
      {/* Header Tabs */}
      <div className="flex items-center justify-between px-3 py-2 bg-slate-900/90 border-b border-slate-800">
        <div className="flex items-center gap-2">
          {/* Console Tab */}
          <button
            onClick={() => setTerminalTab('console')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              terminalTab === 'console'
                ? 'bg-slate-800 text-indigo-400 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <TerminalIcon className="w-3.5 h-3.5" />
            <span>Output</span>
          </button>

          {/* Test Cases Tab */}
          <button
            onClick={() => setTerminalTab('tests')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              terminalTab === 'tests'
                ? 'bg-slate-800 text-indigo-400 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Test Cases</span>
            {result && (
              <span
                className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                  result.tests_failed === 0
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'bg-rose-500/20 text-rose-400'
                }`}
              >
                {result.tests_passed}/{result.tests_passed + result.tests_failed}
              </span>
            )}
          </button>

          {/* Custom Input Tab */}
          <button
            onClick={() => setTerminalTab('custom_input')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              terminalTab === 'custom_input'
                ? 'bg-slate-800 text-indigo-400 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <Sliders className="w-3.5 h-3.5" />
            <span>Custom Stdin</span>
            {customInput && (
              <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
            )}
          </button>

          {/* Submissions Tab */}
          <button
            onClick={() => setTerminalTab('submissions')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-md text-xs font-medium transition-colors ${
              terminalTab === 'submissions'
                ? 'bg-slate-800 text-indigo-400 shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            <FileText className="w-3.5 h-3.5" />
            <span>Submissions</span>
            {submissions.length > 0 && (
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold bg-indigo-500/20 text-indigo-300 font-mono">
                {submissions.length}
              </span>
            )}
          </button>
        </div>

        {/* Stats & Clear */}
        <div className="flex items-center gap-3">
          {result?.duration_ms !== undefined && (
            <span className="flex items-center gap-1 text-[11px] text-slate-400 font-sans">
              <Clock className="w-3 h-3 text-slate-500" />
              {result.duration_ms}ms
            </span>
          )}

          <button
            onClick={() => setExecutionJob(null)}
            title="Clear Output"
            className="p-1 text-slate-500 hover:text-slate-300 hover:bg-slate-800 rounded transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Tab Body */}
      <div className="flex-1 p-3 overflow-y-auto font-mono text-xs select-text">
        {/* TAB 1: Console Output */}
        {terminalTab === 'console' && (
          <div>
            {isRunning ? (
              <div className="flex items-center gap-2 text-amber-400 animate-pulse">
                <Cpu className="w-4 h-4 animate-spin" />
                <span>[Sandbox] Executing in isolated container (--network none)...</span>
              </div>
            ) : result ? (
              <div className="space-y-3">
                {/* Status summary banner */}
                <div
                  className={`flex items-center justify-between p-2 rounded border text-xs ${
                    result.status === 'passed'
                      ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-300'
                      : result.status === 'compile_error'
                      ? 'bg-amber-950/40 border-amber-500/30 text-amber-300'
                      : 'bg-rose-950/40 border-rose-500/30 text-rose-300'
                  }`}
                >
                  <span className="font-semibold uppercase tracking-wider">
                    Verdict: {result.status.replace('_', ' ')}
                  </span>
                  <span>Exit Code: {result.exit_code ?? 0}</span>
                </div>

                {/* Compile output if present */}
                {result.compile_output && (
                  <div>
                    <div className="text-[11px] text-amber-400 font-semibold mb-1">Compiler Output:</div>
                    <pre className="p-2.5 bg-slate-900/80 border border-slate-800 rounded text-slate-300 whitespace-pre-wrap">
                      {result.compile_output}
                    </pre>
                  </div>
                )}

                {/* Stdout */}
                {result.stdout && (
                  <div>
                    <div className="text-[11px] text-slate-400 font-semibold mb-1">Standard Output:</div>
                    <pre className="p-2.5 bg-slate-900/80 border border-slate-800 rounded text-emerald-300 whitespace-pre-wrap">
                      {result.stdout}
                    </pre>
                  </div>
                )}

                {/* Stderr */}
                {result.stderr && (
                  <div>
                    <div className="text-[11px] text-rose-400 font-semibold mb-1">Standard Error:</div>
                    <pre className="p-2.5 bg-rose-950/30 border border-rose-800/40 rounded text-rose-300 whitespace-pre-wrap">
                      {result.stderr}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-slate-600 italic">
                Press &quot;Run&quot; to execute your code against test cases or custom input.
              </div>
            )}
          </div>
        )}

        {/* TAB 2: Test Cases */}
        {terminalTab === 'tests' && (
          <div>
            {result?.test_results && result.test_results.length > 0 ? (
              <div className="space-y-2">
                {result.test_results.map((tc, idx) => (
                  <div
                    key={tc.test_id || idx}
                    className={`p-3 rounded-lg border transition-all ${
                      tc.passed
                        ? 'bg-emerald-950/20 border-emerald-500/30 text-slate-200'
                        : 'bg-rose-950/20 border-rose-500/30 text-slate-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-2">
                        {tc.passed ? (
                          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                        ) : (
                          <XCircle className="w-4 h-4 text-rose-400 shrink-0" />
                        )}
                        <span className="font-semibold text-xs">
                          {tc.title} {tc.is_hidden && '(Hidden Test)'}
                        </span>
                      </div>
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase ${
                          tc.passed
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-rose-500/20 text-rose-400'
                        }`}
                      >
                        {tc.passed ? 'PASSED' : 'FAILED'}
                      </span>
                    </div>

                    {/* Test failure details */}
                    {!tc.passed && tc.error && (
                      <div className="mt-2 p-2 bg-slate-900 border border-slate-800 rounded text-rose-300 text-xs">
                        <span className="font-semibold">Error: </span>
                        {tc.error}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-slate-600 italic">
                No test evaluation results available. Run or Submit code to evaluate test cases.
              </div>
            )}
          </div>
        )}

        {/* TAB 3: Custom Input */}
        {terminalTab === 'custom_input' && (
          <div className="flex flex-col h-full space-y-2">
            <div className="text-xs text-slate-400">
              Provide custom text fed into stdin for your program:
            </div>
            <textarea
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="e.g. 10 20&#10;test input string"
              rows={4}
              className="w-full p-2.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-200 font-mono text-xs focus:ring-2 focus:ring-indigo-500 focus:outline-none resize-none"
            />
          </div>
        )}

        {/* TAB 4: Submissions */}
        {terminalTab === 'submissions' && (
          <div className="h-full">
            <SubmissionHistoryPanel submissions={submissions} />
          </div>
        )}
      </div>
    </div>
  );
};
