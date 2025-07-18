import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { apiService, CreateConversationRequest, ResearchTaskResponse, ResearchProgressUpdate } from '../../services/api';

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
  // Research-specific fields
  task_id?: string;
  research_query?: string;
  research_stage?: string;
  research_progress?: number;
  research_results?: any;
  research_error?: string;
}

export interface ResearchTask {
  task_id: string;
  conversation_id: string;
  query: string;
  status: string;
  created_at: string;
  updated_at: string;
  progress: number;
  results?: any;
  error?: string;
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
  // Research-related state
  researchTasks: { [conversationId: string]: ResearchTask[] };
  activeResearchTask: ResearchTask | null;
  isResearchMode: boolean;
  researchConnectionStatus: 'disconnected' | 'connecting' | 'connected' | 'error';
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
  // Research-related state
  researchTasks: {},
  activeResearchTask: null,
  isResearchMode: false,
  researchConnectionStatus: 'disconnected',
};

// Async thunks
export const createNewConversation = createAsyncThunk(
  'chat/createNewConversation',
  async (data: CreateConversationRequest) => {
    const response = await apiService.createConversation(data);
    // Convert API response to Conversation interface
    return {
      id: response.id,
      project_id: response.project_id,
      title: response.title,
      status: response.status,
      created_at: response.created_at,
      updated_at: response.updated_at,
      message_count: response.message_count,
    } as Conversation;
  }
);

export const loadConversations = createAsyncThunk(
  'chat/loadConversations',
  async (projectId?: string) => {
    return await apiService.getConversations(projectId);
  }
);

export const startResearchTask = createAsyncThunk(
  'chat/startResearchTask',
  async (data: { conversationId: string; query: string; researchMode: 'comprehensive' | 'quick' | 'deep' }) => {
    const response = await apiService.startResearchTask({
      conversation_id: data.conversationId,
      query: data.query,
      research_mode: data.researchMode,
      max_results: 10,
    });
    return response;
  }
);

