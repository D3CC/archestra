// src/store/chatStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  status?: 'sending' | 'sent' | 'thinking' | 'done' | 'error';
}

interface ChatState {
  messages: Message[];
  isThinking: boolean;
  pendingMessageId: string | null;
  addMessage: (msg: Omit<Message, 'id' | 'timestamp'>) => string;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  removeMessage: (id: string) => void;
  setThinking: (thinking: boolean, messageId?: string) => void;
  clearMessages: () => void;
  getPendingMessage: () => Message | null;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      isThinking: false,
      pendingMessageId: null,

      addMessage: (msg) => {
        const id = uuidv4();
        const timestamp = Date.now();
        const newMessage: Message = { ...msg, id, timestamp };

        set((state) => {
          // If we're adding an assistant message while thinking, update the pending one
          if (msg.role === 'assistant' && state.isThinking && state.pendingMessageId) {
            const updatedMessages = state.messages.map((m) =>
              m.id === state.pendingMessageId
                ? { ...m, content: msg.content, status: 'done' as const }
                : m
            );
            return {
              messages: updatedMessages,
              isThinking: false,
              pendingMessageId: null,
            };
          }

          // Deduplicate: check if message with same content and role already exists within 1 second
          const duplicate = state.messages.find(
            (m) =>
              m.role === msg.role &&
              m.content === msg.content &&
              Math.abs(m.timestamp - timestamp) < 1000
          );
          if (duplicate) {
            return state; // Skip duplicate
          }

          return {
            messages: [...state.messages, newMessage],
            isThinking: msg.role === 'assistant' ? true : state.isThinking,
            pendingMessageId: msg.role === 'assistant' ? id : state.pendingMessageId,
          };
        });

        return id;
      },

      updateMessage: (id, updates) => {
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg
          ),
        }));
      },

      removeMessage: (id) => {
        set((state) => ({
          messages: state.messages.filter((msg) => msg.id !== id),
          pendingMessageId:
            state.pendingMessageId === id ? null : state.pendingMessageId,
        }));
      },

      setThinking: (thinking, messageId) => {
        set((state) => ({
          isThinking: thinking,
          pendingMessageId: messageId ?? state.pendingMessageId,
        }));
      },

      clearMessages: () => {
        set({ messages: [], isThinking: false, pendingMessageId: null });
      },

      getPendingMessage: () => {
        const state = get();
        if (!state.pendingMessageId) return null;
        return (
          state.messages.find((m) => m.id === state.pendingMessageId) ?? null
        );
      },
    }),
    {
      name: 'archestra-chat-storage',
      partialize: (state) => ({
        messages: state.messages.filter((m) => m.status !== 'thinking'),
        isThinking: false,
        pendingMessageId: null,
      }),
      merge: (persisted, current) => {
        const saved = persisted as Partial<ChatState>;
        // Filter out any stale thinking messages on reload
        const cleanMessages = (saved.messages ?? []).filter(
          (m) => m.status !== 'thinking'
        );
        return {
          ...current,
          ...saved,
          messages: cleanMessages,
          isThinking: false,
          pendingMessageId: null,
        };
      },
    }
  )
);
