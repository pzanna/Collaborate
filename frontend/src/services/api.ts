/**
 * API service for HTTP requests to the backend
 */

import { Conversation, Message } from '../store/slices/chatSlice';

const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:8000/api'
  : '/api';

export interface CreateConversationRequest {
  project_id: string;
  title: string;
}

export interface CreateConversationResponse {
  id: string;
  project_id: string;
  title: string;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  conversation_count: number;
}

export interface ResearchRequest {
  conversation_id: string;
  query: string;
  research_mode: 'comprehensive' | 'quick' | 'deep';
  max_results: number;
}

export interface ResearchTaskResponse {
  task_id: string;
  conversation_id: string;
  query: string;
  status: string;
  created_at: string;
  updated_at: string;
  progress: number;
  results?: {
    search_results: Array<{
      title: string;
      url: string;
      snippet: string;
      relevance_score: number;
    }>;
    reasoning_output?: string;
    execution_results: Array<any>;
    synthesis?: string;
    metadata: Record<string, any>;
  };
}

export interface ResearchProgressUpdate {
  type: 'research_started' | 'research_progress' | 'research_stage_complete' | 'research_completed' | 'research_error';
  task_id: string;
  stage?: string;
  progress?: number;
  message?: string;
  results?: any;
  error?: string;
}

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  // Conversation methods
  async createConversation(data: CreateConversationRequest): Promise<CreateConversationResponse> {
    return this.request<CreateConversationResponse>('/conversations', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getConversations(projectId?: string): Promise<Conversation[]> {
    const params = projectId ? `?project_id=${projectId}` : '';
    return this.request<Conversation[]>(`/conversations${params}`);
  }

  async getConversationMessages(conversationId: string): Promise<Message[]> {
    return this.request<Message[]>(`/conversations/${conversationId}/messages`);
  }

  // Project methods
  async getProjects(): Promise<Project[]> {
    return this.request<Project[]>('/projects');
  }

  async createProject(data: { name: string; description: string }): Promise<Project> {
    return this.request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteProject(projectId: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/projects/${projectId}`, {
      method: 'DELETE',
    });
  }

  // Research methods
  async startResearchTask(data: ResearchRequest): Promise<ResearchTaskResponse> {
    return this.request<ResearchTaskResponse>('/research/start', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getResearchTask(taskId: string): Promise<ResearchTaskResponse> {
    return this.request<ResearchTaskResponse>(`/research/task/${taskId}`);
  }

  async cancelResearchTask(taskId: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/research/task/${taskId}`, {
      method: 'DELETE',
    });
  }

  // Health check
  async getHealth(): Promise<{
    status: string;
    database: Record<string, any>;
    ai_providers: Record<string, any>;
    research_system: Record<string, any>;
    errors: Record<string, any>;
  }> {
    return this.request('/health');
  }
}

export const apiService = new ApiService();
