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
  setStreaming: (streaming: boolean) => void;
  setPendingMessageId: (id: string | null) => void;
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

      clearMessages: () => {
        set({ messages: [], pendingMessageId: null, isStreaming: false });
      },

      setStreaming: (streaming) => {
        set({ isStreaming: streaming });
      },

      setPendingMessageId: (id) => {
        set({ pendingMessageId: id });
      },

      deduplicateMessages: () => {
        set((state) => {
          const seen = new Set<string>();
          const deduplicated = state.messages.filter((msg) => {
            // Deduplicate by content and role for messages without IDs (legacy)
            const key = msg.id || `${msg.role}-${msg.content}-${msg.timestamp}`;
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
      name: 'archestra-chat-storage',
      version: 2,
      migrate: (persistedState: any, version: number) => {
        if (version === 1) {
          // Migration from v1: ensure all messages have IDs and timestamps
          return {
            ...persistedState,
            messages: persistedState.messages?.map((msg: any) => ({
              ...msg,
              id: msg.id || uuidv4(),
              timestamp: msg.timestamp || Date.now(),
              status: msg.status || 'completed',
            })) || [],
          };
        }
        return persistedState as ChatState;
      },
    }
  )
);
