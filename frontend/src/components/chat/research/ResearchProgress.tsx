import React, { useState } from "react"
import { useSelector, useDispatch } from "react-redux"
import { RootState, AppDispatch } from "../../../store/store"
import { cancelResearchTask } from "../../../store/slices/chatSlice"

interface ResearchProgressProps {
  className?: string
}

const ResearchProgress: React.FC<ResearchProgressProps> = ({
  className = "",
}) => {
  const dispatch = useDispatch<AppDispatch>()
  const { activeResearchTask, researchConnectionStatus } = useSelector(
    (state: RootState) => state.chat
  )
  const [isExpanded, setIsExpanded] = useState(false)

  if (!activeResearchTask) {
    return null
  }

  const handleCancel = () => {
    if (activeResearchTask.task_id) {
      dispatch(cancelResearchTask(activeResearchTask.task_id))
    }
  }

  const getStageDetails = (status: string) => {
    switch (status) {
      case "starting":
        return {
          label: "Initializing",
          description: "Starting research task...",
        }
      case "planning":
        return {
          label: "Planning",
          description: "Analyzing query and planning research approach...",
        }
      case "retrieval":
        return {
          label: "Retrieving",
          description: "Searching and collecting relevant information...",
        }
      case "reasoning":
        return {
          label: "Reasoning",
          description: "Analyzing and connecting information...",
        }
      case "execution":
        return {
          label: "Executing",
          description: "Processing and validating findings...",
        }
      case "synthesis":
        return {
          label: "Synthesizing",
          description: "Compiling final research results...",
        }
      case "completed":
        return {
          label: "Completed",
          description: "Research task completed successfully!",
        }
      case "failed":
        return {
          label: "Failed",
          description: "Research task failed. Please try again.",
        }
      case "cancelled":
        return {
          label: "Cancelled",
          description: "Research task was cancelled.",
        }
      default:
        return {
          label: "Processing",
          description: "Working on your research...",
        }
    }
  }

  const stageDetails = getStageDetails(activeResearchTask.status)
  const isActive = !["completed", "failed", "cancelled"].includes(
    activeResearchTask.status
  )

  return (
    <div
      className={`bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}
    >
      <div className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  isActive ? "bg-blue-500 animate-pulse" : "bg-gray-400"
                }`}
              ></div>
              <h3 className="text-sm font-medium text-gray-900">
                Research Task
              </h3>
            </div>

            <div className="flex items-center space-x-2">
              <span className="text-xs text-gray-500">
                {stageDetails.label}
              </span>
              <span className="text-xs text-gray-400">•</span>
              <span className="text-xs text-gray-500">
                {Math.round(activeResearchTask.progress)}%
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
            >
              {isExpanded ? "⬆️" : "⬇️"}
            </button>

            {isActive && (
              <button
                onClick={handleCancel}
                className="text-xs text-red-500 hover:text-red-700 transition-colors"
                title="Cancel research task"
              >
                ⏹️
              </button>
            )}
          </div>
        </div>

        {/* Progress bar */}
        <div className="mt-3">
          <div className="flex items-center justify-between text-xs text-gray-600 mb-1">
            <span>{stageDetails.description}</span>
            <span>{activeResearchTask.progress}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className={`h-2 rounded-full transition-all duration-300 ${
                activeResearchTask.status === "completed"
                  ? "bg-green-500"
                  : activeResearchTask.status === "failed"
                  ? "bg-red-500"
                  : activeResearchTask.status === "cancelled"
                  ? "bg-gray-500"
                  : "bg-blue-500"
              }`}
              style={{ width: `${activeResearchTask.progress}%` }}
            ></div>
          </div>
        </div>

        {/* Query display */}
        <div className="mt-3 p-2 bg-gray-50 rounded text-sm text-gray-700">
          <span className="font-medium">Query: </span>
          <span className="italic">"{activeResearchTask.query}"</span>
        </div>

        {/* Connection status */}
        {researchConnectionStatus !== "connected" && (
          <div className="mt-2 flex items-center space-x-2 text-xs text-amber-600">
            <span>⚠️</span>
            <span>
              {researchConnectionStatus === "connecting"
                ? "Connecting to research system..."
                : researchConnectionStatus === "error"
                ? "Connection error"
                : "Disconnected from research system"}
            </span>
          </div>
        )}
      </div>

      {/* Expanded details */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-medium text-gray-900 mb-1">
                Task Details
              </h4>
              <div className="grid grid-cols-2 gap-2 text-xs text-gray-600">
                <div>
                  <span className="font-medium">Task ID:</span>{" "}
                  {activeResearchTask.task_id}
                </div>
                <div>
                  <span className="font-medium">Status:</span>{" "}
                  {activeResearchTask.status}
                </div>
                <div>
                  <span className="font-medium">Started:</span>{" "}
                  {new Date(activeResearchTask.created_at).toLocaleTimeString()}
                </div>
                <div>
                  <span className="font-medium">Updated:</span>{" "}
                  {new Date(activeResearchTask.updated_at).toLocaleTimeString()}
                </div>
              </div>
            </div>

            {activeResearchTask.error && (
              <div>
                <h4 className="text-sm font-medium text-red-900 mb-1">Error</h4>
                <p className="text-xs text-red-700 bg-red-50 p-2 rounded">
                  {activeResearchTask.error}
                </p>
              </div>
            )}

            {activeResearchTask.results && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-1">
                  Results Preview
                </h4>
                <div className="text-xs text-gray-600 bg-white p-2 rounded border">
                  {activeResearchTask.results.search_results && (
                    <p>
                      Found {activeResearchTask.results.search_results.length}{" "}
                      search results
                    </p>
                  )}
                  {activeResearchTask.results.synthesis && (
                    <p className="mt-1 italic">
                      "{activeResearchTask.results.synthesis.substring(0, 100)}
                      ..."
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default ResearchProgress
