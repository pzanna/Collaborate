/**
 * Research Topic Detail Component
 * Shows detailed view of a research topic with its plans and navigation
 */

import React, { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  ArrowLeftIcon,
  PlusIcon,
  DocumentTextIcon,
  ChartBarIcon,
  CalendarIcon,
  ClockIcon,
  PencilIcon,
  TrashIcon,
  FolderOpenIcon,
} from "@heroicons/react/24/outline"
import { hierarchicalAPI } from "../../services/hierarchicalAPI"
import {
  ResearchTopicResponse,
  ResearchPlanResponse,
} from "../../types/hierarchical"

const ResearchTopicDetail: React.FC = () => {
  const { projectId, topicId } = useParams<{
    projectId: string
    topicId: string
  }>()
  const navigate = useNavigate()

  const [topic, setTopic] = useState<ResearchTopicResponse | null>(null)
  const [plans, setPlans] = useState<ResearchPlanResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreatePlanForm, setShowCreatePlanForm] = useState(false)
  const [showEditForm, setShowEditForm] = useState(false)

  const loadTopicDetails = useCallback(async () => {
    if (!topicId) return

    try {
      const topicData = await hierarchicalAPI.getResearchTopic(topicId)
      setTopic(topicData)
      setError(null)
    } catch (err) {
      console.error("Failed to load topic details:", err)
      setError(
        err instanceof Error ? err.message : "Failed to load topic details"
      )
    }
  }, [topicId])

  const loadPlans = useCallback(async () => {
    if (!topicId) return

    try {
      setLoading(true)
      const plansData = await hierarchicalAPI.getResearchPlans(topicId)
      setPlans(plansData)
      setError(null)
    } catch (err) {
      console.error("Failed to load research plans:", err)
      setError(
        err instanceof Error ? err.message : "Failed to load research plans"
      )
    } finally {
      setLoading(false)
    }
  }, [topicId])

  useEffect(() => {
    if (topicId) {
      loadTopicDetails()
      loadPlans()
    }
  }, [topicId, loadTopicDetails, loadPlans])

  const handleBackClick = () => {
    navigate(`/projects/${projectId}/topics`)
  }

  const handlePlanClick = (planId: string) => {
    navigate(`/projects/${projectId}/topics/${topicId}/plans/${planId}`)
  }

  const handleCreatePlan = () => {
    setShowCreatePlanForm(true)
  }

  const handleEditTopic = () => {
    setShowEditForm(true)
  }

  const handleDeleteTopic = async () => {
    if (
      !topicId ||
      !window.confirm(
        "Are you sure you want to delete this research topic? This action cannot be undone."
      )
    ) {
      return
    }

    try {
      await hierarchicalAPI.deleteResearchTopic(topicId)
      navigate(`/projects/${projectId}/topics`)
    } catch (err) {
      console.error("Failed to delete topic:", err)
      alert("Failed to delete topic. Please try again.")
    }
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
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    })
  }

  if (loading && !topic) {
    return (
      <div className="flex justify-center items-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  if (error && !topic) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
        <p className="font-medium">Error loading research topic</p>
        <p className="text-sm mt-1">{error}</p>
        <div className="mt-3 space-x-2">
          <button
            onClick={loadTopicDetails}
            className="text-sm text-red-600 hover:text-red-800 underline"
          >
            Try again
          </button>
          <button
            onClick={handleBackClick}
            className="text-sm text-red-600 hover:text-red-800 underline"
          >
            Back to topics
          </button>
        </div>
      </div>
    )
  }

  if (!topic) {
    return <div className="text-center py-8 text-gray-500">Topic not found</div>
  }

  return (
    <div className="space-y-6">
      {/* Navigation */}
      <div className="flex items-center space-x-2 text-sm text-gray-600">
        <button
          onClick={handleBackClick}
          className="inline-flex items-center hover:text-gray-900 transition-colors"
        >
          <ArrowLeftIcon className="h-4 w-4 mr-1" />
          Back to Topics
        </button>
      </div>

      {/* Header */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-3 mb-2">
                <FolderOpenIcon className="h-6 w-6 text-blue-500" />
                <h1 className="text-2xl font-bold text-gray-900">
                  {topic.name}
                </h1>
                <span
                  className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${getStatusColor(
                    topic.status
                  )}`}
                >
                  {topic.status.replace("_", " ").toUpperCase()}
                </span>
              </div>

              {topic.description && (
                <p className="text-gray-600 mb-4">{topic.description}</p>
              )}

              <div className="flex flex-wrap gap-4 text-sm text-gray-500">
                {topic.priority && (
                  <div className="flex items-center">
                    <ChartBarIcon className="h-4 w-4 mr-1" />
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
                  <CalendarIcon className="h-4 w-4 mr-1" />
                  <span>Created {formatDate(topic.created_at)}</span>
                </div>

                {topic.updated_at && topic.updated_at !== topic.created_at && (
                  <div className="flex items-center">
                    <ClockIcon className="h-4 w-4 mr-1" />
                    <span>Updated {formatDate(topic.updated_at)}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-2 ml-4">
              <button
                onClick={handleEditTopic}
                className="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <PencilIcon className="h-4 w-4 mr-1" />
                Edit
              </button>
              <button
                onClick={handleDeleteTopic}
                className="inline-flex items-center px-3 py-2 border border-red-300 shadow-sm text-sm leading-4 font-medium rounded-md text-red-700 bg-white hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
              >
                <TrashIcon className="h-4 w-4 mr-1" />
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Research Plans Section */}
      <div className="bg-white rounded-lg shadow-sm border border-gray-200">
        <div className="px-6 py-4 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-medium text-gray-900">
                Research Plans
              </h2>
              <p className="text-sm text-gray-600 mt-1">
                Organize your research into structured plans and tasks
              </p>
            </div>
            <button
              onClick={handleCreatePlan}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <PlusIcon className="h-4 w-4 mr-2" />
              New Plan
            </button>
          </div>
        </div>

        <div className="p-6">
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
            </div>
          ) : plans.length === 0 ? (
            <div className="text-center py-8">
              <DocumentTextIcon className="mx-auto h-12 w-12 text-gray-400" />
              <h3 className="mt-2 text-sm font-medium text-gray-900">
                No research plans
              </h3>
              <p className="mt-1 text-sm text-gray-500">
                Create your first research plan to get started.
              </p>
              <div className="mt-4">
                <button
                  onClick={handleCreatePlan}
                  className="inline-flex items-center px-4 py-2 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                >
                  <PlusIcon className="h-4 w-4 mr-2" />
                  Create Research Plan
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {plans.map((plan) => (
                <div
                  key={plan.id}
                  onClick={() => handlePlanClick(plan.id)}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer group"
                >
                  <div className="flex items-start justify-between mb-3">
                    <div className="flex items-center">
                      <DocumentTextIcon className="h-5 w-5 text-green-500 mr-2 flex-shrink-0" />
                      <h3 className="font-medium text-gray-900 group-hover:text-blue-600 transition-colors line-clamp-2">
                        {plan.name}
                      </h3>
                    </div>
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-medium border ${getStatusColor(
                        plan.status
                      )}`}
                    >
                      {plan.status.replace("_", " ").toUpperCase()}
                    </span>
                  </div>

                  {plan.description && (
                    <p className="text-gray-600 text-sm mb-3 line-clamp-2">
                      {plan.description}
                    </p>
                  )}

                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <span>
                      Created {new Date(plan.created_at).toLocaleDateString()}
                    </span>
                    <span className="font-medium text-gray-900">
                      {plan.task_count || 0} tasks
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Create Plan Modal */}
      {showCreatePlanForm && topicId && (
        <CreatePlanModal
          topicId={topicId}
          onClose={() => setShowCreatePlanForm(false)}
          onSuccess={() => {
            setShowCreatePlanForm(false)
            loadPlans()
          }}
        />
      )}

      {/* Edit Topic Modal */}
      {showEditForm && (
        <EditTopicModal
          topic={topic}
          onClose={() => setShowEditForm(false)}
          onSuccess={(updatedTopic) => {
            setShowEditForm(false)
            setTopic(updatedTopic)
          }}
        />
      )}
    </div>
  )
}

