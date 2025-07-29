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
 * API client methods
 */
export const apiClient = {
  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return apiRequest("/health")
  },

  // Project methods
  async getProjects(): Promise<Project[]> {
    return apiRequest("/v2/projects")
  },

  async getProject(id: string): Promise<Project> {
    return apiRequest(`/v2/projects/${id}`)
  },

  async createProject(project: CreateProjectRequest): Promise<Project> {
    return apiRequest("/v2/projects", {
      method: "POST",
      body: JSON.stringify(project),
    })
  },

  async updateProject(id: string, project: UpdateProjectRequest): Promise<Project> {
    return apiRequest(`/v2/projects/${id}`, {
      method: "PUT",
      body: JSON.stringify(project),
    })
  },

  async deleteProject(id: string): Promise<void> {
    return apiRequest(`/v2/projects/${id}`, {
      method: "DELETE",
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
