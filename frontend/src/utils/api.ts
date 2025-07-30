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

  async getTopicById(topicId: string): Promise<Topic> {
    if (await isBackendAvailable()) {
      try {
        // In real implementation, this would be a different endpoint or modified to get topic by ID only
        return await apiRequest(`/v2/topics/${topicId}`)
      } catch (error) {
        console.warn("Backend topic API failed, falling back to mock data:", error)
        return mockApiClient.getTopicById(topicId)
      }
    } else {
      console.info("Backend not available, using mock topic data")
      return mockApiClient.getTopicById(topicId)
    }
  },

  // Research Plan methods
  async getResearchPlans(topicId: string): Promise<ResearchPlan[]> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/topics/${topicId}/plans`)
      } catch (error) {
        console.warn("Backend research plan API failed, falling back to mock data:", error)
        return mockApiClient.getResearchPlans(topicId)
      }
    } else {
      console.info("Backend not available, using mock research plan data")
      return mockApiClient.getResearchPlans(topicId)
    }
  },

  async getResearchPlan(planId: string): Promise<ResearchPlan> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/plans/${planId}`)
      } catch (error) {
        console.warn("Backend research plan API failed, falling back to mock data:", error)
        return mockApiClient.getResearchPlan(planId)
      }
    } else {
      console.info("Backend not available, using mock research plan data")
      return mockApiClient.getResearchPlan(planId)
    }
  },

  async createResearchPlan(topicId: string, plan: CreateResearchPlanRequest): Promise<ResearchPlan> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/topics/${topicId}/plans`, {
          method: "POST",
          body: JSON.stringify(plan),
        })
      } catch (error) {
        console.warn("Backend research plan API failed, falling back to mock data:", error)
        return mockApiClient.createResearchPlan(topicId, plan)
      }
    } else {
      console.info("Backend not available, using mock research plan data")
      return mockApiClient.createResearchPlan(topicId, plan)
    }
  },

  async updateResearchPlan(planId: string, plan: UpdateResearchPlanRequest): Promise<ResearchPlan> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/plans/${planId}`, {
          method: "PUT",
          body: JSON.stringify(plan),
        })
      } catch (error) {
        console.warn("Backend research plan API failed, falling back to mock data:", error)
        return mockApiClient.updateResearchPlan(planId, plan)
      }
    } else {
      console.info("Backend not available, using mock research plan data")
      return mockApiClient.updateResearchPlan(planId, plan)
    }
  },

  async deleteResearchPlan(planId: string): Promise<void> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/plans/${planId}`, {
          method: "DELETE",
        })
      } catch (error) {
        console.warn("Backend research plan API failed, falling back to mock data:", error)
        return mockApiClient.deleteResearchPlan(planId)
      }
    } else {
      console.info("Backend not available, using mock research plan data")
      return mockApiClient.deleteResearchPlan(planId)
    }
  },

  async approveResearchPlan(planId: string): Promise<ResearchPlan> {
    if (await isBackendAvailable()) {
      try {
        return await apiRequest(`/v2/plans/${planId}/approve`, {
          method: "POST",
        })
      } catch (error) {
        console.warn("Backend research plan API failed, falling back to mock data:", error)
        return mockApiClient.approveResearchPlan(planId)
      }
    } else {
      console.info("Backend not available, using mock research plan data")
      return mockApiClient.approveResearchPlan(planId)
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
