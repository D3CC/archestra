// src/chat/chat-store.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  status: 'pending' | 'streaming' | 'complete' | 'error';
}

interface ChatState {
  messages: Message[];
  isThinking: boolean;
  pendingMessageId: string | null;
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => string;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  removePendingMessage: () => void;
  setThinking: (thinking: boolean) => void;
  clearMessages: () => void;
  getLastUserMessage: () => Message | undefined;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      isThinking: false,
      pendingMessageId: null,

      addMessage: (message) => {
        const id = uuidv4();
        const newMessage: Message = {
          ...message,
          id,
          timestamp: Date.now(),
        };

        set((state) => {
          // If there's a pending message (streaming), remove it first to avoid duplicates
          const filteredMessages = state.pendingMessageId
            ? state.messages.filter((m) => m.id !== state.pendingMessageId)
            : state.messages;

          return {
            messages: [...filteredMessages, newMessage],
            pendingMessageId: message.status === 'streaming' ? id : null,
          };
        });

        return id;
      },

      updateMessage: (id, updates) => {
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg
          ),
          // Clear pending flag if message is no longer streaming
          pendingMessageId:
            updates.status && updates.status !== 'streaming'
              ? null
              : state.pendingMessageId,
        }));
      },

      removePendingMessage: () => {
        set((state) => {
          if (!state.pendingMessageId) return state;
          return {
            messages: state.messages.filter(
              (m) => m.id !== state.pendingMessageId
            ),
            pendingMessageId: null,
          };
        });
      },

      setThinking: (thinking) => {
        set({ isThinking: thinking });
      },

      clearMessages: () => {
        set({ messages: [], pendingMessageId: null, isThinking: false });
      },

      getLastUserMessage: () => {
        const { messages } = get();
        return [...messages].reverse().find((m) => m.role === 'user');
      },
    }),
    {
      name: 'archestra-chat-storage',
      // Only persist completed messages, not pending/streaming ones
      partialize: (state) => ({
        messages: state.messages.filter(
          (m) => m.status === 'complete' || m.status === 'error'
        ),
      }),
      onRehydrateStorage: () => {
        return (state) => {
          if (state) {
            // Ensure no stale pending state after reload
            state.pendingMessageId = null;
            state.isThinking = false;
          }
        };
      },
    }
  )
);
