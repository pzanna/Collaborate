/**
 * Research Topic List Component
 * Displays all research topics within a project with hierarchical navigation
 */

import React, { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  PlusIcon,
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
  const [showCreateForm, setShowCreateForm] = useState(false)

  useEffect(() => {
    if (projectId) {
      loadTopics()
    }
  }, [projectId, filterStatus])

  const loadTopics = async () => {
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
  }

  const handleCreateTopic = () => {
    setShowCreateForm(true)
  }

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
      <div className="text-center py-8 text-gray-500">No project selected</div>
    )
  }

  if (loading) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (error) {
    return (
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
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Research Topics</h2>
          <p className="text-gray-600 mt-1">
            Organize your research into focused topics and plans
          </p>
        </div>
        <button
          onClick={handleCreateTopic}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <PlusIcon className="h-4 w-4 mr-2" />
          New Topic
        </button>
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
            Get started by creating your first research topic.
          </p>
          <div className="mt-6">
            <button
              onClick={handleCreateTopic}
              className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <PlusIcon className="h-4 w-4 mr-2" />
              New Research Topic
            </button>
          </div>
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

      {/* Create Topic Modal */}
      {showCreateForm && (
        <CreateTopicModal
          projectId={projectId}
          onClose={() => setShowCreateForm(false)}
          onSuccess={() => {
            setShowCreateForm(false)
            loadTopics()
          }}
        />
      )}
    </div>
  )
}

interface CreateTopicModalProps {
  projectId: string
  onClose: () => void
  onSuccess: () => void
}

const CreateTopicModal: React.FC<CreateTopicModalProps> = ({
  projectId,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    priority: "medium" as "low" | "medium" | "high",
    status: "active" as "active" | "on_hold" | "completed" | "cancelled",
  })
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      setError("Topic name is required")
      return
    }

    try {
      setCreating(true)
      setError(null)

      await hierarchicalAPI.createResearchTopic(projectId, {
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        priority: formData.priority,
        status: formData.status,
      })

      onSuccess()
    } catch (err) {
      console.error("Failed to create research topic:", err)
      setError(
        err instanceof Error ? err.message : "Failed to create research topic"
      )
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Create New Research Topic
          </h3>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Topic Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., AI Safety Fundamentals"
                disabled={creating}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
                rows={3}
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="Describe the research topic..."
                disabled={creating}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Priority
                </label>
                <select
                  value={formData.priority}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      priority: e.target.value as any,
                    })
                  }
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  disabled={creating}
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Status
                </label>
                <select
                  value={formData.status}
                  onChange={(e) =>
                    setFormData({ ...formData, status: e.target.value as any })
                  }
                  className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  disabled={creating}
                >
                  <option value="active">Active</option>
                  <option value="on_hold">On Hold</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </div>

            <div className="flex justify-end space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                disabled={creating}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                disabled={creating}
              >
                {creating ? "Creating..." : "Create Topic"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default ResearchTopicList
