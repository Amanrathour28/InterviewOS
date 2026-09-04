'use client';

import React, { useState } from 'react';
import { Code2, X, Send, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';

const SUPPORTED_LANGUAGES = [
  { id: 'python', label: 'Python' },
  { id: 'javascript', label: 'JavaScript' },
  { id: 'typescript', label: 'TypeScript' },
  { id: 'java', label: 'Java' },
  { id: 'cpp', label: 'C++' },
  { id: 'c', label: 'C' },
  { id: 'go', label: 'Go' },
  { id: 'rust', label: 'Rust' },
  { id: 'sql', label: 'SQL' },
  { id: 'bash', label: 'Bash / Shell' },
  { id: 'json', label: 'JSON' },
  { id: 'yaml', label: 'YAML' },
  { id: 'html', label: 'HTML' },
  { id: 'css', label: 'CSS' },
];

interface CodeSnippetComposerProps {
  isOpen: boolean;
  onClose: () => void;
  onSend: (data: { language: string; code: string; title?: string }) => void;
}

export const CodeSnippetComposer: React.FC<CodeSnippetComposerProps> = ({
  isOpen,
  onClose,
  onSend,
}) => {
  const [language, setLanguage] = useState('python');
  const [title, setTitle] = useState('');
  const [code, setCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!code.trim()) return;

    setIsSubmitting(true);
    try {
      onSend({
        language,
        code: code.trim(),
        title: title.trim() || undefined,
      });
      setCode('');
      setTitle('');
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 select-none">
      <div className="w-full max-w-2xl rounded-2xl border border-zinc-800 bg-[#0d0e14] shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="h-12 border-b border-zinc-800 px-4 flex items-center justify-between bg-zinc-950/60">
          <div className="flex items-center gap-2 text-white font-bold text-xs">
            <Code2 className="h-4 w-4 text-indigo-400" />
            <span>Share Structured Code Snippet</span>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-white transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="p-4 space-y-3.5 flex-1 flex flex-col overflow-hidden">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {/* Language Selection */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Language
              </label>
              <select
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
              >
                {SUPPORTED_LANGUAGES.map((lang) => (
                  <option key={lang.id} value={lang.id} className="bg-zinc-900">
                    {lang.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Title / Description */}
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-zinc-400 uppercase tracking-wider">
                Title / Context (Optional)
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Binary Search Optimization"
                maxLength={200}
                className="w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-1.5 text-xs text-white focus:border-indigo-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Code Editor Area */}
          <div className="flex-1 flex flex-col space-y-1 min-h-[200px]">
            <div className="flex items-center justify-between text-[11px] text-zinc-400">
              <span className="font-semibold uppercase tracking-wider">Source Code</span>
              <span className="font-mono text-[10px] text-zinc-500">
                {code.length} / 50,000 chars
              </span>
            </div>
            <textarea
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder={`// Paste or write ${language} code here...`}
              maxLength={50000}
              required
              className="flex-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 p-3 text-xs font-mono text-zinc-200 focus:border-indigo-500 focus:outline-none resize-none leading-relaxed selection:bg-indigo-500/30"
            />
          </div>

          {/* Footer */}
          <div className="pt-2 flex items-center justify-between border-t border-zinc-800/80">
            <span className="text-[10px] text-zinc-500">
              Code snippets are shared with syntax highlighting (data only, not executed).
            </span>
            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="text-xs text-zinc-400 hover:text-white"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                size="sm"
                disabled={isSubmitting || !code.trim()}
                className="text-xs font-bold gap-1.5 bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20"
              >
                <Send className="h-3.5 w-3.5" />
                Share Snippet
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
