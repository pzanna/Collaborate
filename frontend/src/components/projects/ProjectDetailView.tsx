import React, { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { apiService, Task } from "../../services/api"
import { hierarchicalAPI } from "../../services/hierarchicalAPI"
import { ResearchTopicResponse } from "../../types/hierarchical"
import { formatDistanceToNow } from "date-fns"
import {
  ArrowLeftIcon,
  PlayIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  FolderIcon,
  ChevronRightIcon,
} from "@heroicons/react/24/outline"

interface Project {
  id: string
  name: string
  description: string
  status: "active" | "archived"
  created_at: string
  updated_at: string
  topics_count: number
  plans_count: number
  tasks_count: number
  total_cost: number
  completion_rate: number
  metadata: Record<string, any>
}

const ProjectDetailView: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [researchTasks, setResearchTasks] = useState<Task[]>([])
  const [researchTopics, setResearchTopics] = useState<ResearchTopicResponse[]>(
    []
  )
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadProjectData = useCallback(async () => {
    if (!projectId) return

    setIsLoading(true)
    try {
      // Load project details, research tasks, and research topics in parallel
      const [projectsData, tasksData, topicsData] = await Promise.all([
        apiService.getProjects(),
        apiService.getProjectResearchTasks(projectId),
        hierarchicalAPI.getResearchTopics(projectId),
      ])

      const projectData = projectsData.find((p) => p.id === projectId)
      if (!projectData) {
        throw new Error("Project not found")
      }

      setProject(projectData)
      setResearchTasks(tasksData)
      setResearchTopics(topicsData)
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load project data"
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [projectId])

  useEffect(() => {
    loadProjectData()
  }, [loadProjectData])

  const handleTaskClick = (taskId: string) => {
    navigate(`/research/task/${taskId}`)
  }

  const handleTopicClick = (topicId: string) => {
    navigate(`/projects/${projectId}/topics/${topicId}`)
  }

  const getStatusIcon = (status: string, stage: string) => {
    switch (status) {
      case "completed":
      case "complete":
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case "failed":
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case "running":
        return <PlayIcon className="h-5 w-5 text-blue-500" />
      case "pending":
        return <ClockIcon className="h-5 w-5 text-yellow-500" />
      default:
        return <ExclamationTriangleIcon className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
      case "complete":
        return "bg-green-100 text-green-800"
      case "failed":
        return "bg-red-100 text-red-800"
      case "running":
        return "bg-blue-100 text-blue-800"
      case "pending":
        return "bg-yellow-100 text-yellow-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center space-x-2">
          <div className="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-gray-600">Loading project...</span>
        </div>
      </div>
    )
  }

  if (error || !project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Error</h2>
          <p className="text-gray-600 mb-4">{error || "Project not found"}</p>
          <button
            onClick={() => navigate("/projects")}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            Back to Projects
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate("/projects")}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Back to Projects
          </button>

          <div className="bg-white rounded-lg shadow p-6">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {project.name}
            </h1>
            <p className="text-gray-600 mb-4">{project.description}</p>

            <div className="flex items-center space-x-6 text-sm text-gray-500">
              <span>
                Created{" "}
                {formatDistanceToNow(new Date(project.created_at), {
                  addSuffix: true,
                })}
              </span>
              <span>{researchTopics.length} research topics</span>
              <span>{researchTasks.length} research tasks</span>
            </div>
          </div>
        </div>

        {/* Research Topics */}
        <div className="mb-8">
          <div className="bg-white rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200">
              <div className="flex justify-between items-center">
                <h2 className="text-xl font-semibold text-gray-900">
                  Research Topics
                </h2>
                <button
                  onClick={() => navigate(`/projects/${projectId}/topics`)}
                  className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                >
                  View All →
                </button>
              </div>
            </div>

            {researchTopics.length === 0 ? (
              <div className="p-6 text-center">
                <FolderIcon className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No research topics yet
                </h3>
                <p className="text-gray-600 mb-4">
                  Research topics are created via the research workspace.
                </p>
              </div>
            ) : (
              <div className="divide-y divide-gray-200">
                {researchTopics.slice(0, 5).map((topic) => (
                  <div
                    key={topic.id}
                    onClick={() => handleTopicClick(topic.id)}
                    className="p-6 hover:bg-gray-50 cursor-pointer transition-colors group"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center flex-1">
                        <FolderIcon className="h-5 w-5 text-blue-500 mr-3 flex-shrink-0" />
                        <div className="flex-1">
                          <h3 className="text-lg font-medium text-gray-900 group-hover:text-blue-600 transition-colors">
                            {topic.name}
                          </h3>
                          {topic.description && (
                            <p className="text-gray-600 text-sm mt-1 line-clamp-2">
                              {topic.description}
                            </p>
                          )}
                          <div className="flex items-center space-x-4 mt-2 text-sm text-gray-500">
                            <span
                              className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${
                                topic.status === "active"
                                  ? "bg-green-100 text-green-800 border-green-200"
                                  : topic.status === "completed"
                                  ? "bg-blue-100 text-blue-800 border-blue-200"
                                  : topic.status === "on_hold"
                                  ? "bg-yellow-100 text-yellow-800 border-yellow-200"
                                  : "bg-gray-100 text-gray-800 border-gray-200"
                              }`}
                            >
                              {topic.status.replace("_", " ").toUpperCase()}
                            </span>
                            <span>{topic.plans_count || 0} plans</span>
                            <span>{topic.tasks_count || 0} tasks</span>
                          </div>
                        </div>
                      </div>
                      <ChevronRightIcon className="h-5 w-5 text-gray-400 group-hover:text-gray-600 transition-colors" />
                    </div>
                  </div>
                ))}

                {researchTopics.length > 5 && (
                  <div className="p-4 bg-gray-50 text-center">
                    <button
                      onClick={() => navigate(`/projects/${projectId}/topics`)}
                      className="text-sm text-blue-600 hover:text-blue-800 font-medium"
                    >
                      View {researchTopics.length - 5} more topics →
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Research Tasks */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">
              Research Tasks
            </h2>
          </div>

          {researchTasks.length === 0 ? (
            <div className="p-8 text-center">
              <div className="text-gray-400 mb-4">
                <PlayIcon className="h-12 w-12 mx-auto" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                No research tasks yet
              </h3>
              <p className="text-gray-600">
                Research tasks will appear here when created for this project.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {researchTasks.map((task) => (
                <div
                  key={task.id}
                  className="p-6 hover:bg-gray-50 cursor-pointer transition-colors"
                  onClick={() => handleTaskClick(task.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        {getStatusIcon(task.status, task.stage)}
                        <h3 className="text-lg font-medium text-gray-900">
                          {task.name}
                        </h3>
                        <span
                          className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                            task.status
                          )}`}
                        >
                          {task.status}
                        </span>
                      </div>

                      <p className="text-gray-600 mb-3 line-clamp-2">
                        {task.query}
                      </p>

                      <div className="flex items-center space-x-6 text-sm text-gray-500">
                        <span>Stage: {task.stage}</span>
                        <span>Progress: {Math.round(task.progress)}%</span>
                        <span>
                          Created{" "}
                          {formatDistanceToNow(new Date(task.created_at), {
                            addSuffix: true,
                          })}
                        </span>
                        {task.actual_cost > 0 && (
                          <span>Cost: ${task.actual_cost.toFixed(4)}</span>
                        )}
                      </div>
                    </div>

                    {task.progress > 0 && task.progress < 100 && (
                      <div className="ml-4">
                        <div className="w-32 bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                            style={{
                              width: `${Math.min(task.progress, 100)}%`,
                            }}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ProjectDetailView
