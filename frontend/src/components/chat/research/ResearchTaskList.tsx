import React from "react"
import { useSelector } from "react-redux"
import { RootState } from "../../../store/store"
import { ResearchTask } from "../../../store/slices/chatSlice"
import ResearchResults from "./ResearchResults"

interface ResearchTaskListProps {
  conversationId: string
  className?: string
}

const ResearchTaskList: React.FC<ResearchTaskListProps> = ({
  conversationId,
  className = "",
}) => {
  const { researchTasks } = useSelector((state: RootState) => state.chat)

  const tasks = researchTasks[conversationId] || []

  if (tasks.length === 0) {
    return null
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-green-600"
      case "failed":
        return "text-red-600"
      case "cancelled":
        return "text-gray-600"
      default:
        return "text-blue-600"
    }
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <h3 className="text-lg font-medium text-gray-900">Research Tasks</h3>

      <div className="space-y-3">
        {tasks.map((task: ResearchTask) => (
          <div
            key={task.task_id}
            className="bg-white border border-gray-200 rounded-lg shadow-sm"
          >
            <div className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <span className="text-lg">{getStatusIcon(task.status)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h4 className="text-sm font-medium text-gray-900 truncate">
                        "{task.query}"
                      </h4>
                      <span
                        className={`text-xs font-medium ${getStatusColor(
                          task.status
                        )}`}
                      >
                        {task.status}
                      </span>
                    </div>

                    <div className="mt-1 flex items-center space-x-4 text-xs text-gray-500">
                      <span>
                        Started: {new Date(task.created_at).toLocaleString()}
                      </span>
                      <span>Progress: {task.progress}%</span>
                    </div>

                    {task.status !== "completed" &&
                      task.status !== "failed" &&
                      task.status !== "cancelled" && (
                        <div className="mt-2">
                          <div className="w-full bg-gray-200 rounded-full h-1">
                            <div
                              className="bg-blue-500 h-1 rounded-full transition-all duration-300"
                              style={{ width: `${task.progress}%` }}
                            ></div>
                          </div>
                        </div>
                      )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  <span className="text-xs text-gray-500">
                    {task.task_id.substring(0, 8)}...
                  </span>
                </div>
              </div>

              {task.error && (
                <div className="mt-3 p-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">
                  <span className="font-medium">Error:</span> {task.error}
                </div>
              )}
            </div>

            {task.status === "completed" && task.results && (
              <div className="border-t border-gray-200">
                <ResearchResults task={task} />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default ResearchTaskList
