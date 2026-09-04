'use client';

import React, { useState } from 'react';
import {
  MessageSquare,
  Smile,
  MoreVertical,
  Edit2,
  Trash2,
  Copy,
  Check,
  Code2,
  Shield,
  User,
} from 'lucide-react';
import { ChatMessage, ChatReaction } from '@interviewos/types';

const ALLOWED_REACTIONS = ['👍', '❤️', '😂', '🎯', '👏', '❓'];

interface ChatMessageItemProps {
  message: ChatMessage;
  currentUserId: string;
  isInterviewer: boolean;
  onReact: (messageId: string, emoji: string) => void;
  onOpenThread?: (message: ChatMessage) => void;
  onEdit?: (messageId: string, newContent: string) => void;
  onDelete?: (messageId: string) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  currentUserId,
  isInterviewer,
  onReact,
  onOpenThread,
  onEdit,
  onDelete,
}) => {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [showPicker, setShowPicker] = useState(false);
  const [showOptions, setShowOptions] = useState(false);

  const isAuthor = message.sender_id === currentUserId;
  const canDelete = isAuthor || isInterviewer;

  const handleCopyCode = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSaveEdit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editContent.trim()) return;
    onEdit?.(message.id, editContent.trim());
    setIsEditing(false);
  };

  const formatTime = (ts: string) => {
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const isSenderInterviewer =
    message.sender_role === 'interviewer' ||
    message.sender_role === 'lead_interviewer' ||
    message.sender_role === 'panelist' ||
    message.sender_role === 'organizer' ||
    message.sender_role === 'admin' ||
    message.sender_role === 'platform_admin';

  // Group reactions by emoji
  const reactionGroups = (message.reactions || []).reduce<Record<string, { count: number; reactedByMe: boolean }>>(
    (acc, r) => {
      if (!acc[r.emoji]) {
        acc[r.emoji] = { count: 0, reactedByMe: false };
      }
      acc[r.emoji].count += 1;
      if (r.user_id === currentUserId) {
        acc[r.emoji].reactedByMe = true;
      }
      return acc;
    },
    {}
  );

  return (
    <div
      className={`group relative flex gap-3 p-3 rounded-xl transition-all duration-150 ${
        message.is_deleted ? 'opacity-60 bg-zinc-950/40' : 'hover:bg-zinc-900/40'
      }`}
    >
      {/* Avatar */}
      <div className="shrink-0">
        <div
          className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold uppercase border ${
            isSenderInterviewer
              ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400'
              : 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400'
          }`}
        >
          {message.sender_name?.[0] || 'U'}
        </div>
      </div>

      {/* Message Body */}
      <div className="flex-1 min-w-0 space-y-1">
        {/* Header (Name, Role, Timestamp) */}
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-white truncate max-w-[140px]">
            {message.sender_name}
          </span>

          <span
            className={`text-[9px] font-semibold px-1.5 py-0.2 rounded border uppercase tracking-wider ${
              isSenderInterviewer
                ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-300'
                : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300'
            }`}
          >
            {message.sender_role}
          </span>

          <span className="text-[10px] text-zinc-500 font-mono">
            {formatTime(message.created_at)}
          </span>

          {message.is_edited && !message.is_deleted && (
            <span className="text-[9px] text-zinc-500 italic">(edited)</span>
          )}
        </div>

        {/* Content */}
        {message.is_deleted ? (
          <p className="text-xs italic text-zinc-500">{message.content}</p>
        ) : isEditing ? (
          <form onSubmit={handleSaveEdit} className="space-y-2 pt-1">
            <textarea
              value={editContent}
              onChange={(e) => setEditContent(e.target.value)}
              className="w-full rounded-lg border border-zinc-800 bg-zinc-950 p-2 text-xs text-white focus:border-indigo-500 focus:outline-none resize-none"
              rows={3}
            />
            <div className="flex items-center gap-1.5 justify-end">
              <button
                type="button"
                onClick={() => setIsEditing(false)}
                className="px-2 py-1 text-[11px] text-zinc-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-2.5 py-1 text-[11px] font-bold rounded bg-indigo-600 hover:bg-indigo-500 text-white"
              >
                Save
              </button>
            </div>
          </form>
        ) : message.message_type === 'code' ? (
          /* Structured Code Snippet Box */
          <div className="rounded-xl border border-zinc-800 bg-[#0a0b10] overflow-hidden my-1 shadow-lg max-w-xl">
            <div className="h-8 border-b border-zinc-800 px-3 flex items-center justify-between bg-zinc-950">
              <div className="flex items-center gap-1.5">
                <Code2 className="h-3.5 w-3.5 text-indigo-400" />
                <span className="text-[11px] font-bold text-white">
                  {message.metadata?.title || 'Code Snippet'}
                </span>
                <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-zinc-800 text-zinc-400 uppercase">
                  {message.metadata?.language || 'plaintext'}
                </span>
              </div>
              <button
                onClick={() => handleCopyCode(message.content)}
                className="flex items-center gap-1 text-[10px] text-zinc-400 hover:text-white transition-colors"
                title="Copy code to clipboard"
              >
                {copied ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
            <pre className="p-3 text-xs font-mono text-zinc-200 overflow-x-auto leading-relaxed bg-[#06070a]">
              <code>{message.content}</code>
            </pre>
          </div>
        ) : (
          /* Standard Plaintext / Markdown message */
          <p className="text-xs text-zinc-200 leading-relaxed break-words whitespace-pre-wrap selection:bg-indigo-500/30">
            {message.content}
          </p>
        )}

        {/* Reactions & Thread Reply Badges */}
        {!message.is_deleted && (
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            {/* Emoji reaction pills */}
            {Object.entries(reactionGroups).map(([emoji, { count, reactedByMe }]) => (
              <button
                key={emoji}
                onClick={() => onReact(message.id, emoji)}
                className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-xs transition-all border ${
                  reactedByMe
                    ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300 font-bold'
                    : 'bg-zinc-900 border-zinc-800 text-zinc-400 hover:border-zinc-700'
                }`}
              >
                <span>{emoji}</span>
                <span className="text-[10px] font-mono">{count}</span>
              </button>
            ))}

            {/* Thread Reply Count Button */}
            {message.reply_count && message.reply_count > 0 ? (
              <button
                onClick={() => onOpenThread?.(message)}
                className="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 border border-indigo-500/20 transition-all"
              >
                <MessageSquare className="h-3 w-3" />
                <span>
                  {message.reply_count} {message.reply_count === 1 ? 'reply' : 'replies'}
                </span>
              </button>
            ) : null}
          </div>
        )}
      </div>

      {/* Hover Message Action Bar */}
      {!message.is_deleted && (
        <div className="absolute top-2 right-2 hidden group-hover:flex items-center gap-1 p-1 rounded-lg bg-zinc-900/90 border border-zinc-800 backdrop-blur-md shadow-xl z-10">
          {/* Reaction Picker Button */}
          <div className="relative">
            <button
              onClick={() => setShowPicker(!showPicker)}
              className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
              title="Add reaction"
            >
              <Smile className="h-3.5 w-3.5" />
            </button>

            {/* Quick Emoji Picker Dropdown */}
            {showPicker && (
              <div className="absolute right-0 bottom-full mb-1 p-1 rounded-xl bg-zinc-950 border border-zinc-800 shadow-2xl flex items-center gap-1 z-20">
                {ALLOWED_REACTIONS.map((emoji) => (
                  <button
                    key={emoji}
                    onClick={() => {
                      onReact(message.id, emoji);
                      setShowPicker(false);
                    }}
                    className="p-1.5 hover:scale-125 transition-transform text-sm"
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Reply in Thread */}
          {onOpenThread && !message.parent_message_id && (
            <button
              onClick={() => onOpenThread(message)}
              className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
              title="Reply in thread"
            >
              <MessageSquare className="h-3.5 w-3.5" />
            </button>
          )}

          {/* Edit (author only) */}
          {isAuthor && message.message_type === 'text' && (
            <button
              onClick={() => setIsEditing(true)}
              className="p-1 rounded text-zinc-400 hover:text-white hover:bg-zinc-800 transition-colors"
              title="Edit message"
            >
              <Edit2 className="h-3.5 w-3.5" />
            </button>
          )}

          {/* Delete (author or interviewer) */}
          {canDelete && (
            <button
              onClick={() => onDelete?.(message.id)}
              className="p-1 rounded text-zinc-400 hover:text-rose-400 hover:bg-zinc-800 transition-colors"
              title="Delete message"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      )}
    </div>
  );
};
