import { createSlice, PayloadAction } from '@reduxjs/toolkit';

export interface Message {
  id: string;
  conversation_id: string;
  participant: 'user' | 'openai' | 'xai';
  content: string;
  timestamp: string;
  streaming?: boolean;
}

export interface Conversation {
  id: string;
  project_id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface StreamingUpdate {
  type: string;
  provider?: string;
  content?: string;
  chunk?: string;
  message?: Message | string;
  queue?: string[];
  total_providers?: number;
}

interface ChatState {
  conversations: Conversation[];
  currentConversationId: string | null;
  messages: { [conversationId: string]: Message[] };
  isStreaming: boolean;
  streamingProvider: string | null;
  providerQueue: string[];
  connectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
  currentStreamingMessage: string;
}

const initialState: ChatState = {
  conversations: [],
  currentConversationId: null,
  messages: {},
  isStreaming: false,
  streamingProvider: null,
  providerQueue: [],
  connectionStatus: 'disconnected',
  currentStreamingMessage: '',
};

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setConversations: (state, action: PayloadAction<Conversation[]>) => {
      state.conversations = action.payload;
    },
    addConversation: (state, action: PayloadAction<Conversation>) => {
      state.conversations.unshift(action.payload);
    },
    removeConversation: (state, action: PayloadAction<string>) => {
      const conversationId = action.payload;
      state.conversations = state.conversations.filter(conv => conv.id !== conversationId);
      
      // Remove messages for this conversation
      delete state.messages[conversationId];
      
      // If this was the current conversation, clear it
      if (state.currentConversationId === conversationId) {
        state.currentConversationId = null;
      }
    },
    setCurrentConversation: (state, action: PayloadAction<string>) => {
      state.currentConversationId = action.payload;
    },
    setMessages: (state, action: PayloadAction<{ conversationId: string; messages: Message[] }>) => {
      state.messages[action.payload.conversationId] = action.payload.messages;
    },
    addMessage: (state, action: PayloadAction<Message>) => {
      const conversationId = action.payload.conversation_id;
      if (!state.messages[conversationId]) {
        state.messages[conversationId] = [];
      }
      state.messages[conversationId].push(action.payload);
    },
    setConnectionStatus: (state, action: PayloadAction<ChatState['connectionStatus']>) => {
      state.connectionStatus = action.payload;
    },
    handleStreamingUpdate: (state, action: PayloadAction<StreamingUpdate>) => {
      const update = action.payload;
      
      switch (update.type) {
        case 'user_message':
          // Handle user message from WebSocket
          if (update.message && typeof update.message === 'object' && state.currentConversationId) {
            const userMessage: Message = {
              id: update.message.id,
              conversation_id: update.message.conversation_id,
              participant: update.message.participant as 'user',
              content: update.message.content,
              timestamp: update.message.timestamp,
            };
            
            if (!state.messages[state.currentConversationId]) {
              state.messages[state.currentConversationId] = [];
            }
            state.messages[state.currentConversationId].push(userMessage);
          }
          break;
          
        case 'queue_determined':
          state.providerQueue = update.queue || [];
          state.isStreaming = true;
          break;
          
        case 'provider_starting':
          state.streamingProvider = update.provider || null;
          state.currentStreamingMessage = '';
          break;
          
        case 'provider_response_start':
          // Create a new streaming message
          if (update.provider && state.currentConversationId) {
            const newMessage: Message = {
              id: `streaming-${Date.now()}`,
              conversation_id: state.currentConversationId,
              participant: update.provider as 'openai' | 'xai',
              content: '',
              timestamp: new Date().toISOString(),
              streaming: true,
            };
            
            if (!state.messages[state.currentConversationId]) {
              state.messages[state.currentConversationId] = [];
            }
            state.messages[state.currentConversationId].push(newMessage);
          }
          break;
          
        case 'token':
        case 'response_chunk':
          // Append to current streaming message
          if (state.currentConversationId && state.streamingProvider) {
            const messages = state.messages[state.currentConversationId];
            const lastMessage = messages[messages.length - 1];
            
            if (lastMessage && lastMessage.streaming) {
              lastMessage.content += update.content || update.chunk || '';
            }
          }
          break;
          
        case 'provider_completed':
          // Mark streaming message as complete
          if (state.currentConversationId) {
            const messages = state.messages[state.currentConversationId];
            const lastMessage = messages[messages.length - 1];
            
            if (lastMessage && lastMessage.streaming) {
              lastMessage.streaming = false;
              lastMessage.id = `msg-${Date.now()}`; // Update with proper ID
            }
          }
          state.streamingProvider = null;
          break;
          
        case 'conversation_completed':
          state.isStreaming = false;
          state.providerQueue = [];
          state.streamingProvider = null;
          state.currentStreamingMessage = '';
          break;
      }
    },
  },
});

export const {
  setConversations,
  addConversation,
  removeConversation,
  setCurrentConversation,
  setMessages,
  addMessage,
  setConnectionStatus,
  handleStreamingUpdate,
} = chatSlice.actions;

export default chatSlice.reducer;
