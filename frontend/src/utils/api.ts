/**
 * API client utilities for communicating with the Eunice backend
 */

import { mockApiClient } from './mockApi'

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
  plan_count?: number
  task_count?: number
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
 * Check if backend is available
 */
async function isBackendAvailable(): Promise<boolean> {
  try {
    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), 2000)
    
    const response = await fetch(`${API_BASE_URL}/health`, { 
      method: 'GET',
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    return response.ok
  } catch {
    return false
  }
}

/**
 * API client methods with automatic fallback to mock data
 */
export const apiClient = {
  // Health check
  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    try {
      return await apiRequest("/health")
    } catch {
      console.warn("Backend not available, using mock data")
      return mockApiClient.healthCheck()
    }
  },

  // Project methods
  async getProjects(): Promise<Project[]> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest("/v2/projects")
      } catch (error) {
        console.warn("Backend project API failed, falling back to mock data:", error)
        return mockApiClient.getProjects()
      }
    } else {
      console.info("Backend not available, using mock project data")
      return mockApiClient.getProjects()
    }
  },

  async getProject(id: string): Promise<Project> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/projects/${id}`)
      } catch (error) {
        console.warn("Backend project API failed, falling back to mock data:", error)
        return mockApiClient.getProject(id)
      }
    } else {
      console.info("Backend not available, using mock project data")
      return mockApiClient.getProject(id)
    }
  },

  async createProject(project: CreateProjectRequest): Promise<Project> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest("/v2/projects", {
          method: "POST",
          body: JSON.stringify(project),
        })
      } catch (error) {
        console.warn("Backend project API failed, falling back to mock data:", error)
        return mockApiClient.createProject(project)
      }
    } else {
      console.info("Backend not available, using mock project data")
      return mockApiClient.createProject(project)
    }
  },

  async updateProject(id: string, project: UpdateProjectRequest): Promise<Project> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/projects/${id}`, {
          method: "PUT",
          body: JSON.stringify(project),
        })
      } catch (error) {
        console.warn("Backend project API failed, falling back to mock data:", error)
        return mockApiClient.updateProject(id, project)
      }
    } else {
      console.info("Backend not available, using mock project data")
      return mockApiClient.updateProject(id, project)
    }
  },

  async deleteProject(id: string): Promise<void> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/projects/${id}`, {
          method: "DELETE",
        })
      } catch (error) {
        console.warn("Backend project API failed, falling back to mock data:", error)
        return mockApiClient.deleteProject(id)
      }
    } else {
      console.info("Backend not available, using mock project data")
      return mockApiClient.deleteProject(id)
    }
  },

  // Topic methods
  async getTopics(projectId: string): Promise<Topic[]> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/projects/${projectId}/topics`)
      } catch (error) {
        console.warn("Backend topic API failed, falling back to mock data:", error)
        return mockApiClient.getTopics(projectId)
      }
    } else {
      console.info("Backend not available, using mock topic data")
      return mockApiClient.getTopics(projectId)
    }
  },

  async getTopic(projectId: string, topicId: string): Promise<Topic> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/projects/${projectId}/topics/${topicId}`)
      } catch (error) {
        console.warn("Backend topic API failed, falling back to mock data:", error)
        return mockApiClient.getTopic(projectId, topicId)
      }
    } else {
      console.info("Backend not available, using mock topic data")
      return mockApiClient.getTopic(projectId, topicId)
    }
  },

  async createTopic(topic: CreateTopicRequest): Promise<Topic> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/projects/${topic.project_id}/topics`, {
          method: "POST",
          body: JSON.stringify(topic),
        })
      } catch (error) {
        console.warn("Backend topic API failed, falling back to mock data:", error)
        return mockApiClient.createTopic(topic)
      }
    } else {
      console.info("Backend not available, using mock topic data")
      return mockApiClient.createTopic(topic)
    }
  },

  async updateTopic(projectId: string, topicId: string, topic: UpdateTopicRequest): Promise<Topic> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/projects/${projectId}/topics/${topicId}`, {
          method: "PUT",
          body: JSON.stringify(topic),
        })
      } catch (error) {
        console.warn("Backend topic API failed, falling back to mock data:", error)
        return mockApiClient.updateTopic(projectId, topicId, topic)
      }
    } else {
      console.info("Backend not available, using mock topic data")
      return mockApiClient.updateTopic(projectId, topicId, topic)
    }
  },

  async deleteTopic(projectId: string, topicId: string): Promise<void> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/projects/${projectId}/topics/${topicId}`, {
          method: "DELETE",
        })
      } catch (error) {
        console.warn("Backend topic API failed, falling back to mock data:", error)
        return mockApiClient.deleteTopic(projectId, topicId)
      }
    } else {
      console.info("Backend not available, using mock topic data")
      return mockApiClient.deleteTopic(projectId, topicId)
    }
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
