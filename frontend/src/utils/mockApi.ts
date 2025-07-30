import type { 
  Project, CreateProjectRequest, UpdateProjectRequest, 
  Topic, CreateTopicRequest, UpdateTopicRequest,
  ResearchPlan, CreateResearchPlanRequest, UpdateResearchPlanRequest 
} from './api'

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

// Mock research plan data
const mockResearchPlans: ResearchPlan[] = [
  {
    id: "rp1",
    topic_id: "t1",
    name: "Data Collection Methodology",
    description: "Comprehensive plan for collecting neurological data from study participants",
    plan_type: "comprehensive",
    status: "active",
    plan_approved: true,
    created_at: "2024-01-16T10:00:00Z",
    updated_at: "2024-01-18T14:30:00Z",
    estimated_cost: 5000.0,
    actual_cost: 4500.0,
    tasks_count: 8,
    completed_tasks: 6,
    progress: 75.0,
    plan_structure: {
      sections: [
        "1. Subject recruitment and screening protocols",
        "2. Data collection procedures",
        "3. Quality assurance measures",
        "4. Data storage and security protocols"
      ],
      details: "This research plan establishes the framework for systematic data collection in our neuroscience study. The approach includes standardized protocols for participant recruitment, rigorous screening procedures, and comprehensive data quality measures."
    },
    metadata: {}
  },
  {
    id: "rp2",
    topic_id: "t1",
    name: "Statistical Analysis Framework",
    description: "Plan for analyzing collected neurological data using advanced statistical methods",
    plan_type: "comprehensive",
    status: "draft",
    plan_approved: false,
    created_at: "2024-01-17T09:30:00Z",
    updated_at: "2024-01-19T11:45:00Z",
    estimated_cost: 3500.0,
    actual_cost: 0.0,
    tasks_count: 5,
    completed_tasks: 0,
    progress: 0.0,
    plan_structure: {
      sections: [
        "1. Descriptive statistical analysis",
        "2. Inferential statistical methods",
        "3. Machine learning approaches",
        "4. Results interpretation guidelines"
      ],
      details: "This plan outlines the statistical approaches for analyzing the neurological data. It includes both traditional statistical methods and modern machine learning techniques to extract meaningful insights from the collected data."
    },
    metadata: {}
  },
  {
    id: "rp3",
    topic_id: "t2",
    name: "Meta-Analysis Protocol",
    description: "Systematic approach for conducting meta-analysis of neurological studies",
    plan_type: "comprehensive",
    status: "active",
    plan_approved: true,
    created_at: "2024-01-17T15:20:00Z",
    updated_at: "2024-01-20T08:15:00Z",
    estimated_cost: 8000.0,
    actual_cost: 2000.0,
    tasks_count: 12,
    completed_tasks: 3,
    progress: 25.0,
    plan_structure: {
      sections: [
        "1. Literature search strategy",
        "2. Study selection criteria",
        "3. Data extraction procedures",
        "4. Statistical meta-analysis methods",
        "5. Bias assessment protocols"
      ],
      details: "This comprehensive meta-analysis plan provides a systematic framework for synthesizing evidence from multiple neurological studies. The protocol ensures rigorous methodology and reduces potential biases in the analysis."
    },
    metadata: {}
  },
  {
    id: "rp4",
    topic_id: "t3",
    name: "Clinical Trial Literature Review",
    description: "Comprehensive review of Phase III clinical trials",
    plan_type: "comprehensive",
    status: "completed",
    plan_approved: true,
    created_at: "2024-01-11T11:00:00Z",
    updated_at: "2024-01-16T16:30:00Z",
    estimated_cost: 6000.0,
    actual_cost: 5800.0,
    tasks_count: 10,
    completed_tasks: 10,
    progress: 100.0,
    plan_structure: {
      sections: [
        "1. Database search strategy",
        "2. Inclusion/exclusion criteria",
        "3. Data extraction methods",
        "4. Quality assessment framework"
      ],
      details: "Completed systematic review of Phase III clinical trials focusing on therapeutic interventions. The review followed PRISMA guidelines and included comprehensive quality assessment of included studies."
    },
    metadata: {}
  }
]

const mockProjectsState = [...mockProjects]
let mockTopicsState = [...mockTopics]
let mockResearchPlansState = [...mockResearchPlans]

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

  async getTopicById(topicId: string): Promise<Topic> {
    await new Promise(resolve => setTimeout(resolve, 200))
    const topic = mockTopicsState.find(t => t.id === topicId)
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

  // Research Plan methods
  async getResearchPlans(topicId: string): Promise<ResearchPlan[]> {
    await new Promise(resolve => setTimeout(resolve, 300))
    return mockResearchPlansState.filter(plan => plan.topic_id === topicId)
  },

  async getResearchPlan(planId: string): Promise<ResearchPlan> {
    await new Promise(resolve => setTimeout(resolve, 200))
    const plan = mockResearchPlansState.find(p => p.id === planId)
    if (!plan) {
      throw new Error('Research plan not found')
    }
    return plan
  },

  async createResearchPlan(topicId: string, plan: CreateResearchPlanRequest): Promise<ResearchPlan> {
    await new Promise(resolve => setTimeout(resolve, 400))
    const newPlan: ResearchPlan = {
      id: `rp${Date.now()}`,
      topic_id: topicId,
      name: plan.name,
      description: plan.description || "",
      plan_type: plan.plan_type || "comprehensive",
      status: "draft",
      plan_approved: false,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      estimated_cost: 0.0,
      actual_cost: 0.0,
      tasks_count: 0,
      completed_tasks: 0,
      progress: 0.0,
      plan_structure: plan.plan_structure || {},
      metadata: plan.metadata || {}
    }
    mockResearchPlansState.push(newPlan)
    return newPlan
  },

  async updateResearchPlan(planId: string, plan: UpdateResearchPlanRequest): Promise<ResearchPlan> {
    await new Promise(resolve => setTimeout(resolve, 400))
    const existingPlan = mockResearchPlansState.find(p => p.id === planId)
    if (!existingPlan) {
      throw new Error('Research plan not found')
    }
    
    const updatedPlan = {
      ...existingPlan,
      ...plan,
      updated_at: new Date().toISOString()
    }
    
    const index = mockResearchPlansState.findIndex(p => p.id === planId)
    mockResearchPlansState[index] = updatedPlan
    return updatedPlan
  },

  async deleteResearchPlan(planId: string): Promise<void> {
    await new Promise(resolve => setTimeout(resolve, 300))
    const index = mockResearchPlansState.findIndex(p => p.id === planId)
    if (index === -1) {
      throw new Error('Research plan not found')
    }
    mockResearchPlansState.splice(index, 1)
  },

  async approveResearchPlan(planId: string): Promise<ResearchPlan> {
    await new Promise(resolve => setTimeout(resolve, 300))
    const existingPlan = mockResearchPlansState.find(p => p.id === planId)
    if (!existingPlan) {
      throw new Error('Research plan not found')
    }

    const updatedPlan = {
      ...existingPlan,
      plan_approved: true,
      status: "active",
      updated_at: new Date().toISOString()
    }
    
    const index = mockResearchPlansState.findIndex(p => p.id === planId)
    mockResearchPlansState[index] = updatedPlan
    return updatedPlan
  },

  async healthCheck(): Promise<{ status: string; timestamp: string }> {
    return {
      status: "healthy",
      timestamp: new Date().toISOString()
    }
  }
}