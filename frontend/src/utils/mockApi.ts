import type { Project, CreateProjectRequest, UpdateProjectRequest } from './api'

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

let mockProjectsState = [...mockProjects]

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

  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return {
      status: "healthy",
      timestamp: new Date().toISOString()
    }
  }
}