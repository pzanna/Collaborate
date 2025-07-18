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
}

export const apiService = new ApiService();
