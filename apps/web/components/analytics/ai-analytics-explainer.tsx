'use client';

import React, { useState } from 'react';
import { Sparkles, Send, X, Bot, ShieldCheck, AlertCircle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { apiClient } from '@/lib/api';

interface AIAnalyticsExplainerProps {
  workspaceId: string;
  contextLabel: string;
  metrics: Record<string, any>;
  isOpen: boolean;
  onClose: () => void;
}

export function AIAnalyticsExplainer({
  workspaceId,
  contextLabel,
  metrics,
  isOpen,
  onClose,
}: AIAnalyticsExplainerProps) {
  const [question, setQuestion] = useState('');
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleExplain = async (customQuestion?: string) => {
    const query = (customQuestion || question || 'Summarize the key trends, strengths, and bottlenecks visible in these metrics.').trim();
    if (!query) return;

    setLoading(true);
    setError(null);

    try {
      const res = await apiClient<{ explanation: string; context_label: string; generated_at: string }>(
        `/analytics/explain?workspace_id=${workspaceId}`,
        {
          method: 'POST',
          body: JSON.stringify({
            metrics,
            question: query,
            context_label: contextLabel,
          }),
        }
      );

      setExplanation(res.explanation || 'No interpretation generated.');
    } catch (err: any) {
      setError(err.message || 'Failed to generate AI explanation.');
    } finally {
      setLoading(false);
    }
  };

  const presetQuestions = [
    'What are the main bottlenecks in our interview pipeline?',
    'How do candidate score distributions compare across competencies?',
    'Are there any signs of interviewer scoring inconsistency?',
    'What is our evidence sufficiency and grounding quality rate?',
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="relative w-full max-w-2xl rounded-2xl border border-zinc-800 bg-zinc-950 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-zinc-800/80 pb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-500 text-white shadow-lg shadow-indigo-500/20">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white flex items-center gap-2">
                AI Analytics Advisory
                <span className="text-[10px] uppercase font-semibold px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  Advisory Only
                </span>
              </h2>
              <p className="text-xs text-zinc-400">
                Natural-language interpretation grounded directly in deterministic metrics
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Preset quick buttons */}
        <div className="space-y-1.5">
          <div className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Quick Inquiries</div>
          <div className="flex flex-wrap gap-1.5">
            {presetQuestions.map((q, i) => (
              <button
                key={i}
                onClick={() => {
                  setQuestion(q);
                  handleExplain(q);
                }}
                className="rounded-lg border border-zinc-800 bg-zinc-900/60 px-2.5 py-1 text-xs text-zinc-300 hover:border-indigo-500/50 hover:bg-indigo-500/10 hover:text-indigo-300 transition-all text-left"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Custom Input */}
        <div className="space-y-2">
          <div className="relative">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about the active metrics..."
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleExplain();
              }}
              className="w-full rounded-xl border border-zinc-800 bg-zinc-900/80 px-4 py-2.5 pr-24 text-sm text-white placeholder-zinc-500 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            <Button
              size="sm"
              disabled={loading}
              onClick={() => handleExplain()}
              className="absolute right-1.5 top-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs gap-1.5 h-8 px-3"
            >
              {loading ? <RefreshCw className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
              Explain
            </Button>
          </div>
        </div>

        {/* Output Box */}
        <div className="min-h-[160px] max-h-[300px] overflow-y-auto rounded-xl border border-zinc-800/80 bg-zinc-900/40 p-4 text-sm text-zinc-200">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-10 text-zinc-400 space-y-2">
              <RefreshCw className="h-6 w-6 animate-spin text-indigo-400" />
              <p className="text-xs">Analyzing telemetry and deterministic metrics...</p>
            </div>
          ) : error ? (
            <div className="flex items-center gap-2 text-rose-400 text-xs py-4">
              <AlertCircle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : explanation ? (
            <div className="space-y-3 leading-relaxed">
              <div className="flex items-center gap-2 text-xs font-semibold text-indigo-300">
                <Bot className="h-4 w-4" />
                <span>Executive Synthesis</span>
              </div>
              <div className="text-xs sm:text-sm text-zinc-300 whitespace-pre-line bg-zinc-950/40 p-3 rounded-lg border border-zinc-800/50">
                {explanation}
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-8 text-zinc-500 text-xs text-center space-y-1">
              <Bot className="h-6 w-6 text-zinc-600 mb-1" />
              <p>Select a quick inquiry above or enter a custom question.</p>
              <p className="text-[11px] text-zinc-600">Deterministic metrics will be analyzed with strict evidence grounding.</p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t border-zinc-800/80 pt-3 text-[11px] text-zinc-500">
          <div className="flex items-center gap-1.5">
            <ShieldCheck className="h-3.5 w-3.5 text-emerald-400" />
            <span>Advisory Only • Non-Deterministic Reasoning • Grounded to Tenant Metrics</span>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="text-xs h-7 text-zinc-400 hover:text-white">
            Close
          </Button>
        </div>
      </div>
    </div>
  );
}
