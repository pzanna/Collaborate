/**
 * TypeScript models for hierarchical research structure
 * Project → Research Topic → Plan → Tasks
 */

export interface Project {
  id: string
  name: string
  description: string
  created_at: string
  updated_at: string
  metadata?: Record<string, any>
}

export interface ResearchTopic {
  id: string
  name: string
  description?: string
  project_id: string
  status: 'active' | 'on_hold' | 'completed' | 'cancelled'
  priority?: 'low' | 'medium' | 'high'
  created_at: string
  updated_at: string
}

export interface ResearchPlan {
  id: string
  topic_id: string
  name: string
  description: string
  plan_type: 'comprehensive' | 'quick' | 'deep' | 'custom'
  status: 'draft' | 'active' | 'completed' | 'cancelled'
  plan_approved: boolean
  created_at: string
  updated_at: string
  estimated_cost: number
  actual_cost: number
  task_count: number
  completed_tasks: number
  progress: number
  plan_structure?: Record<string, any>
  metadata?: Record<string, any>
}

export interface Task {
  id: string
  plan_id: string
  name: string
  description: string
  task_type: 'research' | 'analysis' | 'synthesis' | 'validation'
  task_order: number
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  stage: 'planning' | 'literature_review' | 'reasoning' | 'execution' | 'synthesis' | 'complete' | 'failed'
  created_at: string
  updated_at: string
  estimated_cost: number
  actual_cost: number
  cost_approved: boolean
  single_agent_mode: boolean
  max_results: number
  progress: number
  query?: string
  search_results?: Array<Record<string, any>>
  reasoning_output?: string
  execution_results?: Array<Record<string, any>>
  synthesis?: string
  metadata?: Record<string, any>
}

// Request models for creating new entities
export interface ResearchTopicRequest {
  name: string
  description?: string
  status?: 'active' | 'on_hold' | 'completed' | 'cancelled'
  priority?: 'low' | 'medium' | 'high'
}

export interface ResearchPlanRequest {
  name: string
  description?: string
  status?: 'active' | 'on_hold' | 'completed' | 'cancelled'
  plan_type?: 'comprehensive' | 'quick' | 'deep' | 'custom'
  plan_structure?: Record<string, any>
  metadata?: Record<string, any>
}

export interface TaskRequest {
  name: string
  description?: string
  task_type?: 'research' | 'analysis' | 'synthesis' | 'validation'
  task_order?: number
  query?: string
  max_results?: number
  single_agent_mode?: boolean
  metadata?: Record<string, any>
}

// Hierarchical navigation models
export interface ProjectHierarchy {
  project_id: string
  topics: Array<ResearchTopicWithPlans>
}

export interface ResearchTopicWithPlans extends ResearchTopic {
  plans: Array<ResearchPlanWithTasks>
}

export interface ResearchPlanWithTasks extends ResearchPlan {
  tasks: Array<Task>
}

// Navigation breadcrumb models
export interface BreadcrumbItem {
  label: string
  path: string
  isActive?: boolean
}

// Status and progress tracking
export interface ProgressSummary {
  total_tasks: number
  completed_tasks: number
  running_tasks: number
  pending_tasks: number
  failed_tasks: number
  progress_percentage: number
  estimated_cost: number
  actual_cost: number
}

export interface HierarchicalStats {
  project: {
    topics_count: number
    plans_count: number
    tasks_count: number
  }
  topic: {
    plans_count: number
    tasks_count: number
    progress: ProgressSummary
  }
  plan: {
    tasks_count: number
    progress: ProgressSummary
  }
}

// Filter and search models
export interface HierarchicalFilters {
  status?: string[]
  task_type?: string[]
  plan_type?: string[]
  date_range?: {
    start: string
    end: string
  }
  cost_range?: {
    min: number
    max: number
  }
}

// API response models (extending base models with additional computed fields)
export interface ResearchTopicResponse extends ResearchTopic {
  project_name?: string
  recent_activity?: string
  stats?: HierarchicalStats['topic']
  research_plans?: ResearchPlan[]
  plans_count?: number
  tasks_count?: number
}

export interface ResearchPlanResponse extends ResearchPlan {
  topic_name?: string
  project_name?: string
  recent_activity?: string
  stats?: HierarchicalStats['plan']
}

export interface TaskResponse extends Task {
  plan_name?: string
  topic_name?: string
  project_name?: string
  duration?: number // execution time in seconds
  agent_used?: string[]
}

// Utility types for component props
export type HierarchyLevel = 'project' | 'topic' | 'plan' | 'task'

export interface HierarchicalComponentProps {
  level: HierarchyLevel
  entityId: string
  parentId?: string
  showActions?: boolean
  compact?: boolean
}

// Navigation and routing helpers
export interface HierarchicalRoute {
  project_id?: string
  topic_id?: string
  plan_id?: string
  task_id?: string
}

export const parseHierarchicalRoute = (pathname: string): HierarchicalRoute => {
  const segments = pathname.split('/').filter(Boolean)
  const route: HierarchicalRoute = {}

  for (let i = 0; i < segments.length; i += 2) {
    const type = segments[i]
    const id = segments[i + 1]

    if (type === 'projects' && id) route.project_id = id
    if (type === 'topics' && id) route.topic_id = id
    if (type === 'plans' && id) route.plan_id = id
    if (type === 'tasks' && id) route.task_id = id
  }

  return route
}

export const buildHierarchicalPath = (route: HierarchicalRoute): string => {
  const segments: string[] = []

  if (route.project_id) {
    segments.push('projects', route.project_id)
  }
  if (route.topic_id) {
    segments.push('topics', route.topic_id)
  }
  if (route.plan_id) {
    segments.push('plans', route.plan_id)
  }
  if (route.task_id) {
    segments.push('tasks', route.task_id)
  }

  return '/' + segments.join('/')
}

// Constants for the hierarchical structure
export const HIERARCHY_LABELS = {
  project: 'Project',
  topic: 'Research Topic',
  plan: 'Research Plan',
  task: 'Task'
} as const

export const STATUS_COLORS = {
  active: 'green',
  draft: 'blue',
  pending: 'yellow',
  running: 'blue',
  completed: 'green',
  failed: 'red',
  cancelled: 'gray',
  paused: 'orange',
  archived: 'gray'
} as const

export const TASK_TYPE_ICONS = {
  research: '🔍',
  analysis: '📊',
  synthesis: '🔄',
  validation: '✅'
} as const

export const PLAN_TYPE_DESCRIPTIONS = {
  comprehensive: 'Full multi-stage research approach',
  quick: 'Fast single-agent research',
  deep: 'Detailed expert-level analysis',
  custom: 'Custom research methodology'
} as const
