/**
 * API service for HTTP requests to the backend using V2 hierarchical endpoints
 */

const API_BASE_URL = process.env.NODE_ENV === 'development' 
  ? 'http://localhost:8000/api/v2'
  : '/api/v2';

export interface Project {
  id: string;
  name: string;
  description: string;
  status: 'active' | 'archived';
  created_at: string;
  updated_at: string;
  topics_count: number;
  plans_count: number;
  tasks_count: number;
  total_cost: number;
  completion_rate: number;
  metadata: Record<string, any>;
}

export interface ResearchTopic {
  id: string;
  project_id: string;
  name: string;
  description: string;
  status: 'active' | 'paused' | 'completed' | 'archived';
  created_at: string;
  updated_at: string;
  plans_count: number;
  tasks_count: number;
  total_cost: number;
  completion_rate: number;
  metadata: Record<string, any>;
}

export interface ResearchPlan {
  id: string;
  topic_id: string;
  name: string;
  description: string;
  plan_type: 'comprehensive' | 'quick' | 'deep' | 'custom';
  status: 'draft' | 'active' | 'completed' | 'cancelled';
  plan_approved: boolean;
  created_at: string;
  updated_at: string;
  estimated_cost: number;
  actual_cost: number;
  task_count: number;
  completed_tasks: number;
  progress: number;
  plan_structure: Record<string, any>;
  metadata: Record<string, any>;
}

export interface Task {
  id: string;
  plan_id: string;
  name: string;
  description: string;
  task_type: 'research' | 'analysis' | 'synthesis' | 'validation';
  task_order: number;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  stage: 'planning' | 'retrieval' | 'reasoning' | 'execution' | 'synthesis' | 'complete' | 'failed';
  created_at: string;
  updated_at: string;
  estimated_cost: number;
  actual_cost: number;
  cost_approved: boolean;
  single_agent_mode: boolean;
  max_results: number;
  progress: number;
  query?: string;
  search_results?: Array<Record<string, any>>;
  reasoning_output?: string;
  execution_results?: Array<Record<string, any>>;
  synthesis?: string;
  metadata?: Record<string, any>;
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

  // Research Topics methods
  async getResearchTopics(projectId: string, status?: string): Promise<ResearchTopic[]> {
    const url = status ? `/projects/${projectId}/topics?status=${status}` : `/projects/${projectId}/topics`;
    return this.request<ResearchTopic[]>(url);
  }

  async createResearchTopic(projectId: string, data: { name: string; description?: string }): Promise<ResearchTopic> {
    return this.request<ResearchTopic>(`/projects/${projectId}/topics`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteResearchTopic(topicId: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/topics/${topicId}`, {
      method: 'DELETE',
    });
  }

  // Research Plans methods
  async getResearchPlans(topicId: string, status?: string): Promise<ResearchPlan[]> {
    const url = status ? `/topics/${topicId}/plans?status=${status}` : `/topics/${topicId}/plans`;
    return this.request<ResearchPlan[]>(url);
  }

  async createResearchPlan(topicId: string, data: { 
    name: string; 
    description?: string; 
    plan_type?: 'comprehensive' | 'quick' | 'deep' | 'custom';
  }): Promise<ResearchPlan> {
    return this.request<ResearchPlan>(`/topics/${topicId}/plans`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteResearchPlan(planId: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/plans/${planId}`, {
      method: 'DELETE',
    });
  }

  // Tasks methods
  async getTasks(planId: string, status?: string): Promise<Task[]> {
    const url = status ? `/plans/${planId}/tasks?status=${status}` : `/plans/${planId}/tasks`;
    return this.request<Task[]>(url);
  }

  async createTask(planId: string, data: {
    name: string;
    description?: string;
    task_type?: 'research' | 'analysis' | 'synthesis' | 'validation';
    query?: string;
    max_results?: number;
  }): Promise<Task> {
    return this.request<Task>(`/plans/${planId}/tasks`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteTask(taskId: string): Promise<{ success: boolean; message: string }> {
    return this.request<{ success: boolean; message: string }>(`/tasks/${taskId}`, {
      method: 'DELETE',
    });
  }

  async executeTask(taskId: string): Promise<Task> {
    return this.request<Task>(`/tasks/${taskId}/execute`, {
      method: 'POST',
    });
  }

  async getResearchTask(taskId: string): Promise<Task> {
    return this.request<Task>(`/tasks/${taskId}`);
  }

  async getProjectResearchTasks(projectId: string): Promise<Task[]> {
    try {
      const topics = await this.getResearchTopics(projectId);
      const allTasks: Task[] = [];
      
      for (const topic of topics) {
        const plans = await this.getResearchPlans(topic.id);
        for (const plan of plans) {
          const tasks = await this.getTasks(plan.id);
          allTasks.push(...tasks);
        }
      }
      
      return allTasks;
    } catch (error) {
      console.warn('Failed to load hierarchical tasks, returning empty array:', error);
      return [];
    }
  }

  // Health check - using v1 endpoint as v2 might not have it yet
  async getHealth(): Promise<{
    status: string;
    database: Record<string, any>;
    ai_providers: Record<string, any>;
    research_system: Record<string, any>;
    mcp_server: Record<string, any>;
    errors: Record<string, any>;
  }> {
    // Use the original API path for health check
    const originalBaseUrl = process.env.NODE_ENV === 'development' 
      ? 'http://localhost:8000/api'
      : '/api';
    
    const response = await fetch(`${originalBaseUrl}/health`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }
}

export const apiService = new ApiService();
