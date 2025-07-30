/**
 * API client utilities for communicating with the Eunice backend
 */

const API_BASE_URL = "/api" // This will be proxied to http://localhost:8001

// Types for project data
export interface Project {
  id: string
  name: string
  description?: string
  status: string
  created_at: string
  updated_at: string
  metadata?: Record<string, any>
}

export interface CreateProjectRequest {
  name: string
  description?: string
  metadata?: Record<string, any>
}

export interface UpdateProjectRequest {
  name?: string
  description?: string
  status?: string
  metadata?: Record<string, any>
}

// Types for topic data
export interface Topic {
  id: string
  name: string
  description?: string
  project_id: string
  created_at: string
  updated_at: string
  status?: string
  plans_count?: number
  tasks_count?: number
  total_cost?: number
  completion_rate?: number
  metadata?: Record<string, any>
}

export interface CreateTopicRequest {
  name: string
  description?: string
  project_id: string
  metadata?: Record<string, any>
}

export interface UpdateTopicRequest {
  name?: string
  description?: string
  metadata?: Record<string, any>
}

// Types for research plan data
export interface ResearchPlan {
  id: string
  topic_id: string
  name: string
  description?: string
  plan_type: string
  status: string
  plan_approved: boolean
  created_at: string
  updated_at: string
  estimated_cost: number
  actual_cost: number
  tasks_count?: number
  completed_tasks?: number
  progress?: number
  plan_structure?: Record<string, any>
  metadata?: Record<string, any>
}

export interface CreateResearchPlanRequest {
  name: string
  description?: string
  plan_type?: string
  plan_structure?: Record<string, any>
  metadata?: Record<string, any>
}

export interface UpdateResearchPlanRequest {
  name?: string
  description?: string
  plan_type?: string
  status?: string
  plan_structure?: Record<string, any>
  metadata?: Record<string, any>
}

/**
 * Generic API request function
 */
async function apiRequest(
  endpoint: string,
  options: RequestInit = {}
): Promise<any> {
  const url = `${API_BASE_URL}${endpoint}`

  const defaultOptions: RequestInit = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  }

  const response = await fetch(url, { ...defaultOptions, ...options })

  if (!response.ok) {
    throw new Error(
      `API request failed: ${response.status} ${response.statusText}`
    )
  }

  return response.json()
}

/**
 * API client methods for communicating with the Eunice backend
 */
export const apiClient = {
  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return await apiRequest("/health")
  },

  // Project methods
  async getProjects(): Promise<Project[]> {
    return await apiRequest("/v2/projects")
  },

  async getProject(id: string): Promise<Project> {
    return await apiRequest(`/v2/projects/${id}`)
  },

  async createProject(project: CreateProjectRequest): Promise<Project> {
    return await apiRequest("/v2/projects", {
      method: "POST",
      body: JSON.stringify(project),
    })
  },

  async updateProject(
    id: string,
    project: UpdateProjectRequest
  ): Promise<Project> {
    return await apiRequest(`/v2/projects/${id}`, {
      method: "PUT",
      body: JSON.stringify(project),
    })
  },

  async deleteProject(id: string): Promise<void> {
    return await apiRequest(`/v2/projects/${id}`, {
      method: "DELETE",
    })
  },

  // Topic methods
  async getTopics(projectId: string): Promise<Topic[]> {
    return await apiRequest(`/v2/projects/${projectId}/topics`)
  },

  async getTopic(projectId: string, topicId: string): Promise<Topic> {
    return await apiRequest(`/v2/projects/${projectId}/topics/${topicId}`)
  },

  async createTopic(topic: CreateTopicRequest): Promise<Topic> {
    return await apiRequest(`/v2/projects/${topic.project_id}/topics`, {
      method: "POST",
      body: JSON.stringify(topic),
    })
  },

  async updateTopic(
    projectId: string,
    topicId: string,
    topic: UpdateTopicRequest
  ): Promise<Topic> {
    return await apiRequest(`/v2/projects/${projectId}/topics/${topicId}`, {
      method: "PUT",
      body: JSON.stringify(topic),
    })
  },

  async deleteTopic(projectId: string, topicId: string): Promise<void> {
    return await apiRequest(`/v2/projects/${projectId}/topics/${topicId}`, {
      method: "DELETE",
    })
  },

  async getTopicById(topicId: string): Promise<Topic> {
    // In real implementation, this would be a different endpoint or modified to get topic by ID only
    return await apiRequest(`/v2/topics/${topicId}`)
  },

  // Research Plan methods
  async getResearchPlans(topicId: string): Promise<ResearchPlan[]> {
    return await apiRequest(`/v2/topics/${topicId}/plans`)
  },

  async getResearchPlan(planId: string): Promise<ResearchPlan> {
    return await apiRequest(`/v2/plans/${planId}`)
  },

  async createResearchPlan(
    topicId: string,
    plan: CreateResearchPlanRequest
  ): Promise<ResearchPlan> {
    return await apiRequest(`/v2/topics/${topicId}/plans`, {
      method: "POST",
      body: JSON.stringify(plan),
    })
  },

  async updateResearchPlan(
    planId: string,
    plan: UpdateResearchPlanRequest
  ): Promise<ResearchPlan> {
    return await apiRequest(`/v2/plans/${planId}`, {
      method: "PUT",
      body: JSON.stringify(plan),
    })
  },

  async deleteResearchPlan(planId: string): Promise<void> {
    return await apiRequest(`/v2/plans/${planId}`, {
      method: "DELETE",
    })
  },

  async approveResearchPlan(planId: string): Promise<ResearchPlan> {
    return await apiRequest(`/v2/plans/${planId}/approve`, {
      method: "POST",
    })
  },

  // Future API methods can be added here
  // async getTasks(): Promise<Task[]> {
  //   return apiRequest('/tasks')
  // },

  // async createTask(task: CreateTaskRequest): Promise<Task> {
  //   return apiRequest('/tasks', {
  //     method: 'POST',
  //     body: JSON.stringify(task)
  //   })
  // },
}

export default apiClient
