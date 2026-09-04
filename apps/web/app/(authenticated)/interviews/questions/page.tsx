'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import {
  BookOpen,
  ArrowLeft,
  Search,
  Plus,
  Clock,
  Tag,
  AlertCircle,
  HelpCircle,
  CheckCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { useAuthStore } from '@/lib/auth/auth-store';
import { apiClient } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface QuestionItem {
  id: string;
  workspace_id?: string;
  title: string;
  prompt: string;
  question_type: string;
  difficulty: string;
  category: string;
  expected_duration_minutes: number;
  skills: string[];
  topics: string[];
  evaluation_criteria: string[];
  hints: string[];
  reference_answer?: string;
}

export default function QuestionsBankPage() {
  const { activeWorkspace } = useAuthStore();

  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [difficultyFilter, setDifficultyFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Create Question Modal
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [questionType, setQuestionType] = useState('technical');
  const [difficulty, setDifficulty] = useState('medium');
  const [category, setCategory] = useState('General');
  const [duration, setDuration] = useState(15);
  const [skillsInput, setSkillsInput] = useState('');
  const [criteriaInput, setCriteriaInput] = useState('');
  const [hintsInput, setHintsInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchQuestions = useCallback(async () => {
    if (!activeWorkspace) return;
    setIsLoading(true);
    setError(null);

    try {
      let url = `/questions?workspace_id=${activeWorkspace.id}&page=${page}&page_size=15`;
      if (typeFilter !== 'all') url += `&question_type=${typeFilter}`;
      if (difficultyFilter !== 'all') url += `&difficulty=${difficultyFilter}`;
      if (search.trim()) url += `&search=${encodeURIComponent(search.trim())}`;

      const res = await apiClient<any>(url);
      setQuestions(res.items || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 0);
    } catch (err: any) {
      setError(err.message || 'Failed to load questions');
    } finally {
      setIsLoading(false);
    }
  }, [activeWorkspace, page, typeFilter, difficultyFilter, search]);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  const handleCreateQuestion = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !title.trim() || !prompt.trim()) return;

    setIsSubmitting(true);
    setCreateError(null);

    const skills = skillsInput.split(',').map((s) => s.trim()).filter(Boolean);
    const criteria = criteriaInput.split('\n').map((s) => s.trim()).filter(Boolean);
    const hints = hintsInput.split('\n').map((s) => s.trim()).filter(Boolean);

    try {
      await apiClient('/questions', {
        method: 'POST',
        body: JSON.stringify({
          workspace_id: activeWorkspace.id,
          title: title.trim(),
          prompt: prompt.trim(),
          question_type: questionType,
          difficulty: difficulty,
          category: category.trim() || 'General',
          expected_duration_minutes: duration,
          skills: skills,
          evaluation_criteria: criteria,
          hints: hints,
        }),
      });

      // Reset form
      setTitle('');
      setPrompt('');
      setSkillsInput('');
      setCriteriaInput('');
      setHintsInput('');
      setShowCreateModal(false);
      await fetchQuestions();
    } catch (err: any) {
      setCreateError(err.message || 'Failed to create question');
    } finally {
      setIsSubmitting(false);
    }
  };

  const getDifficultyBadge = (diff: string) => {
    switch (diff) {
      case 'easy':
        return <Badge variant="success" className="text-[10px]">EASY</Badge>;
      case 'hard':
        return <Badge variant="outline" className="text-rose-400 text-[10px] border-rose-500/30">HARD</Badge>;
      default:
        return <Badge variant="warning" className="text-[10px]">MEDIUM</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Back link */}
      <div>
        <Link
          href="/interviews"
          className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-white transition-colors"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          Back to Interviews
        </Link>
      </div>

      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800/80 pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2.5">
            <BookOpen className="h-6 w-6 text-indigo-400" />
            Question Bank & Rubrics
          </h1>
          <p className="text-xs text-zinc-400 mt-1">
            Reusable technical, behavioral, and system architecture assessment library.
          </p>
        </div>

        <Button
          onClick={() => setShowCreateModal(true)}
          size="sm"
          className="text-xs font-semibold gap-1.5 shadow-lg shadow-primary/20"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Question
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col md:flex-row items-center gap-3">
        <div className="relative flex-1 w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-zinc-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search questions by title, keywords, or category..."
            className="w-full h-9 rounded-lg border border-zinc-800 bg-zinc-950 pl-9 pr-3 text-xs text-white placeholder:text-zinc-600 focus:border-primary focus:outline-none"
          />
        </div>

        <div className="flex items-center gap-2 w-full md:w-auto">
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-2.5 text-xs text-white focus:border-primary focus:outline-none capitalize"
          >
            <option value="all">All Types</option>
            <option value="technical">Technical</option>
            <option value="coding">Coding</option>
            <option value="system_design">System Design</option>
            <option value="behavioral">Behavioral</option>
          </select>

          <select
            value={difficultyFilter}
            onChange={(e) => setDifficultyFilter(e.target.value)}
            className="h-9 rounded-lg border border-zinc-800 bg-zinc-950 px-2.5 text-xs text-white focus:border-primary focus:outline-none capitalize"
          >
            <option value="all">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-950/20 text-xs text-rose-400">
          {error}
        </div>
      )}

      {/* Questions list */}
      <div className="space-y-3">
        {questions.map((q) => {
          const isExpanded = expandedId === q.id;
          return (
            <Card key={q.id} className="bg-[#0e0f15] border-zinc-800 p-4 space-y-3 transition-all">
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono uppercase text-indigo-400 font-semibold">
                      {q.category}
                    </span>
                    <Badge variant="default" className="text-[10px] capitalize">
                      {q.question_type.replace('_', ' ')}
                    </Badge>
                    {getDifficultyBadge(q.difficulty)}
                    <span className="text-[11px] text-zinc-500">• {q.expected_duration_minutes} mins</span>
                  </div>

                  <h3 className="text-sm font-bold text-white">{q.title}</h3>
                </div>

                <button
                  onClick={() => setExpandedId(isExpanded ? null : q.id)}
                  className="p-1 rounded text-zinc-400 hover:text-white text-xs"
                >
                  {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                </button>
              </div>

              <p className="text-xs text-zinc-300 leading-relaxed whitespace-pre-wrap">
                {isExpanded ? q.prompt : `${q.prompt.slice(0, 180)}...`}
              </p>

              {/* Skills tags */}
              {q.skills && q.skills.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {q.skills.map((s) => (
                    <span key={s} className="px-1.5 py-0.5 rounded text-[10px] bg-zinc-900 border border-zinc-800 text-zinc-300">
                      {s}
                    </span>
                  ))}
                </div>
              )}

              {/* Expanded details (Criteria & Hints) */}
              {isExpanded && (
                <div className="pt-3 border-t border-zinc-800/60 grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {q.evaluation_criteria && q.evaluation_criteria.length > 0 && (
                    <div className="space-y-1">
                      <span className="font-bold text-zinc-400 text-[11px] uppercase tracking-wider">
                        Evaluation Rubric:
                      </span>
                      <ul className="list-disc list-inside space-y-0.5 text-zinc-300 text-[11px]">
                        {q.evaluation_criteria.map((c, i) => (
                          <li key={i}>{c}</li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {q.hints && q.hints.length > 0 && (
                    <div className="space-y-1">
                      <span className="font-bold text-zinc-400 text-[11px] uppercase tracking-wider">
                        Interviewer Hints:
                      </span>
                      <ul className="list-disc list-inside space-y-0.5 text-zinc-400 text-[11px]">
                        {q.hints.map((h, i) => (
                          <li key={i}>{h}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </Card>
          );
        })}
      </div>

      {/* Create Question Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="w-full max-w-lg rounded-2xl border border-zinc-800 bg-[#0d0e14] p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
              <h3 className="text-base font-bold text-white">Create Reusable Question</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-zinc-500 hover:text-white">
                ✕
              </button>
            </div>

            {createError && (
              <div className="p-2 rounded bg-rose-950/20 border border-rose-500/30 text-xs text-rose-400">
                {createError}
              </div>
            )}

            <form onSubmit={handleCreateQuestion} className="space-y-3 text-xs">
              <div className="space-y-1">
                <label className="text-zinc-300 font-semibold">Question Title *</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Invert a Binary Tree in Memory"
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="space-y-1">
                  <label className="text-zinc-300">Type</label>
                  <select
                    value={questionType}
                    onChange={(e) => setQuestionType(e.target.value)}
                    className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none capitalize"
                  >
                    <option value="technical">Technical</option>
                    <option value="coding">Coding</option>
                    <option value="system_design">System Design</option>
                    <option value="behavioral">Behavioral</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-zinc-300">Difficulty</label>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none capitalize"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-zinc-300">Est. Duration (m)</label>
                  <input
                    type="number"
                    min="5"
                    max="120"
                    value={duration}
                    onChange={(e) => setDuration(parseInt(e.target.value, 10) || 15)}
                    className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                  />
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-zinc-300">Category</label>
                <input
                  type="text"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="e.g. Distributed Systems, Algorithms"
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-zinc-300 font-semibold">Prompt Text *</label>
                <textarea
                  rows={4}
                  required
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Full question instructions presented to the candidate..."
                  className="w-full rounded border border-zinc-800 bg-zinc-950 p-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-zinc-300">Skills (comma-separated)</label>
                <input
                  type="text"
                  value={skillsInput}
                  onChange={(e) => setSkillsInput(e.target.value)}
                  placeholder="Python, Trees, Recursion"
                  className="w-full h-8 rounded border border-zinc-800 bg-zinc-950 px-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="space-y-1">
                <label className="text-zinc-300">Evaluation Criteria (one per line)</label>
                <textarea
                  rows={2}
                  value={criteriaInput}
                  onChange={(e) => setCriteriaInput(e.target.value)}
                  placeholder="Correct recursive termination&#10;Handles null pointer cases"
                  className="w-full rounded border border-zinc-800 bg-zinc-950 p-2 text-xs text-white focus:border-primary focus:outline-none"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-zinc-800">
                <Button type="button" variant="ghost" size="sm" onClick={() => setShowCreateModal(false)} className="text-xs">
                  Cancel
                </Button>
                <Button type="submit" size="sm" disabled={isSubmitting} className="text-xs font-semibold">
                  {isSubmitting ? 'Saving...' : 'Save Question'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
