/**
 * Research Topic List Component
 * Displays all research topics within a project with hierarchical navigation
 */

import React, { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  FolderIcon,
  DocumentTextIcon,
  ChartBarIcon,
  CalendarIcon,
  ClockIcon,
} from "@heroicons/react/24/outline"
import { hierarchicalAPI } from "../../services/hierarchicalAPI"
import { ResearchTopicResponse } from "../../types/hierarchical"

interface ResearchTopicListProps {
  projectId?: string
}

const ResearchTopicList: React.FC<ResearchTopicListProps> = ({
  projectId: propProjectId,
}) => {
  const { projectId: paramProjectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()

  const projectId = propProjectId || paramProjectId

  const [topics, setTopics] = useState<ResearchTopicResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filterStatus, setFilterStatus] = useState<string>("")

  const loadTopics = useCallback(async () => {
    if (!projectId) return

    try {
      setLoading(true)
      const topicsData = await hierarchicalAPI.getResearchTopics(
        projectId,
        filterStatus || undefined
      )
      setTopics(topicsData)
      setError(null)
    } catch (err) {
      console.error("Failed to load research topics:", err)
      setError(
        err instanceof Error ? err.message : "Failed to load research topics"
      )
    } finally {
      setLoading(false)
    }
  }, [projectId, filterStatus])

  useEffect(() => {
    if (projectId) {
      loadTopics()
    }
  }, [projectId, filterStatus, loadTopics])

  const handleTopicClick = (topicId: string) => {
    navigate(`/projects/${projectId}/topics/${topicId}`)
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "active":
        return "bg-green-100 text-green-800 border-green-200"
      case "completed":
        return "bg-blue-100 text-blue-800 border-blue-200"
      case "on_hold":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "cancelled":
        return "bg-red-100 text-red-800 border-red-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const getPriorityColor = (priority: string) => {
    switch (priority.toLowerCase()) {
      case "high":
        return "text-red-600"
      case "medium":
        return "text-yellow-600"
      case "low":
        return "text-green-600"
      default:
        return "text-gray-600"
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    })
  }

  if (!projectId) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="text-center py-8 text-gray-500">
          No project selected
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="flex justify-center items-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
          <p className="font-medium">Error loading research topics</p>
          <p className="text-sm mt-1">{error}</p>
          <button
            onClick={loadTopics}
            className="mt-2 text-sm text-red-600 hover:text-red-800 underline"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Research Topics</h2>
          <p className="text-gray-600 mt-1">
            Organize your research into focused topics and plans
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="flex space-x-4">
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="completed">Completed</option>
          <option value="on_hold">On Hold</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {/* Topics Grid */}
      {topics.length === 0 ? (
        <div className="text-center py-12">
          <FolderIcon className="mx-auto h-12 w-12 text-gray-400" />
          <h3 className="mt-2 text-sm font-medium text-gray-900">
            No research topics
          </h3>
          <p className="mt-1 text-sm text-gray-500">
            Research topics are created via the research workspace.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {topics.map((topic) => (
            <div
              key={topic.id}
              onClick={() => handleTopicClick(topic.id)}
              className="bg-white rounded-lg border border-gray-200 shadow-sm hover:shadow-md transition-shadow cursor-pointer group"
            >
              <div className="p-6">
                {/* Header */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center">
                    <FolderIcon className="h-5 w-5 text-blue-500 mr-2 flex-shrink-0" />
                    <h3 className="text-lg font-medium text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-2">
                      {topic.name}
                    </h3>
                  </div>
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${getStatusColor(
                      topic.status
                    )}`}
                  >
                    {topic.status.replace("_", " ").toUpperCase()}
                  </span>
                </div>

                {/* Description */}
                {topic.description && (
                  <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                    {topic.description}
                  </p>
                )}

                {/* Metadata */}
                <div className="space-y-2 text-xs text-gray-500">
                  {topic.priority && (
                    <div className="flex items-center">
                      <ChartBarIcon className="h-3 w-3 mr-1" />
                      <span
                        className={`font-medium ${getPriorityColor(
                          topic.priority
                        )}`}
                      >
                        {topic.priority.charAt(0).toUpperCase() +
                          topic.priority.slice(1)}{" "}
                        Priority
                      </span>
                    </div>
                  )}

                  <div className="flex items-center">
                    <CalendarIcon className="h-3 w-3 mr-1" />
                    <span>Created {formatDate(topic.created_at)}</span>
                  </div>

                  {topic.updated_at &&
                    topic.updated_at !== topic.created_at && (
                      <div className="flex items-center">
                        <ClockIcon className="h-3 w-3 mr-1" />
                        <span>Updated {formatDate(topic.updated_at)}</span>
                      </div>
                    )}
                </div>

                {/* Plans Count */}
                <div className="mt-4 pt-4 border-t border-gray-100">
                  <div className="flex items-center justify-between text-sm">
                    <div className="flex items-center text-gray-600">
                      <DocumentTextIcon className="h-4 w-4 mr-1" />
                      <span>Research Plans</span>
                    </div>
                    <span className="font-medium text-gray-900">
                      {topic.research_plans?.length || 0}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ResearchTopicList
