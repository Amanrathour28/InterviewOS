'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import {
  ArrowLeft,
  BookOpen,
  Save,
  Copy,
  Archive,
  Plus,
  Trash2,
  Eye,
  EyeOff,
  Code2,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  FileCode,
  Layers,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { SUPPORTED_CODING_LANGUAGES, getLanguageConfig } from '@interviewos/types';

export default function ProblemDetailPage() {
  const params = useParams();
  const router = useRouter();
  const problemId = params?.problemId as string;

  const [problem, setProblem] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'statement' | 'starter' | 'tests' | 'versions'>('statement');
  const [selectedLanguage, setSelectedLanguage] = useState('python');

  // Edit states
  const [title, setTitle] = useState('');
  const [difficulty, setDifficulty] = useState('medium');
  const [category, setCategory] = useState('algorithms');
  const [statement, setStatement] = useState('');
  const [constraints, setConstraints] = useState<string[]>([]);
  const [examples, setExamples] = useState<any[]>([]);
  const [starterCodes, setStarterCodes] = useState<Record<string, string>>({});
  const [testCases, setTestCases] = useState<any[]>([]);

  const [isSaving, setIsSaving] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);

  // New test case modal state
  const [isAddTestOpen, setIsAddTestOpen] = useState(false);
  const [newTestTitle, setNewTestTitle] = useState('');
  const [newTestInput, setNewTestInput] = useState('');
  const [newTestExpected, setNewTestExpected] = useState('');
  const [newTestIsHidden, setNewTestIsHidden] = useState(false);

  const fetchProblem = useCallback(async () => {
    try {
      setIsLoading(true);
      const data = await apiClient<any>(`/coding/problems/${problemId}`);
      setProblem(data);
      setTitle(data.title);
      setDifficulty(data.difficulty);
      setCategory(data.category);

      const ver = data.current_version;
      if (ver) {
        setStatement(ver.problem_statement || '');
        setConstraints(ver.constraints || []);
        setExamples(ver.examples || []);
        setStarterCodes(ver.starter_codes || {});
        setTestCases(ver.test_cases || []);
      }
    } catch (err) {
      console.error('Failed to fetch problem:', err);
    } finally {
      setIsLoading(false);
    }
  }, [problemId]);

  useEffect(() => {
    if (problemId) {
      fetchProblem();
    }
  }, [problemId, fetchProblem]);

  const handleSave = async () => {
    try {
      setIsSaving(true);
      setSaveSuccess(false);
      const updated = await apiClient<any>(`/coding/problems/${problemId}`, {
        method: 'PATCH',
        body: JSON.stringify({
          title,
          difficulty,
          category,
          problem_statement: statement,
          constraints,
          examples,
          starter_codes: starterCodes,
        }),
      });
      setProblem(updated);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err) {
      console.error('Failed to save problem updates:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleClone = async () => {
    try {
      const cloned = await apiClient<any>(`/coding/problems/${problemId}/clone`, {
        method: 'POST',
        body: JSON.stringify({ new_title: `${title} (Clone)` }),
      });
      router.push(`/coding/problems/${cloned.id}`);
    } catch (err) {
      console.error('Failed to clone problem:', err);
    }
  };

  const handleArchive = async () => {
    if (!confirm('Are you sure you want to archive this problem?')) return;
    try {
      await apiClient(`/coding/problems/${problemId}/archive`, { method: 'POST' });
      router.push('/coding/problems');
    } catch (err) {
      console.error('Failed to archive problem:', err);
    }
  };

  const handleAddTestCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!problem?.current_version?.id) return;
    try {
      const tc = await apiClient<any>(`/coding/problem-versions/${problem.current_version.id}/tests`, {
        method: 'POST',
        body: JSON.stringify({
          title: newTestTitle,
          input_data: newTestInput,
          expected_output: newTestExpected,
          is_hidden: newTestIsHidden,
          weight: newTestIsHidden ? 2.0 : 1.0,
        }),
      });
      setTestCases([...testCases, tc]);
      setIsAddTestOpen(false);
      setNewTestTitle('');
      setNewTestInput('');
      setNewTestExpected('');
      setNewTestIsHidden(false);
    } catch (err) {
      console.error('Failed to add test case:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center text-slate-400 text-xs">
        Loading problem details...
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-5">
        <div className="flex items-center gap-3">
          <Link
            href="/coding/problems"
            className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-white">{title}</h1>
              <Badge variant="outline" className="text-[10px] font-mono border-slate-700 text-slate-300">
                v{problem?.current_version?.version_number || 1}
              </Badge>
              {problem?.is_system && (
                <span className="text-[9px] bg-slate-800 text-indigo-400 px-1.5 py-0.5 rounded border border-indigo-500/20">
                  System Problem
                </span>
              )}
            </div>
            <p className="text-xs text-slate-400 mt-0.5">{category.replace('_', ' ')} • {difficulty}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {saveSuccess && (
            <span className="text-xs text-emerald-400 flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> Saved (v{problem?.current_version?.version_number})
            </span>
          )}
          <Button
            variant="outline"
            onClick={handleClone}
            className="border-slate-800 bg-slate-900 text-slate-300 hover:text-white text-xs flex items-center gap-1.5"
          >
            <Copy className="w-3.5 h-3.5" />
            Clone
          </Button>
          {!problem?.is_system && (
            <Button
              variant="outline"
              onClick={handleArchive}
              className="border-slate-800 bg-slate-900 text-rose-400 hover:text-rose-300 text-xs flex items-center gap-1.5"
            >
              <Archive className="w-3.5 h-3.5" />
              Archive
            </Button>
          )}
          <Button
            onClick={handleSave}
            disabled={isSaving}
            className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs flex items-center gap-1.5 shadow-lg shadow-indigo-600/20"
          >
            <Save className="w-3.5 h-3.5" />
            {isSaving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-800 gap-1 text-xs">
        <button
          onClick={() => setActiveTab('statement')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'statement'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Statement & Examples
        </button>
        <button
          onClick={() => setActiveTab('starter')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'starter'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Starter Code Templates
        </button>
        <button
          onClick={() => setActiveTab('tests')}
          className={`px-4 py-2 font-medium border-b-2 transition-colors ${
            activeTab === 'tests'
              ? 'border-indigo-500 text-white'
              : 'border-transparent text-slate-400 hover:text-slate-200'
          }`}
        >
          Test Suite ({testCases.length})
        </button>
      </div>

      {/* Tab: Statement */}
      {activeTab === 'statement' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            <Card className="p-5 bg-slate-900/90 border-slate-800 space-y-3">
              <label className="text-xs font-semibold text-white block">Problem Description (Markdown)</label>
              <textarea
                value={statement}
                onChange={(e) => setStatement(e.target.value)}
                rows={12}
                className="w-full bg-slate-950 border border-slate-800 text-xs font-mono rounded-lg p-3 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </Card>

            <Card className="p-5 bg-slate-900/90 border-slate-800 space-y-3">
              <label className="text-xs font-semibold text-white block">Constraints</label>
              <div className="space-y-2">
                {constraints.map((c, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <Input
                      value={c}
                      onChange={(e) => {
                        const updated = [...constraints];
                        updated[i] = e.target.value;
                        setConstraints(updated);
                      }}
                      className="bg-slate-950 border-slate-800 text-xs font-mono"
                    />
                    <button
                      onClick={() => setConstraints(constraints.filter((_, idx) => idx !== i))}
                      className="text-slate-500 hover:text-rose-400 p-1"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                ))}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setConstraints([...constraints, ''])}
                  className="border-slate-800 text-xs text-indigo-400"
                >
                  + Add Constraint
                </Button>
              </div>
            </Card>
          </div>

          <div className="space-y-4">
            <Card className="p-5 bg-slate-900/90 border-slate-800 space-y-4">
              <h3 className="text-xs font-bold text-white uppercase tracking-wider">Assessment Properties</h3>

              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Difficulty</label>
                <select
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 text-xs rounded-md p-2 text-slate-200"
                >
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] text-slate-400 block mb-1">Category</label>
                <Input
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="bg-slate-950 border-slate-800 text-xs"
                />
              </div>

              <div className="pt-2 border-t border-slate-800 text-xs text-slate-400 space-y-2">
                <div className="flex justify-between">
                  <span>Created:</span>
                  <span className="font-mono text-slate-300">
                    {new Date(problem?.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span>Versions:</span>
                  <span className="font-mono text-slate-300">{problem?.versions_count}</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      )}

      {/* Tab: Starter Code */}
      {activeTab === 'starter' && (
        <Card className="p-5 bg-slate-900/90 border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              <Code2 className="w-4 h-4 text-indigo-400" />
              <h3 className="text-xs font-bold text-white">Language Starter Code Templates</h3>
            </div>

            <select
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-xs rounded-md px-3 py-1.5 text-slate-200"
            >
              {SUPPORTED_CODING_LANGUAGES.map((lang) => (
                <option key={lang.id} value={lang.id}>
                  {lang.name}
                </option>
              ))}
            </select>
          </div>

          <textarea
            value={starterCodes[selectedLanguage] || getLanguageConfig(selectedLanguage).starterCode}
            onChange={(e) =>
              setStarterCodes({
                ...starterCodes,
                [selectedLanguage]: e.target.value,
              })
            }
            rows={14}
            className="w-full bg-slate-950 border border-slate-800 text-xs font-mono rounded-lg p-3 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          />
        </Card>
      )}

      {/* Tab: Tests */}
      {activeTab === 'tests' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-white">Assessment Test Cases</h3>
              <p className="text-xs text-slate-400">
                Public tests are visible to candidates. Hidden tests are evaluated securely during submission.
              </p>
            </div>

            <Button
              onClick={() => setIsAddTestOpen(true)}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs flex items-center gap-1.5"
            >
              <Plus className="w-3.5 h-3.5" />
              Add Test Case
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {testCases.map((tc, idx) => (
              <Card
                key={tc.id || idx}
                className="p-4 bg-slate-900/90 border-slate-800 space-y-2.5 relative"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-white">{tc.title}</span>
                    {tc.is_hidden ? (
                      <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20 text-[10px] flex items-center gap-1">
                        <EyeOff className="w-3 h-3" /> Hidden
                      </Badge>
                    ) : (
                      <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 text-[10px] flex items-center gap-1">
                        <Eye className="w-3 h-3" /> Public
                      </Badge>
                    )}
                  </div>
                  <span className="text-[10px] text-slate-500 font-mono">Weight: {tc.weight || 1.0}</span>
                </div>

                <div className="space-y-1.5 text-xs font-mono">
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">Input:</span>
                    <pre className="p-2 bg-slate-950 rounded border border-slate-800/80 text-slate-300 text-[11px] overflow-x-auto">
                      {tc.input_data || '(empty)'}
                    </pre>
                  </div>
                  <div>
                    <span className="text-[10px] text-slate-500 uppercase block">Expected Output:</span>
                    <pre className="p-2 bg-slate-950 rounded border border-slate-800/80 text-emerald-400/90 text-[11px] overflow-x-auto">
                      {tc.expected_output || '(empty)'}
                    </pre>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Add Test Case Modal */}
      {isAddTestOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-md w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white">Add Assessment Test Case</h2>
              <button onClick={() => setIsAddTestOpen(false)} className="text-slate-400 hover:text-slate-200 text-xs">
                ✕
              </button>
            </div>

            <form onSubmit={handleAddTestCase} className="space-y-3">
              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1">Title</label>
                <Input
                  value={newTestTitle}
                  onChange={(e) => setNewTestTitle(e.target.value)}
                  placeholder="e.g., Hidden Edge Case: Empty Array"
                  className="bg-slate-950 border-slate-800 text-xs"
                  required
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1">Input Data (Stdin)</label>
                <textarea
                  value={newTestInput}
                  onChange={(e) => setNewTestInput(e.target.value)}
                  placeholder="Raw input passed to solution stdin..."
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 text-xs font-mono rounded-md p-2 text-slate-200"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1">Expected Output (Stdout)</label>
                <textarea
                  value={newTestExpected}
                  onChange={(e) => setNewTestExpected(e.target.value)}
                  placeholder="Exact expected stdout match..."
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 text-xs font-mono rounded-md p-2 text-slate-200"
                  required
                />
              </div>

              <div className="flex items-center gap-2 pt-1">
                <input
                  type="checkbox"
                  id="isHiddenCheckbox"
                  checked={newTestIsHidden}
                  onChange={(e) => setNewTestIsHidden(e.target.checked)}
                  className="rounded bg-slate-950 border-slate-800 text-indigo-600 focus:ring-0"
                />
                <label htmlFor="isHiddenCheckbox" className="text-xs text-slate-300 cursor-pointer">
                  Hidden test case (do not expose input/output to candidates)
                </label>
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsAddTestOpen(false)}
                  className="border-slate-800 text-xs text-slate-300"
                >
                  Cancel
                </Button>
                <Button type="submit" className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs">
                  Add Test
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
