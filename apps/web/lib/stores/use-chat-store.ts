import { create } from 'zustand';
import { ChatChannel, ChatMessage, ChatReaction } from '@interviewos/types';

interface ChatState {
  channels: ChatChannel[];
  activeChannelId: string | null;
  messagesByChannel: Record<string, ChatMessage[]>;
  threads: Record<string, ChatMessage[]>; // Keyed by parent_message_id
  activeThreadParentId: string | null;
  typingUsersByChannel: Record<string, { userId: string; userName: string; timestamp: number }[]>;
  isCodeComposerOpen: boolean;
  isLoadingMessages: boolean;

  // Actions
  setChannels: (channels: ChatChannel[]) => void;
  setActiveChannelId: (channelId: string) => void;
  setMessages: (channelId: string, messages: ChatMessage[]) => void;
  addMessage: (channelId: string, message: ChatMessage) => void;
  updateMessage: (channelId: string, messageId: string, updates: Partial<ChatMessage>) => void;
  deleteMessage: (channelId: string, messageId: string) => void;
  setThread: (parentMessageId: string, replies: ChatMessage[]) => void;
  addThreadReply: (parentMessageId: string, reply: ChatMessage) => void;
  setActiveThreadParentId: (parentId: string | null) => void;
  setTyping: (channelId: string, user: { userId: string; userName: string }, isTyping: boolean) => void;
  updateReactions: (channelId: string, messageId: string, reactions: ChatReaction[]) => void;
  markChannelRead: (channelId: string) => void;
  setIsCodeComposerOpen: (open: boolean) => void;
  setIsLoadingMessages: (loading: boolean) => void;
  resetChat: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  channels: [],
  activeChannelId: null,
  messagesByChannel: {},
  threads: {},
  activeThreadParentId: null,
  typingUsersByChannel: {},
  isCodeComposerOpen: false,
  isLoadingMessages: false,

  setChannels: (channels) =>
    set((state) => ({
      channels,
      activeChannelId: state.activeChannelId || channels[0]?.id || null,
    })),

  setActiveChannelId: (activeChannelId) =>
    set((state) => {
      // Clear unread count for the newly active channel
      const updatedChannels = state.channels.map((c) =>
        c.id === activeChannelId ? { ...c, unread_count: 0 } : c
      );
      return { activeChannelId, channels: updatedChannels };
    }),

  setMessages: (channelId, messages) =>
    set((state) => ({
      messagesByChannel: {
        ...state.messagesByChannel,
        [channelId]: messages,
      },
    })),

  addMessage: (channelId, message) =>
    set((state) => {
      const existing = state.messagesByChannel[channelId] || [];
      // Deduplicate by client_message_id or id
      if (
        existing.some(
          (m) =>
            m.id === message.id ||
            (message.client_message_id && m.client_message_id === message.client_message_id)
        )
      ) {
        return {
          messagesByChannel: {
            ...state.messagesByChannel,
            [channelId]: existing.map((m) =>
              m.id === message.id ||
              (message.client_message_id && m.client_message_id === message.client_message_id)
                ? message
                : m
            ),
          },
        };
      }

      // If active channel is different, increment unread count
      const updatedChannels = state.channels.map((c) =>
        c.id === channelId && state.activeChannelId !== channelId
          ? { ...c, unread_count: c.unread_count + 1 }
          : c
      );

      return {
        channels: updatedChannels,
        messagesByChannel: {
          ...state.messagesByChannel,
          [channelId]: [...existing, message],
        },
      };
    }),

  updateMessage: (channelId, messageId, updates) =>
    set((state) => {
      const existing = state.messagesByChannel[channelId] || [];
      return {
        messagesByChannel: {
          ...state.messagesByChannel,
          [channelId]: existing.map((m) => (m.id === messageId ? { ...m, ...updates } : m)),
        },
      };
    }),

  deleteMessage: (channelId, messageId) =>
    set((state) => {
      const existing = state.messagesByChannel[channelId] || [];
      return {
        messagesByChannel: {
          ...state.messagesByChannel,
          [channelId]: existing.map((m) =>
            m.id === messageId
              ? { ...m, is_deleted: true, content: 'This message was deleted.', reactions: [] }
              : m
          ),
        },
      };
    }),

  setThread: (parentMessageId, replies) =>
    set((state) => ({
      threads: {
        ...state.threads,
        [parentMessageId]: replies,
      },
    })),

  addThreadReply: (parentMessageId, reply) =>
    set((state) => {
      const existingReplies = state.threads[parentMessageId] || [];
      const updatedReplies = existingReplies.some((r) => r.id === reply.id)
        ? existingReplies.map((r) => (r.id === reply.id ? reply : r))
        : [...existingReplies, reply];

      // Also increment reply count on parent message if in active channel
      const updatedMessages = { ...state.messagesByChannel };
      Object.keys(updatedMessages).forEach((chId) => {
        updatedMessages[chId] = updatedMessages[chId].map((m) =>
          m.id === parentMessageId ? { ...m, reply_count: (m.reply_count || 0) + 1 } : m
        );
      });

      return {
        threads: {
          ...state.threads,
          [parentMessageId]: updatedReplies,
        },
        messagesByChannel: updatedMessages,
      };
    }),

  setActiveThreadParentId: (activeThreadParentId) => set({ activeThreadParentId }),

  setTyping: (channelId, user, isTyping) =>
    set((state) => {
      const current = state.typingUsersByChannel[channelId] || [];
      if (isTyping) {
        const withoutUser = current.filter((u) => u.userId !== user.userId);
        return {
          typingUsersByChannel: {
            ...state.typingUsersByChannel,
            [channelId]: [...withoutUser, { ...user, timestamp: Date.now() }],
          },
        };
      } else {
        return {
          typingUsersByChannel: {
            ...state.typingUsersByChannel,
            [channelId]: current.filter((u) => u.userId !== user.userId),
          },
        };
      }
    }),

  updateReactions: (channelId, messageId, reactions) =>
    set((state) => {
      const existing = state.messagesByChannel[channelId] || [];
      return {
        messagesByChannel: {
          ...state.messagesByChannel,
          [channelId]: existing.map((m) => (m.id === messageId ? { ...m, reactions } : m)),
        },
      };
    }),

  markChannelRead: (channelId) =>
    set((state) => ({
      channels: state.channels.map((c) =>
        c.id === channelId ? { ...c, unread_count: 0 } : c
      ),
    })),

  setIsCodeComposerOpen: (isCodeComposerOpen) => set({ isCodeComposerOpen }),
  setIsLoadingMessages: (isLoadingMessages) => set({ isLoadingMessages }),

  resetChat: () =>
    set({
      channels: [],
      activeChannelId: null,
      messagesByChannel: {},
      threads: {},
      activeThreadParentId: null,
      typingUsersByChannel: {},
      isCodeComposerOpen: false,
      isLoadingMessages: false,
    }),
}));
