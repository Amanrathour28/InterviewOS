'use client';

import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText,
  Star,
  Plus,
  Trash2,
  Tag,
  CheckCircle2,
  Shield,
  X,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { NoteCategoryType } from '@interviewos/types';

interface StructuredNotesPanelProps {
  sessionId: string;
  currentStage: string;
}

export const StructuredNotesPanel: React.FC<StructuredNotesPanelProps> = ({
  sessionId,
  currentStage,
}) => {
  const [notes, setNotes] = useState<any[]>([]);
  const [activeCategory, setActiveCategory] = useState<NoteCategoryType>('rubric');
  const [content, setContent] = useState('');
  const [rating, setRating] = useState<number | null>(null);
  const [tagInput, setTagInput] = useState('');
  const [tags, setTags] = useState<string[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [savedFeedback, setSavedFeedback] = useState(false);

  const fetchNotes = useCallback(async () => {
    try {
      const data = await apiClient<any[]>(`/sessions/${sessionId}/notes`);
      setNotes(data || []);
    } catch (err) {
      console.error('Failed to load notes:', err);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchNotes();
  }, [fetchNotes]);

  const handleAddTag = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && tagInput.trim()) {
      e.preventDefault();
      if (!tags.includes(tagInput.trim())) {
        setTags([...tags, tagInput.trim()]);
      }
      setTagInput('');
    }
  };

  const handleRemoveTag = (t: string) => {
    setTags(tags.filter((item) => item !== t));
  };

  const handleSaveNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!content.trim()) return;

    try {
      setIsSubmitting(true);
      const newNote = await apiClient<any>(`/sessions/${sessionId}/notes`, {
        method: 'POST',
        body: JSON.stringify({
          category: activeCategory,
          stage: currentStage,
          content: content.trim(),
          rating: rating,
          tags: tags,
        }),
      });

      setNotes([newNote, ...notes]);
      setContent('');
      setRating(null);
      setTags([]);
      setSavedFeedback(true);
      setTimeout(() => setSavedFeedback(false), 2500);
    } catch (err) {
      console.error('Failed to save note:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDeleteNote = async (noteId: string) => {
    try {
      await apiClient(`/sessions/${sessionId}/notes/${noteId}`, { method: 'DELETE' });
      setNotes(notes.filter((n) => n.id !== noteId));
    } catch (err) {
      console.error('Failed to delete note:', err);
    }
  };

  const categories: { id: NoteCategoryType; label: string }[] = [
    { id: 'rubric', label: 'Rubric Score' },
    { id: 'coding', label: 'Coding Assessment' },
    { id: 'system_design', label: 'System Design' },
    { id: 'behavioral', label: 'Behavioral & Comm' },
    { id: 'general', label: 'General Notes' },
  ];

  return (
    <div className="h-full flex flex-col max-w-4xl mx-auto w-full space-y-4">
      {/* Header Banner */}
      <div className="flex items-center justify-between p-3 rounded-lg bg-purple-950/30 border border-purple-900/40 text-xs text-purple-300">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-purple-400 shrink-0" />
          <span>Interviewer Structured Private Notes — strictly isolated and confidential to hiring team.</span>
        </div>
        {savedFeedback && (
          <span className="text-emerald-400 font-medium flex items-center gap-1">
            <CheckCircle2 className="w-3.5 h-3.5" /> Note Recorded
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 overflow-hidden">
        {/* Note Creation Form (7 cols) */}
        <form onSubmit={handleSaveNote} className="lg:col-span-7 flex flex-col space-y-3">
          {/* Category Selector */}
          <div className="flex items-center gap-1 overflow-x-auto no-scrollbar pb-1">
            {categories.map((c) => (
              <button
                key={c.id}
                type="button"
                onClick={() => setActiveCategory(c.id)}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-colors shrink-0 ${
                  activeCategory === c.id
                    ? 'bg-purple-600 text-white'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {c.label}
              </button>
            ))}
          </div>

          {/* Rating Stars */}
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400 font-mono text-[10px] uppercase">Evaluation Rating:</span>
            <div className="flex items-center gap-1">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setRating(rating === star ? null : star)}
                  className="p-1 hover:scale-110 transition-transform"
                >
                  <Star
                    className={`w-4 h-4 ${
                      rating && star <= rating
                        ? 'text-amber-400 fill-amber-400'
                        : 'text-slate-600 hover:text-slate-400'
                    }`}
                  />
                </button>
              ))}
            </div>
            {rating && (
              <span className="text-amber-400 font-mono text-[10px]">({rating}/5)</span>
            )}
          </div>

          {/* Note Input */}
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Record technical evaluation notes, code optimization observations, communication signals..."
            className="flex-1 min-h-[140px] w-full rounded-xl border border-slate-800 bg-slate-950 p-3.5 text-xs text-slate-200 focus:border-purple-500 focus:outline-none resize-none font-sans leading-relaxed"
          />

          {/* Tags */}
          <div className="space-y-1.5">
            <div className="flex flex-wrap items-center gap-1.5">
              {tags.map((t) => (
                <Badge
                  key={t}
                  variant="outline"
                  className="bg-purple-950/40 border-purple-800/60 text-purple-300 text-[10px] gap-1 px-2 py-0.5"
                >
                  <span>#{t}</span>
                  <button type="button" onClick={() => handleRemoveTag(t)}>
                    <X className="w-2.5 h-2.5" />
                  </button>
                </Badge>
              ))}
            </div>
            <input
              type="text"
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={handleAddTag}
              placeholder="Add tag and press Enter (e.g., algorithms, edge-cases, system-architecture)"
              className="w-full bg-slate-900 border border-slate-800 text-xs text-slate-300 rounded px-2.5 py-1.5 focus:outline-none focus:border-purple-500"
            />
          </div>

          <div className="flex justify-end pt-1">
            <Button
              type="submit"
              disabled={isSubmitting || !content.trim()}
              className="bg-purple-600 hover:bg-purple-500 text-white text-xs h-8 px-4 flex items-center gap-1.5 shadow-lg shadow-purple-600/20"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>Record Private Note</span>
            </Button>
          </div>
        </form>

        {/* Existing Notes List (5 cols) */}
        <div className="lg:col-span-5 flex flex-col space-y-2 overflow-hidden">
          <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
            Session Notes History ({notes.length})
          </h4>
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {notes.length === 0 ? (
              <div className="text-center py-12 text-slate-500 text-xs">
                No structured notes recorded yet.
              </div>
            ) : (
              notes.map((note) => (
                <Card
                  key={note.id}
                  className="p-3 bg-slate-900/80 border-slate-800 hover:border-slate-700 transition-colors space-y-2 text-xs"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <Badge
                        variant="outline"
                        className="text-[9px] font-mono uppercase border-purple-800/60 text-purple-300"
                      >
                        {note.category}
                      </Badge>
                      {note.rating && (
                        <span className="ml-2 text-amber-400 font-mono text-[10px]">
                          ★ {note.rating}/5
                        </span>
                      )}
                    </div>
                    <button
                      onClick={() => handleDeleteNote(note.id)}
                      className="text-slate-500 hover:text-rose-400 transition-colors"
                      title="Delete note"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>

                  <p className="text-slate-300 whitespace-pre-wrap leading-relaxed text-[11px]">
                    {note.content}
                  </p>

                  {note.tags && note.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1 pt-1">
                      {note.tags.map((tag: string) => (
                        <span key={tag} className="text-[9px] font-mono text-purple-400">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}

                  <div className="text-[9px] text-slate-500 font-mono pt-1 border-t border-slate-800/60 flex justify-between">
                    <span>Stage: {note.stage || 'General'}</span>
                    <span>{new Date(note.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                  </div>
                </Card>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
