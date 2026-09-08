'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  MessageSquare,
  Lock,
  Send,
  Code2,
  Smile,
  ChevronDown,
  Shield,
  AlertCircle,
  Sparkles,
} from 'lucide-react';
import { apiClient } from '@/lib/api';
import { RealtimeClient } from '@/lib/realtime/realtime-client';
import { useChatStore } from '@/lib/stores/use-chat-store';
import { ChatMessage, ChatChannel } from '@interviewos/types';
import { ChatMessageItem } from './chat-message-item';
import { CodeSnippetComposer } from './code-snippet-composer';
import { ThreadDrawer } from './thread-drawer';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface ChatPanelProps {
  sessionId: string;
  currentUserId: string;
  isInterviewer: boolean;
  realtimeClient: RealtimeClient | null;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({
  sessionId,
  currentUserId,
  isInterviewer,
  realtimeClient,
}) => {
  const {
    channels,
    activeChannelId,
    messagesByChannel,
    threads,
    activeThreadParentId,
    typingUsersByChannel,
    isCodeComposerOpen,
    isLoadingMessages,
    setChannels,
    setActiveChannelId,
    setMessages,
    addMessage,
    updateMessage,
    deleteMessage,
    setThread,
    addThreadReply,
    setActiveThreadParentId,
    setTyping,
    updateReactions,
    markChannelRead,
    setIsCodeComposerOpen,
    setIsLoadingMessages,
  } = useChatStore();

  const [textInput, setTextInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const realtimeClientRef = useRef(realtimeClient);
  realtimeClientRef.current = realtimeClient;

  // 1. Fetch accessible channels on mount
  const loadChannels = useCallback(async () => {
    try {
      const data = await apiClient<ChatChannel[]>(`/sessions/${sessionId}/chat/channels`);
      setChannels(data);
      if (data.length > 0 && !activeChannelId) {
        setActiveChannelId(data[0].id);
      }
    } catch (err) {
      console.warn('[ChatPanel] Failed to load chat channels:', err);
    }
  }, [sessionId, activeChannelId, setChannels, setActiveChannelId]);

  useEffect(() => {
    loadChannels();
  }, [loadChannels]);

  // 2. Fetch messages for active channel
  const loadMessages = useCallback(async (channelId: string) => {
    setIsLoadingMessages(true);
    try {
      const data = await apiClient<ChatMessage[]>(`/chat/channels/${channelId}/messages?limit=50`);
      setMessages(channelId, data);
      // Mark channel read
      if (data.length > 0) {
        const lastMsg = data[data.length - 1];
        await apiClient(`/chat/channels/${channelId}/read`, {
          method: 'POST',
          body: JSON.stringify({ last_read_message_id: lastMsg.id }),
        }).catch(() => {});
        markChannelRead(channelId);
      }
    } catch (err) {
      console.warn('[ChatPanel] Failed to load messages:', err);
    } finally {
      setIsLoadingMessages(false);
    }
  }, [setIsLoadingMessages, setMessages, markChannelRead]);

  useEffect(() => {
    if (activeChannelId) {
      loadMessages(activeChannelId);
    }
  }, [activeChannelId, loadMessages]);

  // 3. Scroll to bottom handler
  const scrollToBottom = (smooth = true) => {
    messagesEndRef.current?.scrollIntoView({ behavior: smooth ? 'smooth' : 'auto' });
  };

  useEffect(() => {
    scrollToBottom(false);
  }, [activeChannelId]);

  const handleScroll = () => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
    setShowScrollBottom(!isNearBottom);
  };

  // 4. Hook into RealtimeClient for live chat & typing events
  useEffect(() => {
    if (!realtimeClient) return;

    const unsubTyping = realtimeClient.onChatTyping((data: any) => {
      if (data.userId !== currentUserId) {
        setTyping(data.channelId, { userId: data.userId, userName: data.userName }, data.isTyping);
      }
    });

    const handleInterviewEvent = (event: any) => {
      if (event?.event_type === 'CHAT_MESSAGE_CREATED') {
        const channelId = event.payload?.channel_id;
        const message = event.payload?.message;
        if (channelId && message) {
          addMessage(channelId, message);
        }
      }
    };

    const unsubEvent = realtimeClient.on('interview_event', handleInterviewEvent);

    return () => {
      unsubTyping();
      unsubEvent();
    };
  }, [realtimeClient, currentUserId, setTyping, addMessage]);

  // 5. Send plain text message
  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!textInput.trim() || !activeChannelId) return;

    const content = textInput.trim();
    const clientMessageId = `client-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    setTextInput('');

    // Clear typing state
    realtimeClient?.sendTyping(activeChannelId, activeChannel?.channel_type || 'public', false);

    // Optimistic local add
    const tempMessage: ChatMessage = {
      id: clientMessageId,
      channel_id: activeChannelId,
      session_id: sessionId,
      workspace_id: '',
      sender_id: currentUserId,
      sender_name: 'You',
      sender_role: isInterviewer ? 'interviewer' : 'candidate',
      message_type: 'text',
      content,
      is_edited: false,
      is_deleted: false,
      reactions: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      client_message_id: clientMessageId,
    };
    addMessage(activeChannelId, tempMessage);
    scrollToBottom(true);

    setIsSending(true);
    try {
      const serverMsg = await apiClient<ChatMessage>(`/chat/channels/${activeChannelId}/messages`, {
        method: 'POST',
        body: JSON.stringify({
          message_type: 'text',
          content,
          client_message_id: clientMessageId,
        }),
      });
      addMessage(activeChannelId, serverMsg);
      realtimeClientRef.current?.dispatchEvent('CHAT_MESSAGE_CREATED', {
        channel_id: activeChannelId,
        message: serverMsg,
      });
    } catch (err: any) {
      console.warn('[ChatPanel] Send message failed:', err);
    } finally {
      setIsSending(false);
    }
  };

  // 6. Share structured code snippet
  const handleSendCodeSnippet = async (data: { language: string; code: string; title?: string }) => {
    if (!activeChannelId) return;

    const clientMessageId = `client-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const tempMessage: ChatMessage = {
      id: clientMessageId,
      channel_id: activeChannelId,
      session_id: sessionId,
      workspace_id: '',
      sender_id: currentUserId,
      sender_name: 'You',
      sender_role: isInterviewer ? 'interviewer' : 'candidate',
      message_type: 'code',
      content: data.code,
      metadata: { language: data.language, title: data.title },
      is_edited: false,
      is_deleted: false,
      reactions: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      client_message_id: clientMessageId,
    };
    addMessage(activeChannelId, tempMessage);
    scrollToBottom(true);

    try {
      const serverMsg = await apiClient<ChatMessage>(`/chat/channels/${activeChannelId}/messages`, {
        method: 'POST',
        body: JSON.stringify({
          message_type: 'code',
          content: data.code,
          metadata: { language: data.language, title: data.title },
          client_message_id: clientMessageId,
        }),
      });
      addMessage(activeChannelId, serverMsg);
      realtimeClientRef.current?.dispatchEvent('CHAT_MESSAGE_CREATED', {
        channel_id: activeChannelId,
        message: serverMsg,
      });
    } catch (err: any) {
      console.warn('[ChatPanel] Share code failed:', err);
    }
  };

  // 7. Handle Typing Input & Throttle
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setTextInput(e.target.value);

    if (activeChannelId && realtimeClientRef.current) {
      realtimeClientRef.current.sendTyping(activeChannelId, activeChannel?.channel_type || 'public', true);

      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
      typingTimeoutRef.current = setTimeout(() => {
        realtimeClientRef.current?.sendTyping(activeChannelId, activeChannel?.channel_type || 'public', false);
      }, 3000);
    }
  };

  // 8. Reactions
  const handleReact = async (messageId: string, emoji: string) => {
    if (!activeChannelId) return;
    try {
      const updatedReactions = await apiClient<any[]>(`/chat/messages/${messageId}/reactions`, {
        method: 'POST',
        body: JSON.stringify({ emoji }),
      });
      updateReactions(activeChannelId, messageId, updatedReactions);
    } catch (err) {
      console.warn('[ChatPanel] Toggle reaction failed:', err);
    }
  };

  // 9. Edit Message
  const handleEditMessage = async (messageId: string, content: string) => {
    if (!activeChannelId) return;
    try {
      const updated = await apiClient<ChatMessage>(`/chat/messages/${messageId}`, {
        method: 'PATCH',
        body: JSON.stringify({ content }),
      });
      updateMessage(activeChannelId, messageId, updated);
    } catch (err: any) {
      alert(err.message || 'Failed to edit message');
    }
  };

  // 10. Delete Message
  const handleDeleteMessage = async (messageId: string) => {
    if (!activeChannelId) return;
    try {
      await apiClient(`/chat/messages/${messageId}`, { method: 'DELETE' });
      deleteMessage(activeChannelId, messageId);
    } catch (err: any) {
      alert(err.message || 'Failed to delete message');
    }
  };

  // 11. Threads
  const handleOpenThread = async (parentMsg: ChatMessage) => {
    setActiveThreadParentId(parentMsg.id);
    try {
      const threadData = await apiClient<{ parent_message: ChatMessage; replies: ChatMessage[] }>(
        `/chat/messages/${parentMsg.id}/thread`
      );
      setThread(parentMsg.id, threadData.replies);
    } catch (err) {
      console.warn('[ChatPanel] Failed to fetch thread detail:', err);
    }
  };

  const handleSendThreadReply = async (parentMessageId: string, content: string) => {
    if (!activeChannelId) return;
    try {
      const reply = await apiClient<ChatMessage>(`/chat/channels/${activeChannelId}/messages`, {
        method: 'POST',
        body: JSON.stringify({
          message_type: 'text',
          content,
          parent_message_id: parentMessageId,
        }),
      });
      addThreadReply(parentMessageId, reply);
    } catch (err: any) {
      alert(err.message || 'Failed to reply in thread');
    }
  };

  const activeChannel = channels.find((c) => c.id === activeChannelId);
  const activeMessages = activeChannelId ? messagesByChannel[activeChannelId] || [] : [];
  const activeTyping = activeChannelId ? typingUsersByChannel[activeChannelId] || [] : [];
  const isPrivateChannel = activeChannel?.channel_type === 'interviewer_private';

  const activeThreadParent = activeThreadParentId
    ? activeMessages.find((m) => m.id === activeThreadParentId) || null
    : null;
  const activeThreadReplies = activeThreadParentId ? threads[activeThreadParentId] || [] : [];

  return (
    <div className="flex-1 flex h-full overflow-hidden bg-[#07080c] select-none">
      {/* MAIN CHAT COLUMN */}
      <div className="flex-1 flex flex-col h-full min-w-0">
        {/* Top Channel Selector Tabs */}
        <div className="h-11 border-b border-zinc-800 bg-zinc-950/80 px-4 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-2">
            {channels.map((c) => {
              const isPrivate = c.channel_type === 'interviewer_private';
              const isActive = c.id === activeChannelId;

              return (
                <button
                  key={c.id}
                  onClick={() => setActiveChannelId(c.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    isActive
                      ? isPrivate
                        ? 'bg-amber-500/10 border border-amber-500/30 text-amber-300'
                        : 'bg-zinc-800 border border-zinc-700 text-white'
                      : 'text-zinc-400 hover:text-zinc-200 border border-transparent'
                  }`}
                >
                  {isPrivate ? <Lock className="h-3.5 w-3.5 text-amber-400" /> : <MessageSquare className="h-3.5 w-3.5" />}
                  <span>{c.name}</span>
                  {c.unread_count > 0 && (
                    <Badge variant="accent" className="h-4 px-1 text-[9px] font-mono bg-rose-500 text-white border-0">
                      {c.unread_count}
                    </Badge>
                  )}
                </button>
              );
            })}
          </div>

          <span className="text-[10px] text-zinc-500 font-mono hidden sm:inline">
            PostgreSQL Durable • Socket.IO Live
          </span>
        </div>

        {/* Private Channel Confidential Warning */}
        {isPrivateChannel && (
          <div className="px-4 py-2 border-b border-amber-500/20 bg-amber-500/5 flex items-center gap-2 text-[11px] text-amber-300 shrink-0">
            <Shield className="h-3.5 w-3.5 text-amber-400 shrink-0" />
            <span>
              <strong>Confidential Interviewer Channel:</strong> Messages here are strictly isolated to panel members and never visible to the candidate.
            </span>
          </div>
        )}

        {/* Messages List Container */}
        <div
          ref={scrollContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-4 space-y-2 relative"
        >
          {isLoadingMessages ? (
            <div className="flex items-center justify-center h-48 text-xs text-zinc-500">
              Loading conversation history...
            </div>
          ) : activeMessages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-48 text-center space-y-2">
              <div className="h-10 w-10 rounded-full bg-zinc-800/50 flex items-center justify-center text-zinc-500">
                <MessageSquare className="h-5 w-5" />
              </div>
              <p className="text-xs font-bold text-zinc-300">
                {isPrivateChannel ? 'No private notes yet.' : 'No messages yet.'}
              </p>
              <p className="text-[10px] text-zinc-500 max-w-xs">
                {isPrivateChannel
                  ? 'Use this private channel to discuss scoring signals, follow-ups, and panel observations.'
                  : 'Start the conversation with questions, notes, or syntax-highlighted code snippets.'}
              </p>
            </div>
          ) : (
            activeMessages.map((msg) => (
              <ChatMessageItem
                key={msg.id}
                message={msg}
                currentUserId={currentUserId}
                isInterviewer={isInterviewer}
                onReact={handleReact}
                onOpenThread={handleOpenThread}
                onEdit={handleEditMessage}
                onDelete={handleDeleteMessage}
              />
            ))
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Floating Jump-to-Bottom Button */}
        {showScrollBottom && (
          <button
            onClick={() => scrollToBottom(true)}
            className="absolute bottom-20 right-8 px-3 py-1.5 rounded-full bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow-xl shadow-indigo-600/30 flex items-center gap-1.5 transition-all z-20"
          >
            <ChevronDown className="h-3.5 w-3.5" />
            <span>Latest Messages</span>
          </button>
        )}

        {/* Typing Indicator Bar */}
        {activeTyping.length > 0 && (
          <div className="px-4 py-1 text-[11px] text-indigo-400 flex items-center gap-1.5 shrink-0 bg-zinc-950/40">
            <span className="flex gap-0.5">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-bounce" />
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.2s]" />
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-400 animate-bounce [animation-delay:0.4s]" />
            </span>
            <span>
              {activeTyping.map((u) => u.userName).join(', ')}{' '}
              {activeTyping.length === 1 ? 'is typing...' : 'are typing...'}
            </span>
          </div>
        )}

        {/* Bottom Message Input Bar */}
        <form
          onSubmit={handleSendMessage}
          className="p-3 border-t border-zinc-800 bg-[#0d0e14] flex items-center gap-2 shrink-0"
        >
          {/* Share Code Snippet Button */}
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => setIsCodeComposerOpen(true)}
            className="h-9 px-2.5 border-zinc-800 text-zinc-400 hover:text-white hover:bg-zinc-800 shrink-0 gap-1"
            title="Share Code Snippet"
          >
            <Code2 className="h-4 w-4 text-indigo-400" />
            <span className="hidden sm:inline text-xs">Share Code</span>
          </Button>

          {/* Text Input */}
          <input
            type="text"
            value={textInput}
            onChange={handleInputChange}
            placeholder={
              isPrivateChannel
                ? 'Type private interviewer note (visible to panel only)...'
                : 'Type a message (markdown supported)...'
            }
            maxLength={8000}
            className="flex-1 rounded-xl border border-zinc-800 bg-zinc-950 px-3.5 py-2 text-xs text-white placeholder:text-zinc-500 focus:border-indigo-500 focus:outline-none"
          />

          {/* Send Button */}
          <Button
            type="submit"
            size="sm"
            disabled={isSending || !textInput.trim()}
            className="h-9 px-4 font-bold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white shrink-0 shadow-lg shadow-indigo-600/20"
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
        </form>
      </div>

      {/* THREAD DRAWER (if thread open) */}
      {activeThreadParent && (
        <ThreadDrawer
          parentMessage={activeThreadParent}
          replies={activeThreadReplies}
          currentUserId={currentUserId}
          isInterviewer={isInterviewer}
          onClose={() => setActiveThreadParentId(null)}
          onSendReply={handleSendThreadReply}
          onReact={handleReact}
          onEdit={handleEditMessage}
          onDelete={handleDeleteMessage}
        />
      )}

      {/* CODE SNIPPET COMPOSER MODAL */}
      <CodeSnippetComposer
        isOpen={isCodeComposerOpen}
        onClose={() => setIsCodeComposerOpen(false)}
        onSend={handleSendCodeSnippet}
      />
    </div>
  );
};
