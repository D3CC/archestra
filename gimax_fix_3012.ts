// src/store/chatStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: number;
  status: 'sending' | 'sent' | 'streaming' | 'completed' | 'error';
  pendingId?: string; // 用于追踪未完成的消息
}

interface ChatState {
  messages: Message[];
  isStreaming: boolean;
  addMessage: (message: Omit<Message, 'id' | 'timestamp'>) => string;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  removeMessage: (id: string) => void;
  clearMessages: () => void;
  setStreaming: (streaming: boolean) => void;
  getPendingMessages: () => Message[];
  finalizePendingMessages: () => void;
}

// 用于在页面刷新时保留pendingId的临时存储
const pendingMessageIds = new Set<string>();

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      isStreaming: false,

      addMessage: (message) => {
        const id = uuidv4();
        const newMessage: Message = {
          ...message,
          id,
          timestamp: Date.now(),
        };

        // 如果是流式消息，记录pendingId
        if (message.status === 'streaming' || message.status === 'sending') {
          pendingMessageIds.add(id);
          newMessage.pendingId = id;
        }

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

        // 如果消息完成或出错，从pending集合中移除
        if (
          updates.status === 'completed' ||
          updates.status === 'error'
        ) {
          pendingMessageIds.delete(id);
        }
      },

      removeMessage: (id) => {
        pendingMessageIds.delete(id);
        set((state) => ({
          messages: state.messages.filter((msg) => msg.id !== id),
        }));
      },

      clearMessages: () => {
        pendingMessageIds.clear();
        set({ messages: [], isStreaming: false });
      },

      setStreaming: (streaming) => {
        set({ isStreaming: streaming });
      },

      getPendingMessages: () => {
        return get().messages.filter((msg) => pendingMessageIds.has(msg.id));
      },

      finalizePendingMessages: () => {
        // 在页面加载时调用，处理未完成的消息
        const pendingMessages = get().messages.filter((msg) =>
          pendingMessageIds.has(msg.id)
        );

        if (pendingMessages.length > 0) {
          set((state) => ({
            messages: state.messages.map((msg) =>
              pendingMessageIds.has(msg.id)
                ? { ...msg, status: 'error', content: msg.content || '[消息未完成]' }
                : msg
            ),
          }));
          pendingMessageIds.clear();
        }
      },
    }),
    {
      name: 'chat-storage',
      partialize: (state) => ({
        messages: state.messages.map((msg) => ({
          ...msg,
          // 不持久化流式状态，页面加载后重新标记
          status: msg.status === 'streaming' ? 'sending' : msg.status,
        })),
      }),
      onRehydrateStorage: () => {
        // 页面加载完成后，处理未完成的消息
        return (state) => {
          if (state) {
            state.finalizePendingMessages();
          }
        };
      },
    }
  )
);
