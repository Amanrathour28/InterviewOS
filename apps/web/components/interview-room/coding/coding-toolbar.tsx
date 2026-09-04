import {
  Play,
  Rocket,
  Lock,
  Unlock,
  History,
  Code2,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Loader2,
  BookOpen,
  Award,
} from 'lucide-react';
import { SUPPORTED_CODING_LANGUAGES } from '@interviewos/types';
import { useCodingStore } from '@/lib/stores/use-coding-store';

interface CodingToolbarProps {
  isInterviewer: boolean;
  onRunCode: () => void;
  onSubmitCode: () => void;
  onToggleLock: () => void;
  onOpenSnapshots: () => void;
  onResetCode: () => void;
  onOpenProblemDrawer?: () => void;
  onOpenAssessment?: () => void;
}

export const CodingToolbar: React.FC<CodingToolbarProps> = ({
  isInterviewer,
  onRunCode,
  onSubmitCode,
  onToggleLock,
  onOpenSnapshots,
  onResetCode,
  onOpenProblemDrawer,
  onOpenAssessment,
}) => {
  const {
    selectedLanguage,
    setSelectedLanguage,
    isEditorLocked,
    isRunning,
    executionJob,
  } = useCodingStore();

  const handleLanguageChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedLanguage(e.target.value);
  };

  const getStatusBadge = () => {
    if (isRunning) {
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
          <Loader2 className="w-3.5 h-3.5 animate-spin" />
          Running Sandbox...
        </span>
      );
    }
    if (executionJob?.result) {
      if (executionJob.result.status === 'passed') {
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Passed ({executionJob.result.duration_ms}ms)
          </span>
        );
      }
      return (
        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
          <AlertCircle className="w-3.5 h-3.5" />
          {executionJob.result.status.replace('_', ' ').toUpperCase()}
        </span>
      );
    }
    return null;
  };

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-2.5 bg-slate-900 border-b border-slate-800">
      {/* Left controls: Language Picker & Lock Indicator */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Code2 className="w-4 h-4 text-indigo-400" />
          <select
            value={selectedLanguage}
            onChange={handleLanguageChange}
            disabled={isEditorLocked && !isInterviewer}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-xs rounded-lg px-3 py-1.5 font-medium focus:ring-2 focus:ring-indigo-500 focus:outline-none transition-colors disabled:opacity-50"
          >
            {SUPPORTED_CODING_LANGUAGES.map((lang) => (
              <option key={lang.id} value={lang.id}>
                {lang.name}
              </option>
            ))}
          </select>
        </div>

        {/* Lock status banner for candidates */}
        {isEditorLocked ? (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-500/10 text-amber-300 border border-amber-500/30">
            <Lock className="w-3.5 h-3.5 text-amber-400" />
            Editor Locked
          </span>
        ) : (
          <span className="hidden sm:inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-[11px] font-medium bg-slate-800 text-slate-400">
            Live CRDT Active
          </span>
        )}

        {/* Execution status indicator */}
        {getStatusBadge()}
      </div>

      {/* Right controls: Actions */}
      <div className="flex items-center gap-2">
        {/* Reset starter code */}
        <button
          onClick={onResetCode}
          disabled={isRunning || (isEditorLocked && !isInterviewer)}
          title="Reset to starter template"
          className="p-1.5 text-slate-400 hover:text-slate-200 hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-40"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        {/* Snapshots History */}
        <button
          onClick={onOpenSnapshots}
          title="View Checkpoint History"
          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg transition-colors"
        >
          <History className="w-3.5 h-3.5 text-slate-400" />
          <span className="hidden md:inline">History</span>
        </button>

        {/* Problem Library Button (Interviewer Only) */}
        {isInterviewer && onOpenProblemDrawer && (
          <button
            onClick={onOpenProblemDrawer}
            title="Browse & Assign Coding Problem"
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-indigo-300 hover:text-white bg-indigo-950/60 hover:bg-indigo-900/80 border border-indigo-500/30 rounded-lg transition-colors"
          >
            <BookOpen className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden md:inline">Problems</span>
          </button>
        )}

        {/* Assessment Diagnostics (Interviewer Only) */}
        {isInterviewer && onOpenAssessment && (
          <button
            onClick={onOpenAssessment}
            title="View Candidate Assessment Diagnostics"
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium text-amber-300 hover:text-white bg-amber-950/60 hover:bg-amber-900/80 border border-amber-500/30 rounded-lg transition-colors"
          >
            <Award className="w-3.5 h-3.5 text-amber-400" />
            <span className="hidden md:inline">Assessment</span>
          </button>
        )}

        {/* Interviewer Lock Toggle */}
        {isInterviewer && (
          <button
            onClick={onToggleLock}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-all ${
              isEditorLocked
                ? 'bg-amber-500/20 text-amber-300 border-amber-500/40 hover:bg-amber-500/30'
                : 'bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700'
            }`}
          >
            {isEditorLocked ? (
              <>
                <Unlock className="w-3.5 h-3.5 text-amber-400" />
                Unlock Candidate
              </>
            ) : (
              <>
                <Lock className="w-3.5 h-3.5 text-slate-400" />
                Lock Candidate
              </>
            )}
          </button>
        )}

        {/* Run Code */}
        <button
          onClick={onRunCode}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-emerald-600 hover:bg-emerald-500 active:scale-95 disabled:opacity-50 disabled:pointer-events-none rounded-lg shadow-sm shadow-emerald-950/50 transition-all"
        >
          {isRunning ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5 fill-current" />
          )}
          <span>Run</span>
        </button>

        {/* Submit Solution */}
        <button
          onClick={onSubmitCode}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-500 active:scale-95 disabled:opacity-50 disabled:pointer-events-none rounded-lg shadow-sm shadow-indigo-950/50 transition-all"
        >
          <Rocket className="w-3.5 h-3.5" />
          <span>Submit</span>
        </button>
      </div>
    </div>
  );
};
