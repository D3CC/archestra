// src/store/chatStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  status: 'sending' | 'sent' | 'streaming' | 'completed' | 'error';
}

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  pendingMessageId: string | null;
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => string;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  removeMessage: (id: string) => void;
  clearMessages: () => void;
  setStreaming: (streaming: boolean, messageId?: string) => void;
  getPendingMessage: () => Message | null;
  deduplicateMessages: () => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      isStreaming: false,
      pendingMessageId: null,

      addMessage: (message) => {
        const id = uuidv4();
        const newMessage: Message = {
          ...message,
          id,
          timestamp: Date.now(),
        };
        set((state) => ({
          messages: [...state.messages, newMessage],
          pendingMessageId: message.status === 'streaming' ? id : state.pendingMessageId,
        }));
        return id;
      },

      updateMessage: (id, updates) => {
        set((state) => {
          const messages = state.messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg
          );
          return { messages };
        });
      },

      removeMessage: (id) => {
        set((state) => ({
          messages: state.messages.filter((msg) => msg.id !== id),
          pendingMessageId: state.pendingMessageId === id ? null : state.pendingMessageId,
        }));
      },

      clearMessages: () => {
        set({ messages: [], pendingMessageId: null, isStreaming: false });
      },

      setStreaming: (streaming, messageId) => {
        set({
          isStreaming: streaming,
          pendingMessageId: streaming ? messageId || null : null,
        });
      },

      getPendingMessage: () => {
        const { messages, pendingMessageId } = get();
        if (!pendingMessageId) return null;
        return messages.find((msg) => msg.id === pendingMessageId) || null;
      },

      deduplicateMessages: () => {
        set((state) => {
          const seen = new Set<string>();
          const deduplicated = state.messages.filter((msg) => {
            const key = `${msg.role}-${msg.content}-${msg.timestamp}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
          });
          return { messages: deduplicated };
        });
      },
    }),
    {
      name: 'archestra-chat-storage',
      partialize: (state) => ({
        messages: state.messages.map((msg) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp,
          status: msg.status === 'streaming' ? 'sent' : msg.status,
        })),
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.deduplicateMessages();
          state.setStreaming(false);
        }
      },
    }
  )
);
