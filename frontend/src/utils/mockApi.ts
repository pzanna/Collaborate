import type { Project, CreateProjectRequest, UpdateProjectRequest, Topic, CreateTopicRequest, UpdateTopicRequest } from './api'

// Mock data for testing when backend is not available
const mockProjects: Project[] = [
  {
    id: "1",
    name: "Neuroscience Meta-Analysis",
    description: "A comprehensive meta-analysis of recent neuroscience research focusing on cognitive behavioral patterns and neural plasticity.",
    status: "active",
    created_at: "2024-01-15T10:30:00Z",
    updated_at: "2024-01-20T14:22:00Z",
    metadata: {}
  },
  {
    id: "2", 
    name: "Clinical Trial Review",
    description: "Systematic review of Phase III clinical trials for new therapeutic interventions.",
    status: "active",
    created_at: "2024-01-10T09:15:00Z",
    updated_at: "2024-01-18T16:45:00Z",
    metadata: {}
  },
  {
    id: "3",
    name: "Database Integration Study", 
    description: "Research project analyzing the integration patterns of multiple healthcare databases.",
    status: "completed",
    created_at: "2023-12-01T08:00:00Z",
    updated_at: "2024-01-05T12:30:00Z",
    metadata: {}
  }
]

// Mock topic data
const mockTopics: Topic[] = [
  {
    id: "t1",
    name: "Data Collection Methods",
    description: "Research various methods for collecting neurological data from subjects",
    project_id: "1",
    created_at: "2024-01-16T09:00:00Z",
    updated_at: "2024-01-18T11:30:00Z",
    plans_count: 3,
    tasks_count: 8,
    metadata: {}
  },
  {
    id: "t2",
    name: "Statistical Analysis",
    description: "Perform comprehensive statistical analysis on collected data",
    project_id: "1",
    created_at: "2024-01-17T14:15:00Z",
    updated_at: "2024-01-19T16:45:00Z",
    plans_count: 2,
    tasks_count: 5,
    metadata: {}
  },
  {
    id: "t3",
    name: "Literature Review",
    description: "Comprehensive review of existing clinical trial literature",
    project_id: "2",
    created_at: "2024-01-11T10:30:00Z",
    updated_at: "2024-01-15T12:00:00Z",
    plans_count: 4,
    tasks_count: 12,
    metadata: {}
  },
  {
    id: "t4",
    name: "Efficacy Analysis",
    description: "Analyze the efficacy of different therapeutic interventions",
    project_id: "2",
    created_at: "2024-01-12T08:45:00Z",
    updated_at: "2024-01-16T17:20:00Z",
    plans_count: 1,
    tasks_count: 6,
    metadata: {}
  },
  {
    id: "t5",
    name: "Database Schema Design",
    description: "Design optimal database schemas for healthcare data integration",
    project_id: "3",
    created_at: "2023-12-02T11:15:00Z",
    updated_at: "2023-12-20T14:30:00Z",
    plans_count: 2,
    tasks_count: 4,
    metadata: {}
  }
]

const mockProjectsState = [...mockProjects]
let mockTopicsState = [...mockTopics]

/**
 * Mock API methods for when backend is not available
 */
export const mockApiClient = {
  async getProjects(): Promise<Project[]> {
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500))
    return [...mockProjectsState]
  },

  async getProject(id: string): Promise<Project> {
    await new Promise(resolve => setTimeout(resolve, 300))
    const project = mockProjectsState.find(p => p.id === id)
    if (!project) {
      throw new Error('Project not found')
    }
    return project
  },

  async createProject(project: CreateProjectRequest): Promise<Project> {
    await new Promise(resolve => setTimeout(resolve, 400))
    const newProject: Project = {
      id: String(Date.now()),
      name: project.name,
      description: project.description || "",
      status: "active",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: project.metadata || {}
    }
    mockProjectsState.push(newProject)
    return newProject
  },

  async updateProject(id: string, project: UpdateProjectRequest): Promise<Project> {
    await new Promise(resolve => setTimeout(resolve, 400))
    const existingProject = mockProjectsState.find(p => p.id === id)
    if (!existingProject) {
      throw new Error('Project not found')
    }
    
    const updatedProject = {
      ...existingProject,
      ...project,
      updated_at: new Date().toISOString()
    }
    
    const index = mockProjectsState.findIndex(p => p.id === id)
    mockProjectsState[index] = updatedProject
    return updatedProject
  },

  async deleteProject(id: string): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 300))
    const index = mockProjectsState.findIndex(p => p.id === id)
    if (index === -1) {
      throw new Error('Project not found')
    }
    mockProjectsState.splice(index, 1)
  },

  // Topic methods
  async getTopics(projectId: string): Promise<Topic[]> {
    await new Promise(resolve => setTimeout(resolve, 300))
    return mockTopicsState.filter(topic => topic.project_id === projectId)
  },

  async getTopic(projectId: string, topicId: string): Promise<Topic> {
    await new Promise(resolve => setTimeout(resolve, 200))
    const topic = mockTopicsState.find(t => t.id === topicId && t.project_id === projectId)
    if (!topic) {
      throw new Error('Topic not found')
    }
    return topic
  },

  async createTopic(topic: CreateTopicRequest): Promise<Topic> {
    await new Promise(resolve => setTimeout(resolve, 400))
    const newTopic: Topic = {
      id: `t${Date.now()}`,
      name: topic.name,
      description: topic.description || "",
      project_id: topic.project_id,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      plans_count: 0,
      tasks_count: 0,
      metadata: topic.metadata || {}
    }
    mockTopicsState.push(newTopic)
    return newTopic
  },

  async updateTopic(projectId: string, topicId: string, topic: UpdateTopicRequest): Promise<Topic> {
    await new Promise(resolve => setTimeout(resolve, 400))
    const existingTopic = mockTopicsState.find(t => t.id === topicId && t.project_id === projectId)
    if (!existingTopic) {
      throw new Error('Topic not found')
    }
    
    const updatedTopic = {
      ...existingTopic,
      ...topic,
      updated_at: new Date().toISOString()
    }
    
    const index = mockTopicsState.findIndex(t => t.id === topicId && t.project_id === projectId)
    mockTopicsState[index] = updatedTopic
    return updatedTopic
  },

  async deleteTopic(projectId: string, topicId: string): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 300))
    const index = mockTopicsState.findIndex(t => t.id === topicId && t.project_id === projectId)
    if (index === -1) {
      throw new Error('Topic not found')
    }
    mockTopicsState.splice(index, 1)
  },

  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return {
      status: "healthy",
      timestamp: new Date().toISOString()
    }
  }
}