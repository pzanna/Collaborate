import React, { useEffect, useState, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { apiService, Task } from "../../services/api"
import { formatDistanceToNow } from "date-fns"
import {
  ArrowLeftIcon,
  PlayIcon,
  ClockIcon,
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  DocumentTextIcon,
  CurrencyDollarIcon,
} from "@heroicons/react/24/outline"

const ResearchTaskDetailView: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>()
  const navigate = useNavigate()
  const [task, setTask] = useState<Task | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadTaskData = useCallback(async () => {
    if (!taskId) return

    setIsLoading(true)
    try {
      const taskData = await apiService.getResearchTask(taskId)
      setTask(taskData)
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load task data"
      setError(errorMessage)
    } finally {
      setIsLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    loadTaskData()
  }, [loadTaskData])

  const getStatusIcon = (status: string, stage: string) => {
    switch (status) {
      case "completed":
      case "complete":
        return <CheckCircleIcon className="h-6 w-6 text-green-500" />
      case "failed":
        return <XCircleIcon className="h-6 w-6 text-red-500" />
      case "running":
        return <PlayIcon className="h-6 w-6 text-blue-500" />
      case "pending":
        return <ClockIcon className="h-6 w-6 text-yellow-500" />
      default:
        return <ExclamationTriangleIcon className="h-6 w-6 text-gray-500" />
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
          <span className="text-gray-600">Loading task...</span>
        </div>
      </div>
    )
  }

  if (error || !task) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Error</h2>
          <p className="text-gray-600 mb-4">{error || "Task not found"}</p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
          >
            Go Back
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center text-gray-600 hover:text-gray-900 mb-4"
          >
            <ArrowLeftIcon className="h-5 w-5 mr-2" />
            Back
          </button>

          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center space-x-3">
                {getStatusIcon(task.status, task.stage)}
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">
                    {task.name}
                  </h1>
                  <span
                    className={`inline-block px-2 py-1 text-sm font-medium rounded-full ${getStatusColor(
                      task.status
                    )} mt-1`}
                  >
                    {task.status}
                  </span>
                </div>
              </div>

              {task.progress > 0 && task.progress < 100 && (
                <div className="text-right">
                  <div className="text-sm text-gray-600 mb-1">
                    {Math.round(task.progress)}% complete
                  </div>
                  <div className="w-32 bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(task.progress, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-gray-600">
              <div>
                <span className="font-medium">Stage:</span> {task.stage}
              </div>
              <div>
                <span className="font-medium">Created:</span>{" "}
                {formatDistanceToNow(new Date(task.created_at), {
                  addSuffix: true,
                })}
              </div>
              <div>
                <span className="font-medium">Updated:</span>{" "}
                {formatDistanceToNow(new Date(task.updated_at), {
                  addSuffix: true,
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Query */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center">
              <DocumentTextIcon className="h-5 w-5 mr-2" />
              Research Query
            </h2>
          </div>
          <div className="p-6">
            <p className="text-gray-800">{task.query}</p>
          </div>
        </div>

        {/* Cost Information */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900 flex items-center">
              <CurrencyDollarIcon className="h-5 w-5 mr-2" />
              Cost Information
            </h2>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <div className="text-sm text-gray-600">Estimated Cost</div>
                <div className="text-lg font-medium">
                  ${task.estimated_cost.toFixed(4)}
                </div>
              </div>
              <div>
                <div className="text-sm text-gray-600">Actual Cost</div>
                <div className="text-lg font-medium">
                  ${task.actual_cost.toFixed(4)}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Results */}
        {task.search_results && (
          <div className="space-y-6">
            {/* Search Results */}
            {task.search_results && task.search_results.length > 0 && (
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Search Results
                  </h2>
                </div>
                <div className="p-6">
                  <div className="space-y-4">
                    {task.search_results.map((result: any, index: number) => (
                      <div key={index} className="border rounded-lg p-4">
                        <h3 className="font-medium text-blue-600 hover:text-blue-800">
                          <a
                            href={result.url}
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {result.title}
                          </a>
                        </h3>
                        <p className="text-gray-600 text-sm mt-1">
                          {result.snippet}
                        </p>
                        <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
                          <span>{result.url}</span>
                          <span>
                            Relevance:{" "}
                            {Math.round(result.relevance_score * 100)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Reasoning Output */}
            {task.reasoning_output && (
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Analysis
                  </h2>
                </div>
                <div className="p-6">
                  <div className="prose max-w-none">
                    <pre className="whitespace-pre-wrap font-sans text-gray-800">
                      {task.reasoning_output}
                    </pre>
                  </div>
                </div>
              </div>
            )}

            {/* Synthesis */}
            {task.synthesis && (
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Summary
                  </h2>
                </div>
                <div className="p-6">
                  <div className="prose max-w-none">
                    <pre className="whitespace-pre-wrap font-sans text-gray-800">
                      {task.synthesis}
                    </pre>
                  </div>
                </div>
              </div>
            )}

            {/* Execution Results */}
            {task.execution_results && task.execution_results.length > 0 && (
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200">
                  <h2 className="text-lg font-semibold text-gray-900">
                    Execution Results
                  </h2>
                </div>
                <div className="p-6">
                  <pre className="bg-gray-50 p-4 rounded-lg overflow-x-auto text-sm">
                    {JSON.stringify(task.execution_results, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default ResearchTaskDetailView
