import { create } from 'zustand';

export interface CodingFile {
  id: string;
  coding_session_id: string;
  path: string;
  name: string;
  language: string;
  content: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TestResultItem {
  test_id?: string;
  title: string;
  passed: boolean;
  duration_ms?: number;
  error?: string;
  stdout?: string;
  is_hidden?: boolean;
}

export interface CodingExecutionResult {
  id: string;
  execution_job_id: string;
  status: string;
  exit_code?: number;
  stdout: string;
  stderr: string;
  compile_output?: string;
  duration_ms?: number;
  memory_bytes?: number;
  tests_passed: number;
  tests_failed: number;
  test_results: TestResultItem[];
  created_at: string;
}

export interface CodingExecutionJob {
  id: string;
  coding_session_id: string;
  requested_by?: string;
  snapshot_id: string;
  status: string;
  language: string;
  is_submission: boolean;
  custom_input?: string;
  result?: CodingExecutionResult;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface CodingSnapshot {
  id: string;
  coding_session_id: string;
  created_by?: string;
  reason: string;
  files: Array<{ path: string; name: string; language: string; content: string }>;
  created_at: string;
}

export interface TestCase {
  id: string;
  problem_version_id?: string;
  title: string;
  input_data?: string | null;
  expected_output?: string | null;
  explanation?: string | null;
  is_hidden: boolean;
  weight: number;
  order: number;
  timeout_seconds: number;
}

export interface ProblemVersion {
  id: string;
  problem_id: string;
  version_number: number;
  problem_statement: string;
  examples: Array<{ input: string; output: string; explanation?: string }>;
  constraints: string[];
  expected_time_complexity?: string | null;
  expected_space_complexity?: string | null;
  starter_codes: Record<string, string>;
  scoring_policy: Record<string, any>;
  time_limit_seconds: number;
  memory_limit_mb: number;
  test_cases: TestCase[];
  created_at: string;
}

export interface ProblemDetail {
  id: string;
  workspace_id?: string | null;
  created_by?: string | null;
  title: string;
  slug: string;
  short_description: string;
  difficulty: 'easy' | 'medium' | 'hard';
  category: string;
  status: string;
  estimated_duration_minutes: number;
  default_time_limit_seconds: number;
  default_memory_limit_mb: number;
  tags: string[];
  is_system: boolean;
  current_version_id?: string | null;
  current_version?: ProblemVersion | null;
  versions_count: number;
  created_at: string;
  updated_at: string;
}

export interface SubmissionItem {
  id: string;
  coding_session_id: string;
  session_problem_id?: string | null;
  problem_version_id: string;
  candidate_id?: string | null;
  submission_number: number;
  language: string;
  status: string;
  score: number;
  tests_passed: number;
  tests_failed: number;
  total_tests: number;
  runtime_ms: number;
  memory_bytes: number;
  submitted_at: string;
  test_results?: TestResultItem[];
}

export interface CodingSession {
  id: string;
  interview_session_id: string;
  workspace_id: string;
  problem_id?: string;
  active_problem_version_id?: string;
  language: string;
  active_file_id?: string;
  status: string;
  is_editor_locked: boolean;
  settings: Record<string, any>;
  files: CodingFile[];
  created_at: string;
  updated_at: string;
}

interface CodingState {
  codingSession: CodingSession | null;
  files: CodingFile[];
  activeFileId: string | null;
  isEditorLocked: boolean;
  selectedLanguage: string;
  executionJob: CodingExecutionJob | null;
  isRunning: boolean;
  customInput: string;
  terminalTab: 'console' | 'tests' | 'custom_input' | 'submissions';
  snapshots: CodingSnapshot[];
  isSnapshotsDrawerOpen: boolean;
  activeProblem: ProblemDetail | null;
  submissions: SubmissionItem[];
  isProblemDrawerOpen: boolean;
  isInterviewerAssessmentOpen: boolean;

  setCodingSession: (session: CodingSession) => void;
  setActiveFileId: (fileId: string) => void;
  setIsEditorLocked: (locked: boolean) => void;
  setSelectedLanguage: (lang: string) => void;
  setExecutionJob: (job: CodingExecutionJob | null) => void;
  setIsRunning: (running: boolean) => void;
  setCustomInput: (input: string) => void;
  setTerminalTab: (tab: 'console' | 'tests' | 'custom_input' | 'submissions') => void;
  setSnapshots: (snapshots: CodingSnapshot[]) => void;
  setIsSnapshotsDrawerOpen: (open: boolean) => void;
  setActiveProblem: (problem: ProblemDetail | null) => void;
  setSubmissions: (submissions: SubmissionItem[]) => void;
  addSubmission: (submission: SubmissionItem) => void;
  setIsProblemDrawerOpen: (open: boolean) => void;
  setIsInterviewerAssessmentOpen: (open: boolean) => void;

  addFile: (file: CodingFile) => void;
  updateFileContent: (fileId: string, content: string) => void;
  deleteFile: (fileId: string) => void;
}

export const useCodingStore = create<CodingState>((set) => ({
  codingSession: null,
  files: [],
  activeFileId: null,
  isEditorLocked: false,
  selectedLanguage: 'python',
  executionJob: null,
  isRunning: false,
  customInput: '',
  terminalTab: 'console',
  snapshots: [],
  isSnapshotsDrawerOpen: false,
  activeProblem: null,
  submissions: [],
  isProblemDrawerOpen: false,
  isInterviewerAssessmentOpen: false,

  setCodingSession: (session) => {
    const activeId = session.active_file_id || (session.files.length > 0 ? session.files[0].id : null);
    set({
      codingSession: session,
      files: session.files || [],
      activeFileId: activeId,
      isEditorLocked: session.is_editor_locked,
      selectedLanguage: session.language || 'python',
    });
  },

  setActiveFileId: (activeFileId) => set({ activeFileId }),
  setIsEditorLocked: (isEditorLocked) => set({ isEditorLocked }),
  setSelectedLanguage: (selectedLanguage) => set({ selectedLanguage }),
  setExecutionJob: (executionJob) => set({ executionJob }),
  setIsRunning: (isRunning) => set({ isRunning }),
  setCustomInput: (customInput) => set({ customInput }),
  setTerminalTab: (terminalTab) => set({ terminalTab }),
  setSnapshots: (snapshots) => set({ snapshots }),
  setIsSnapshotsDrawerOpen: (isSnapshotsDrawerOpen) => set({ isSnapshotsDrawerOpen }),
  setActiveProblem: (activeProblem) => set({ activeProblem }),
  setSubmissions: (submissions) => set({ submissions }),
  addSubmission: (submission) => set((state) => ({ submissions: [submission, ...state.submissions] })),
  setIsProblemDrawerOpen: (isProblemDrawerOpen) => set({ isProblemDrawerOpen }),
  setIsInterviewerAssessmentOpen: (isInterviewerAssessmentOpen) => set({ isInterviewerAssessmentOpen }),

  addFile: (file) =>
    set((state) => ({
      files: [...state.files, file],
      activeFileId: file.id,
    })),

  updateFileContent: (fileId, content) =>
    set((state) => ({
      files: state.files.map((f) => (f.id === fileId ? { ...f, content } : f)),
    })),

  deleteFile: (fileId) =>
    set((state) => {
      const remaining = state.files.filter((f) => f.id !== fileId);
      const newActive = state.activeFileId === fileId ? (remaining.length > 0 ? remaining[0].id : null) : state.activeFileId;
      return { files: remaining, activeFileId: newActive };
    }),
}));
