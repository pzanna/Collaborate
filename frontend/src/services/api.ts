/**
 * API service for HTTP requests to the backend
 */

const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:8000/api'
  : '/api';

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  item_count: number;
  research_task_count: number;  // New field for research task count
}

export interface ResearchRequest {
  project_id: string;  // New required field
  conversation_id: string;
  query: string;
  name?: string;  // Optional human-readable task name
  research_mode: 'comprehensive' | 'quick' | 'deep';
  max_results: number;
}

export interface ResearchTaskResponse {
  task_id: string;
  project_id: string;  // New field
  conversation_id: string;
  query: string;
  name: string;  // Human-readable task name
  status: string;
  stage: string;  // Current stage
  created_at: string;
  updated_at: string;
  progress: number;
  estimated_cost: number;  // New field
  actual_cost: number;     // New field
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

  // Research task listing methods
  async getProjectResearchTasks(projectId: string): Promise<ResearchTaskResponse[]> {
    return this.request<ResearchTaskResponse[]>(`/projects/${projectId}/research-tasks`);
  }

  async getAllResearchTasks(filters?: {
    project_id?: string;
    status?: string;
    limit?: number;
  }): Promise<ResearchTaskResponse[]> {
    const params = new URLSearchParams();
    if (filters?.project_id) params.append('project_id', filters.project_id);
    if (filters?.status) params.append('status', filters.status);
    if (filters?.limit) params.append('limit', filters.limit.toString());
    
    const queryString = params.toString();
    return this.request<ResearchTaskResponse[]>(`/research-tasks${queryString ? `?${queryString}` : ''}`);
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
