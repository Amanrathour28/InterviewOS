'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  BookOpen,
  Search,
  Plus,
  Filter,
  Layers,
  Clock,
  Tag,
  CheckCircle2,
  ExternalLink,
  Copy,
  Sparkles,
  ChevronRight,
  Code2,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';

const CATEGORIES = [
  'all',
  'arrays',
  'strings',
  'hashing',
  'two_pointers',
  'sliding_window',
  'linked_list',
  'trees',
  'binary_search',
  'graphs',
  'dynamic_programming',
  'greedy',
  'backtracking',
  'sql',
  'algorithms',
];

export default function ProblemLibraryPage() {
  const router = useRouter();
  const [problems, setProblems] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [selectedDifficulty, setSelectedDifficulty] = useState<string>('all');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedScope, setSelectedScope] = useState<'all' | 'system' | 'workspace'>('all');
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  // Create form state
  const [createTitle, setCreateTitle] = useState('');
  const [createDifficulty, setCreateDifficulty] = useState('medium');
  const [createCategory, setCreateCategory] = useState('algorithms');
  const [createDuration, setCreateDuration] = useState(30);
  const [createDescription, setCreateDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);

  const fetchProblems = useCallback(async () => {
    try {
      setIsLoading(true);
      const params = new URLSearchParams();
      if (search) params.append('search', search);
      if (selectedDifficulty !== 'all') params.append('difficulty', selectedDifficulty);
      if (selectedCategory !== 'all') params.append('category', selectedCategory);
      if (selectedScope !== 'all') params.append('scope', selectedScope);

      const data = await apiClient<any>(`/coding/problems?${params.toString()}`);
      setProblems(data.items || []);
    } catch (err) {
      console.error('Failed to fetch problems:', err);
    } finally {
      setIsLoading(false);
    }
  }, [search, selectedDifficulty, selectedCategory, selectedScope]);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchProblems();
    }, 200);
    return () => clearTimeout(timer);
  }, [fetchProblems]);

  const handleCreateProblem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createTitle.trim()) return;
    try {
      setIsCreating(true);
      const newProblem = await apiClient<any>('/coding/problems', {
        method: 'POST',
        body: JSON.stringify({
          title: createTitle,
          difficulty: createDifficulty,
          category: createCategory,
          estimated_duration_minutes: createDuration,
          short_description: createDescription,
          problem_statement: `# ${createTitle}\n\n${createDescription}`,
        }),
      });
      setIsCreateModalOpen(false);
      setCreateTitle('');
      setCreateDescription('');
      router.push(`/coding/problems/${newProblem.id}`);
    } catch (err) {
      console.error('Failed to create problem:', err);
    } finally {
      setIsCreating(false);
    }
  };

  const getDifficultyBadge = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20 font-mono text-[10px]">Easy</Badge>;
      case 'medium':
        return <Badge className="bg-amber-500/10 text-amber-400 border-amber-500/20 font-mono text-[10px]">Medium</Badge>;
      case 'hard':
        return <Badge className="bg-rose-500/10 text-rose-400 border-rose-500/20 font-mono text-[10px]">Hard</Badge>;
      default:
        return <Badge variant="outline" className="text-[10px]">{difficulty}</Badge>;
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 lg:p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-6">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <BookOpen className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">Interview Problem Library</h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Browse, author, and assign curated coding problems and test suites for technical interviews.
          </p>
        </div>

        <Button
          onClick={() => setIsCreateModalOpen(true)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs px-4 py-2 flex items-center gap-2 shadow-lg shadow-indigo-600/20"
        >
          <Plus className="w-4 h-4" />
          Create Problem
        </Button>
      </div>

      {/* Filter Toolbar */}
      <div className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          {/* Search Input */}
          <div className="md:col-span-2 relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search problems by title, topic, or keyword..."
              className="pl-9 bg-slate-900/90 border-slate-800 text-xs focus:ring-indigo-500/50"
            />
          </div>

          {/* Scope Selector */}
          <div className="flex rounded-md bg-slate-900 border border-slate-800 p-0.5">
            <button
              onClick={() => setSelectedScope('all')}
              className={`flex-1 py-1.5 text-xs font-medium rounded ${
                selectedScope === 'all' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => setSelectedScope('system')}
              className={`flex-1 py-1.5 text-xs font-medium rounded ${
                selectedScope === 'system' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              System
            </button>
            <button
              onClick={() => setSelectedScope('workspace')}
              className={`flex-1 py-1.5 text-xs font-medium rounded ${
                selectedScope === 'workspace' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              Workspace
            </button>
          </div>

          {/* Difficulty Filter */}
          <select
            value={selectedDifficulty}
            onChange={(e) => setSelectedDifficulty(e.target.value)}
            className="bg-slate-900 border border-slate-800 text-xs rounded-md px-3 text-slate-300 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          >
            <option value="all">All Difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
        </div>

        {/* Category Filter Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 scrollbar-none">
          {CATEGORIES.map((cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-2.5 py-1 rounded-full text-[11px] whitespace-nowrap transition-colors ${
                selectedCategory === cat
                  ? 'bg-slate-800 text-indigo-400 border border-indigo-500/30 font-semibold'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 border border-slate-800/80'
              }`}
            >
              {cat === 'all' ? 'All Categories' : cat.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
            </button>
          ))}
        </div>
      </div>

      {/* Problem Cards List */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pt-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="h-44 bg-slate-900/50 rounded-xl border border-slate-800/60 animate-pulse" />
          ))}
        </div>
      ) : problems.length === 0 ? (
        <div className="text-center py-16 border border-dashed border-slate-800 rounded-xl bg-slate-900/20">
          <BookOpen className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <h3 className="text-sm font-semibold text-slate-300">No problems found</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Try adjusting your search query or filters, or create a new coding problem for your workspace.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {problems.map((problem) => (
            <Card
              key={problem.id}
              className="bg-slate-900/80 border-slate-800/90 hover:border-slate-700/80 transition-all p-5 flex flex-col justify-between group shadow-sm hover:shadow-md"
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold text-white group-hover:text-indigo-400 transition-colors">
                        {problem.title}
                      </h3>
                      {problem.is_system && (
                        <span className="text-[9px] bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded border border-slate-700 font-medium">
                          System
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      {getDifficultyBadge(problem.difficulty)}
                      <span className="text-[11px] text-slate-400 capitalize">
                        {problem.category.replace('_', ' ')}
                      </span>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed">
                  {problem.short_description || 'No description provided.'}
                </p>

                {problem.tags && problem.tags.length > 0 && (
                  <div className="flex flex-wrap gap-1 pt-1">
                    {problem.tags.slice(0, 3).map((tag: string) => (
                      <span key={tag} className="text-[10px] bg-slate-800/60 text-slate-400 px-2 py-0.5 rounded-full border border-slate-800">
                        #{tag}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              <div className="pt-4 mt-4 border-t border-slate-800/80 flex items-center justify-between">
                <div className="flex items-center gap-1.5 text-[11px] text-slate-400">
                  <Clock className="w-3.5 h-3.5 text-slate-500" />
                  <span>{problem.estimated_duration_minutes || 30} mins</span>
                </div>

                <Link
                  href={`/coding/problems/${problem.id}`}
                  className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 flex items-center gap-1 group-hover:translate-x-0.5 transition-transform"
                >
                  View Details
                  <ChevronRight className="w-3.5 h-3.5" />
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Create Problem Modal */}
      {isCreateModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h2 className="text-base font-bold text-white">Create Coding Problem</h2>
              <button onClick={() => setIsCreateModalOpen(false)} className="text-slate-400 hover:text-slate-200 text-xs">
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateProblem} className="space-y-3.5">
              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1">Problem Title</label>
                <Input
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  placeholder="e.g., Longest Substring Without Repeating Characters"
                  className="bg-slate-950 border-slate-800 text-xs"
                  required
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-slate-300 font-medium block mb-1">Difficulty</label>
                  <select
                    value={createDifficulty}
                    onChange={(e) => setCreateDifficulty(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 text-xs rounded-md p-2 text-slate-200"
                  >
                    <option value="easy">Easy</option>
                    <option value="medium">Medium</option>
                    <option value="hard">Hard</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-slate-300 font-medium block mb-1">Category</label>
                  <select
                    value={createCategory}
                    onChange={(e) => setCreateCategory(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 text-xs rounded-md p-2 text-slate-200"
                  >
                    {CATEGORIES.filter((c) => c !== 'all').map((cat) => (
                      <option key={cat} value={cat}>
                        {cat.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="text-xs text-slate-300 font-medium block mb-1">Short Description</label>
                <textarea
                  value={createDescription}
                  onChange={(e) => setCreateDescription(e.target.value)}
                  placeholder="Brief summary of the problem requirements..."
                  rows={3}
                  className="w-full bg-slate-950 border border-slate-800 text-xs rounded-md p-2.5 text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsCreateModalOpen(false)}
                  className="border-slate-800 text-xs text-slate-300"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isCreating}
                  className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs"
                >
                  {isCreating ? 'Creating...' : 'Create & Edit Details'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
