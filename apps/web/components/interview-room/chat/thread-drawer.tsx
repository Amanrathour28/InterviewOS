'use client';

import React, { useState } from 'react';
import { MessageSquare, X, Send } from 'lucide-react';
import { ChatMessage, ChatReaction } from '@interviewos/types';
import { ChatMessageItem } from './chat-message-item';
import { Button } from '@/components/ui/button';

interface ThreadDrawerProps {
  parentMessage: ChatMessage | null;
  replies: ChatMessage[];
  currentUserId: string;
  isInterviewer: boolean;
  onClose: () => void;
  onSendReply: (parentMessageId: string, content: string) => void;
  onReact: (messageId: string, emoji: string) => void;
  onEdit: (messageId: string, content: string) => void;
  onDelete: (messageId: string) => void;
}

export const ThreadDrawer: React.FC<ThreadDrawerProps> = ({
  parentMessage,
  replies,
  currentUserId,
  isInterviewer,
  onClose,
  onSendReply,
  onReact,
  onEdit,
  onDelete,
}) => {
  const [replyText, setReplyText] = useState('');
  const [isSending, setIsSending] = useState(false);

  if (!parentMessage) return null;

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!replyText.trim()) return;

    setIsSending(true);
    try {
      onSendReply(parentMessage.id, replyText.trim());
      setReplyText('');
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="w-80 border-l border-zinc-800 bg-[#0a0b10] flex flex-col h-full shrink-0 select-none">
      {/* Thread Header */}
      <div className="h-10 border-b border-zinc-800 px-3 flex items-center justify-between bg-zinc-950/60">
        <div className="flex items-center gap-2 text-xs font-bold text-white">
          <MessageSquare className="h-3.5 w-3.5 text-indigo-400" />
          <span>Thread Discussion</span>
        </div>
        <button onClick={onClose} className="text-zinc-500 hover:text-white transition-colors">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Thread Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Parent Message Card */}
        <div className="p-2.5 rounded-xl border border-indigo-500/30 bg-indigo-500/5">
          <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-400 block mb-1">
            Original Message
          </span>
          <ChatMessageItem
            message={parentMessage}
            currentUserId={currentUserId}
            isInterviewer={isInterviewer}
            onReact={onReact}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        </div>

        <div className="flex items-center gap-2 text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">
          <span className="h-px bg-zinc-800 flex-1" />
          <span>{replies.length} {replies.length === 1 ? 'Reply' : 'Replies'}</span>
          <span className="h-px bg-zinc-800 flex-1" />
        </div>

        {/* Replies List */}
        <div className="space-y-2">
          {replies.map((reply) => (
            <ChatMessageItem
              key={reply.id}
              message={reply}
              currentUserId={currentUserId}
              isInterviewer={isInterviewer}
              onReact={onReact}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </div>
      </div>

      {/* Reply Composer */}
      <form onSubmit={handleSend} className="p-3 border-t border-zinc-800 bg-zinc-950/80">
        <div className="relative">
          <input
            type="text"
            value={replyText}
            onChange={(e) => setReplyText(e.target.value)}
            placeholder="Reply to thread..."
            maxLength={8000}
            className="w-full rounded-xl border border-zinc-800 bg-zinc-900 px-3 py-2 pr-10 text-xs text-white placeholder:text-zinc-500 focus:border-indigo-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={isSending || !replyText.trim()}
            className="absolute right-1.5 top-1/2 -translate-y-1/2 h-7 w-7 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white flex items-center justify-center transition-all"
          >
            <Send className="h-3.5 w-3.5" />
          </button>
        </div>
      </form>
    </div>
  );
};
