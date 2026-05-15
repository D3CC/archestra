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
  setStreaming: (streaming: boolean) => void;
  setPendingMessageId: (id: string | null) => void;
  clearMessages: () => void;
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
        }));
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
        }));
      },

      setStreaming: (streaming) => {
        set({ isStreaming: streaming });
      },

      setPendingMessageId: (id) => {
        set({ pendingMessageId: id });
      },

      clearMessages: () => {
        set({ messages: [], pendingMessageId: null, isStreaming: false });
      },

      deduplicateMessages: () => {
        set((state) => {
          const seen = new Set<string>();
          const deduplicated = state.messages.filter((msg) => {
            const key = `${msg.role}-${msg.content}-${msg.timestamp}`;
            if (seen.has(key)) {
              return false;
            }
            seen.add(key);
            return true;
          });
          return { messages: deduplicated };
        });
      },
    }),
    {
      name: 'chat-storage',
      version: 1,
      migrate: (persistedState: any, version: number) => {
        if (version === 0) {
          // Migration from v0 to v1: add deduplication on load
          return {
            ...persistedState,
            messages: persistedState.messages?.filter(
              (msg: Message, index: number, self: Message[]) =>
                index === self.findIndex(
                  (m) =>
                    m.role === msg.role &&
                    m.content === msg.content &&
                    m.timestamp === msg.timestamp
                )
            ),
          };
        }
        return persistedState;
      },
    }
  )
);
