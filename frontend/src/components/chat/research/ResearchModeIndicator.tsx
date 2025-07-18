import React from "react"
import { useSelector } from "react-redux"
import { RootState } from "../../../store/store"

interface ResearchModeIndicatorProps {
  className?: string
}

const ResearchModeIndicator: React.FC<ResearchModeIndicatorProps> = ({
  className = "",
}) => {
  const { isResearchMode, activeResearchTask } = useSelector(
    (state: RootState) => state.chat
  )

  if (!isResearchMode || !activeResearchTask) {
    return null
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "starting":
      case "planning":
        return "bg-blue-100 text-blue-800"
      case "retrieval":
        return "bg-yellow-100 text-yellow-800"
      case "reasoning":
        return "bg-purple-100 text-purple-800"
      case "execution":
        return "bg-orange-100 text-orange-800"
      case "synthesis":
        return "bg-indigo-100 text-indigo-800"
      case "completed":
        return "bg-green-100 text-green-800"
      case "failed":
      case "cancelled":
        return "bg-red-100 text-red-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "starting":
      case "planning":
        return "🎯"
      case "retrieval":
        return "🔍"
      case "reasoning":
        return "🧠"
      case "execution":
        return "⚡"
      case "synthesis":
        return "📝"
      case "completed":
        return "✅"
      case "failed":
        return "❌"
      case "cancelled":
        return "⏹️"
      default:
        return "🔄"
    }
  }

  return (
    <div
      className={`flex items-center space-x-3 p-3 bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg ${className}`}
    >
      <div className="flex items-center space-x-2">
        <div className="w-2 h-2 bg-blue-500 rounded-full animate-pulse"></div>
        <span className="text-sm font-medium text-gray-700">Research Mode</span>
      </div>

      <div className="flex items-center space-x-2">
        <span className="text-sm">
          {getStatusIcon(activeResearchTask.status)}
        </span>
        <span
          className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(
            activeResearchTask.status
          )}`}
        >
          {activeResearchTask.status.charAt(0).toUpperCase() +
            activeResearchTask.status.slice(1)}
        </span>
      </div>

      <div className="flex items-center space-x-2">
        <div className="w-20 bg-gray-200 rounded-full h-2">
          <div
            className="bg-blue-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${activeResearchTask.progress}%` }}
          ></div>
        </div>
        <span className="text-xs text-gray-600">
          {Math.round(activeResearchTask.progress)}%
        </span>
      </div>

      {activeResearchTask.query && (
        <div className="flex-1 min-w-0">
          <p className="text-sm text-gray-600 truncate">
            "{activeResearchTask.query}"
          </p>
        </div>
      )}
    </div>
  )
}

export default ResearchModeIndicator
