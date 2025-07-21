/**
 * API service for hierarchical research operations
 * Handles Project → Research Topic → Plan → Tasks API calls
 */

// Note: Keeping these types here for future API integration
// eslint-disable-next-line @typescript-eslint/no-unused-vars
import {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  Project,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  ResearchTopic,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  ResearchPlan,
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  Task,
  ResearchTopicRequest,
  ResearchPlanRequest,
  TaskRequest,
  ProjectHierarchy,
  ResearchTopicResponse,
  ResearchPlanResponse,
  TaskResponse
} from '../types/hierarchical'

class HierarchicalResearchAPI {
  private baseUrl: string

  constructor(baseUrl: string = 'http://localhost:8000') {
    this.baseUrl = baseUrl
  }

  // ============================================================================
  // RESEARCH TOPICS
  // ============================================================================

  async getResearchTopics(projectId: string, status?: string): Promise<ResearchTopicResponse[]> {
    const url = new URL(`${this.baseUrl}/api/v2/projects/${projectId}/topics`)
    if (status) {
      url.searchParams.append('status', status)
    }

    const response = await fetch(url.toString())
    if (!response.ok) {
      throw new Error(`Failed to fetch research topics: ${response.statusText}`)
    }

    return response.json()
  }

  async getResearchTopic(topicId: string): Promise<ResearchTopicResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/topics/${topicId}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch research topic: ${response.statusText}`)
    }

    return response.json()
  }

  async createResearchTopic(
    projectId: string,
    topicData: ResearchTopicRequest
  ): Promise<ResearchTopicResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/projects/${projectId}/topics`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(topicData),
    })

    if (!response.ok) {
      throw new Error(`Failed to create research topic: ${response.statusText}`)
    }

    return response.json()
  }

  async updateResearchTopic(
    topicId: string,
    updates: Partial<ResearchTopicRequest>
  ): Promise<ResearchTopicResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/topics/${topicId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    })

    if (!response.ok) {
      throw new Error(`Failed to update research topic: ${response.statusText}`)
    }

    return response.json()
  }

  async deleteResearchTopic(topicId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v2/topics/${topicId}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      throw new Error(`Failed to delete research topic: ${response.statusText}`)
    }
  }

  // ============================================================================
  // RESEARCH PLANS
  // ============================================================================

  async getResearchPlans(topicId: string, status?: string): Promise<ResearchPlanResponse[]> {
    const url = new URL(`${this.baseUrl}/api/v2/topics/${topicId}/plans`)
    if (status) {
      url.searchParams.append('status', status)
    }

    const response = await fetch(url.toString())
    if (!response.ok) {
      throw new Error(`Failed to fetch research plans: ${response.statusText}`)
    }

    return response.json()
  }

  async getResearchPlan(planId: string): Promise<ResearchPlanResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/plans/${planId}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch research plan: ${response.statusText}`)
    }

    return response.json()
  }

  async createResearchPlan(
    topicId: string,
    planData: ResearchPlanRequest
  ): Promise<ResearchPlanResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/topics/${topicId}/plans`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(planData),
    })

    if (!response.ok) {
      throw new Error(`Failed to create research plan: ${response.statusText}`)
    }

    return response.json()
  }

  async updateResearchPlan(
    planId: string,
    updates: Partial<ResearchPlanRequest>
  ): Promise<ResearchPlanResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/plans/${planId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    })

    if (!response.ok) {
      throw new Error(`Failed to update research plan: ${response.statusText}`)
    }

    return response.json()
  }

  async deleteResearchPlan(planId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v2/plans/${planId}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      throw new Error(`Failed to delete research plan: ${response.statusText}`)
    }
  }

  // ============================================================================
  // TASKS
  // ============================================================================

  async getTasks(
    planId: string,
    status?: string,
    taskType?: string
  ): Promise<TaskResponse[]> {
    const url = new URL(`${this.baseUrl}/api/v2/plans/${planId}/tasks`)
    if (status) {
      url.searchParams.append('status', status)
    }
    if (taskType) {
      url.searchParams.append('task_type', taskType)
    }

    const response = await fetch(url.toString())
    if (!response.ok) {
      throw new Error(`Failed to fetch tasks: ${response.statusText}`)
    }

    return response.json()
  }

  async getTask(taskId: string): Promise<TaskResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/tasks/${taskId}`)
    if (!response.ok) {
      throw new Error(`Failed to fetch task: ${response.statusText}`)
    }

    return response.json()
  }

  async createTask(planId: string, taskData: TaskRequest): Promise<TaskResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/plans/${planId}/tasks`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(taskData),
    })

    if (!response.ok) {
      throw new Error(`Failed to create task: ${response.statusText}`)
    }

    return response.json()
  }

  async updateTask(taskId: string, updates: Partial<TaskRequest>): Promise<TaskResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/tasks/${taskId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updates),
    })

    if (!response.ok) {
      throw new Error(`Failed to update task: ${response.statusText}`)
    }

    return response.json()
  }

  async deleteTask(taskId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v2/tasks/${taskId}`, {
      method: 'DELETE',
    })

    if (!response.ok) {
      throw new Error(`Failed to delete task: ${response.statusText}`)
    }
  }

  async executeTask(taskId: string): Promise<TaskResponse> {
    const response = await fetch(`${this.baseUrl}/api/v2/tasks/${taskId}/execute`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`Failed to execute task: ${response.statusText}`)
    }

    return response.json()
  }

  async cancelTask(taskId: string): Promise<void> {
    const response = await fetch(`${this.baseUrl}/api/v2/tasks/${taskId}/cancel`, {
      method: 'POST',
    })

    if (!response.ok) {
      throw new Error(`Failed to cancel task: ${response.statusText}`)
    }
  }

  // ============================================================================
  // HIERARCHICAL NAVIGATION
  // ============================================================================

  async getProjectHierarchy(projectId: string): Promise<ProjectHierarchy> {
    const response = await fetch(`${this.baseUrl}/api/v2/projects/${projectId}/hierarchy`)
    if (!response.ok) {
      throw new Error(`Failed to fetch project hierarchy: ${response.statusText}`)
    }

    return response.json()
  }

  // ============================================================================
  // SEARCH AND FILTERING
  // ============================================================================

  async searchAcrossHierarchy(
    projectId: string,
    query: string,
    filters?: {
      types?: ('topic' | 'plan' | 'task')[]
      status?: string[]
    }
  ): Promise<{
    topics: ResearchTopicResponse[]
    plans: ResearchPlanResponse[]
    tasks: TaskResponse[]
  }> {
    const url = new URL(`${this.baseUrl}/api/v2/projects/${projectId}/search`)
    url.searchParams.append('q', query)
    
    if (filters?.types) {
      filters.types.forEach(type => url.searchParams.append('types', type))
    }
    if (filters?.status) {
      filters.status.forEach(status => url.searchParams.append('status', status))
    }

    const response = await fetch(url.toString())
    if (!response.ok) {
      throw new Error(`Failed to search hierarchy: ${response.statusText}`)
    }

    return response.json()
  }

  // ============================================================================
  // BULK OPERATIONS
  // ============================================================================

  async bulkCreateTasks(planId: string, tasks: TaskRequest[]): Promise<TaskResponse[]> {
    const response = await fetch(`${this.baseUrl}/api/v2/plans/${planId}/tasks/bulk`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ tasks }),
    })

    if (!response.ok) {
      throw new Error(`Failed to bulk create tasks: ${response.statusText}`)
    }

    return response.json()
  }

  async bulkUpdateTaskStatus(
    taskIds: string[],
    status: string
  ): Promise<TaskResponse[]> {
    const response = await fetch(`${this.baseUrl}/api/v2/tasks/bulk/status`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ task_ids: taskIds, status }),
    })

    if (!response.ok) {
      throw new Error(`Failed to bulk update task status: ${response.statusText}`)
    }

    return response.json()
  }

  // ============================================================================
  // STATISTICS AND ANALYTICS
  // ============================================================================

  async getProjectStats(projectId: string): Promise<{
    topics_count: number
    plans_count: number
    tasks_count: number
    total_cost: number
    completion_rate: number
  }> {
    const response = await fetch(`${this.baseUrl}/api/v2/projects/${projectId}/stats`)
    if (!response.ok) {
      throw new Error(`Failed to fetch project stats: ${response.statusText}`)
    }

    return response.json()
  }

  async getTopicStats(topicId: string): Promise<{
    plans_count: number
    tasks_count: number
    total_cost: number
    completion_rate: number
  }> {
    const response = await fetch(`${this.baseUrl}/api/v2/topics/${topicId}/stats`)
    if (!response.ok) {
      throw new Error(`Failed to fetch topic stats: ${response.statusText}`)
    }

    return response.json()
  }

  async getPlanStats(planId: string): Promise<{
    tasks_count: number
    completed_tasks: number
    total_cost: number
    progress: number
  }> {
    const response = await fetch(`${this.baseUrl}/api/v2/plans/${planId}/stats`)
    if (!response.ok) {
      throw new Error(`Failed to fetch plan stats: ${response.statusText}`)
    }

    return response.json()
  }

  // ============================================================================
  // LEGACY COMPATIBILITY
  // ============================================================================

  async getLegacyResearchTasks(projectId?: string): Promise<TaskResponse[]> {
    // Use a more robust deprecation warning that can be controlled
    if (process.env.NODE_ENV === 'development') {
      console.warn(
        '⚠️  [DEPRECATED] getLegacyResearchTasks() is deprecated. ' +
        'Please migrate to the hierarchical structure using getTasksByPlan().'
      )
    }
    
    const url = projectId 
      ? `${this.baseUrl}/api/projects/${projectId}/research-tasks`
      : `${this.baseUrl}/api/research-tasks`
    
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`Failed to fetch legacy research tasks: ${response.statusText}`)
    }

    return response.json()
  }

  async startLegacyResearchTask(request: {
    project_id: string
    conversation_id: string
    query: string
    name?: string
    research_mode?: string
    max_results?: number
  }): Promise<TaskResponse> {
    console.warn('⚠️  Using deprecated endpoint. Consider creating tasks within plans.')
    
    const response = await fetch(`${this.baseUrl}/api/research/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(request),
    })

    if (!response.ok) {
      throw new Error(`Failed to start legacy research task: ${response.statusText}`)
    }

    return response.json()
  }
}

// Export singleton instance
export const hierarchicalAPI = new HierarchicalResearchAPI()

// Export class for custom instances
export { HierarchicalResearchAPI }

// Utility function to determine base URL
export const getAPIBaseURL = (): string => {
  if (typeof window !== 'undefined') {
    // Browser environment
    return window.location.origin
  }
  // Node.js environment (SSR)
  return process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000'
}