export const cancelResearchTask = createAsyncThunk(
  'chat/cancelResearchTask',
  async (taskId: string) => {
    await apiService.cancelResearchTask(taskId);
    return taskId;
  }
);

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
    setResearchConnectionStatus: (state, action: PayloadAction<ChatState['researchConnectionStatus']>) => {
      state.researchConnectionStatus = action.payload;
    },
    setResearchMode: (state, action: PayloadAction<boolean>) => {
      state.isResearchMode = action.payload;
    },
    setActiveResearchTask: (state, action: PayloadAction<ResearchTask | null>) => {
      state.activeResearchTask = action.payload;
    },
    addResearchTask: (state, action: PayloadAction<ResearchTask>) => {
      const task = action.payload;
      if (!state.researchTasks[task.conversation_id]) {
        state.researchTasks[task.conversation_id] = [];
      }
      state.researchTasks[task.conversation_id].push(task);
    },
    updateResearchTask: (state, action: PayloadAction<Partial<ResearchTask> & { task_id: string }>) => {
      const update = action.payload;
      Object.values(state.researchTasks).forEach(tasks => {
        const task = tasks.find(t => t.task_id === update.task_id);
        if (task) {
          Object.assign(task, update);
        }
      });
      
      // Update active task if it matches
      if (state.activeResearchTask?.task_id === update.task_id) {
        Object.assign(state.activeResearchTask, update);
      }
    },
    removeResearchTask: (state, action: PayloadAction<string>) => {
      const taskId = action.payload;
      Object.values(state.researchTasks).forEach(tasks => {
        const index = tasks.findIndex(t => t.task_id === taskId);
        if (index >= 0) {
          tasks.splice(index, 1);
        }
      });
      
      // Clear active task if it matches
      if (state.activeResearchTask?.task_id === taskId) {
        state.activeResearchTask = null;
      }
    },
    handleResearchProgress: (state, action: PayloadAction<ResearchProgressUpdate>) => {
      const update = action.payload;
      
      // Update the research task
      if (update.task_id) {
        Object.values(state.researchTasks).forEach(tasks => {
          const task = tasks.find(t => t.task_id === update.task_id);
          if (task) {
            if (update.progress !== undefined) task.progress = update.progress;
            if (update.message) task.status = update.message;
            if (update.results) task.results = update.results;
            if (update.error) task.error = update.error;
          }
        });
        
        // Update active task if it matches
        if (state.activeResearchTask?.task_id === update.task_id) {
          if (update.progress !== undefined) state.activeResearchTask.progress = update.progress;
          if (update.message) state.activeResearchTask.status = update.message;
          if (update.results) state.activeResearchTask.results = update.results;
          if (update.error) state.activeResearchTask.error = update.error;
        }
      }
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
          
        case 'research_started':
          // Handle research task started
          state.isResearchMode = true;
          if (update.task_id && update.research_query && state.currentConversationId) {
            const newTask: ResearchTask = {
              task_id: update.task_id,
              conversation_id: state.currentConversationId,
              query: update.research_query,
              status: 'starting',
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              progress: 0,
            };
            
            if (!state.researchTasks[state.currentConversationId]) {
              state.researchTasks[state.currentConversationId] = [];
            }
            state.researchTasks[state.currentConversationId].push(newTask);
            state.activeResearchTask = newTask;
          }
          break;
          
        case 'research_progress':
          // Handle research progress updates
          if (update.task_id && update.research_progress !== undefined) {
            Object.values(state.researchTasks).forEach(tasks => {
              const task = tasks.find(t => t.task_id === update.task_id);
              if (task) {
                task.progress = update.research_progress!;
                task.status = update.research_stage || task.status;
                task.updated_at = new Date().toISOString();
              }
            });
            
            if (state.activeResearchTask?.task_id === update.task_id) {
              state.activeResearchTask.progress = update.research_progress!;
              state.activeResearchTask.status = update.research_stage || state.activeResearchTask.status;
              state.activeResearchTask.updated_at = new Date().toISOString();
            }
          }
          break;
          
        case 'research_completed':
          // Handle research completion
          if (update.task_id) {
            Object.values(state.researchTasks).forEach(tasks => {
              const task = tasks.find(t => t.task_id === update.task_id);
              if (task) {
                task.status = 'completed';
                task.progress = 100;
                task.results = update.research_results;
                task.updated_at = new Date().toISOString();
              }
            });
            
            if (state.activeResearchTask?.task_id === update.task_id) {
              state.activeResearchTask.status = 'completed';
              state.activeResearchTask.progress = 100;
              state.activeResearchTask.results = update.research_results;
              state.activeResearchTask.updated_at = new Date().toISOString();
            }
          }
          state.isResearchMode = false;
          break;
          
        case 'research_error':
          // Handle research errors
          if (update.task_id) {
            Object.values(state.researchTasks).forEach(tasks => {
              const task = tasks.find(t => t.task_id === update.task_id);
              if (task) {
                task.status = 'failed';
                task.error = update.research_error || 'Unknown error';
                task.updated_at = new Date().toISOString();
              }
            });
            
            if (state.activeResearchTask?.task_id === update.task_id) {
              state.activeResearchTask.status = 'failed';
              state.activeResearchTask.error = update.research_error || 'Unknown error';
              state.activeResearchTask.updated_at = new Date().toISOString();
            }
          }
          state.isResearchMode = false;
          break;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(createNewConversation.fulfilled, (state, action) => {
        state.conversations.unshift(action.payload);
        state.currentConversationId = action.payload.id;
      })
      .addCase(loadConversations.fulfilled, (state, action) => {
        state.conversations = action.payload;
      })
      .addCase(startResearchTask.fulfilled, (state, action) => {
        const task = action.payload;
        const researchTask: ResearchTask = {
          task_id: task.task_id,
          conversation_id: task.conversation_id,
          query: task.query,
          status: task.status,
          created_at: task.created_at,
          updated_at: task.updated_at,
          progress: task.progress,
          results: task.results,
        };
        
        if (!state.researchTasks[task.conversation_id]) {
          state.researchTasks[task.conversation_id] = [];
        }
        state.researchTasks[task.conversation_id].push(researchTask);
        state.activeResearchTask = researchTask;
        state.isResearchMode = true;
      })
      .addCase(cancelResearchTask.fulfilled, (state, action) => {
        const taskId = action.payload;
        Object.values(state.researchTasks).forEach(tasks => {
          const task = tasks.find(t => t.task_id === taskId);
          if (task) {
            task.status = 'cancelled';
            task.updated_at = new Date().toISOString();
          }
        });
        
        if (state.activeResearchTask?.task_id === taskId) {
          state.activeResearchTask.status = 'cancelled';
          state.activeResearchTask.updated_at = new Date().toISOString();
        }
        state.isResearchMode = false;
      });
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
  setResearchConnectionStatus,
  setResearchMode,
  setActiveResearchTask,
  addResearchTask,
  updateResearchTask,
  removeResearchTask,
  handleResearchProgress,
  handleStreamingUpdate,
} = chatSlice.actions;

export default chatSlice.reducer;