interface CreatePlanModalProps {
  topicId: string
  onClose: () => void
  onSuccess: () => void
}

const CreatePlanModal: React.FC<CreatePlanModalProps> = ({
  topicId,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    status: "active" as "active" | "on_hold" | "completed" | "cancelled",
  })
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      setError("Plan name is required")
      return
    }

    try {
      setCreating(true)
      setError(null)

      await hierarchicalAPI.createResearchPlan(topicId, {
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        status: formData.status,
      })

      onSuccess()
    } catch (err) {
      console.error("Failed to create research plan:", err)
      setError(
        err instanceof Error ? err.message : "Failed to create research plan"
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
            Create New Research Plan
          </h3>

          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-red-700 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Plan Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
                className="w-full border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder="e.g., Literature Review"
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
                placeholder="Describe the research plan..."
                disabled={creating}
              />
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
                {creating ? "Creating..." : "Create Plan"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

interface EditTopicModalProps {
  topic: ResearchTopicResponse
  onClose: () => void
  onSuccess: (updatedTopic: ResearchTopicResponse) => void
}

const EditTopicModal: React.FC<EditTopicModalProps> = ({
  topic,
  onClose,
  onSuccess,
}) => {
  const [formData, setFormData] = useState({
    name: topic.name,
    description: topic.description || "",
    priority: topic.priority || ("medium" as "low" | "medium" | "high"),
    status: topic.status,
  })
  const [updating, setUpdating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!formData.name.trim()) {
      setError("Topic name is required")
      return
    }

    try {
      setUpdating(true)
      setError(null)

      const updatedTopic = await hierarchicalAPI.updateResearchTopic(topic.id, {
        name: formData.name.trim(),
        description: formData.description.trim() || undefined,
        priority: formData.priority,
        status: formData.status,
      })

      onSuccess(updatedTopic)
    } catch (err) {
      console.error("Failed to update research topic:", err)
      setError(
        err instanceof Error ? err.message : "Failed to update research topic"
      )
    } finally {
      setUpdating(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <h3 className="text-lg font-medium text-gray-900 mb-4">
            Edit Research Topic
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
                disabled={updating}
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
                disabled={updating}
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
                  disabled={updating}
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
                  disabled={updating}
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
                disabled={updating}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
                disabled={updating}
              >
                {updating ? "Updating..." : "Update Topic"}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

export default ResearchTopicDetail
