import React from "react"

interface Task {
  task_id: string
  parent_id?: string
  agent_type: string
  status: string
  stage: string
  created_at: string
  updated_at: string
  content: Record<string, any>
  metadata?: Record<string, any>
  dependencies: string[]
  children: string[]
}

interface TaskDetailsProps {
  task: Task | null
  onCancel: (taskId: string) => void
  className?: string
}

const TaskDetails: React.FC<TaskDetailsProps> = ({
  task,
  onCancel,
  className = "",
}) => {
  if (!task) {
    return (
      <div className={`border border-gray-200 rounded-lg p-6 ${className}`}>
        <div className="text-center text-gray-500">
          <div className="text-lg font-medium mb-2">No Task Selected</div>
          <div className="text-sm">
            Select a task from the list or graph to view details
          </div>
        </div>
      </div>
    )
  }

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString()
    } catch {
      return dateString
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "pending":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "running":
        return "bg-blue-100 text-blue-800 border-blue-200"
      case "completed":
        return "bg-green-100 text-green-800 border-green-200"
      case "failed":
        return "bg-red-100 text-red-800 border-red-200"
      case "cancelled":
        return "bg-gray-100 text-gray-800 border-gray-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  const getAgentIcon = (agentType: string) => {
    switch (agentType.toLowerCase()) {
      case "retriever":
        return "🔍"
      case "planning":
        return "🧠"
      case "executor":
        return "⚡"
      case "memory":
        return "💾"
      default:
        return "🤖"
    }
  }

  return (
    <div className={`border border-gray-200 rounded-lg ${className}`}>
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <span className="text-2xl">{getAgentIcon(task.agent_type)}</span>
          <div>
            <h3 className="text-lg font-semibold">{task.task_id}</h3>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`px-2 py-1 text-xs font-medium rounded border ${getStatusColor(
                  task.status
                )}`}
              >
                {task.status}
              </span>
              <span className="text-sm text-gray-600">{task.agent_type}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="p-4 space-y-4">
        {/* Basic Info */}
        <div>
          <h4 className="text-sm font-medium text-gray-900 mb-2">
            Basic Information
          </h4>
          <div className="bg-gray-50 rounded-lg p-3 space-y-2">
            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Stage:</span>
              <span className="font-medium">{task.stage}</span>
            </div>

            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Created:</span>
              <span className="font-medium">{formatDate(task.created_at)}</span>
            </div>

            <div className="flex justify-between text-sm">
              <span className="text-gray-600">Updated:</span>
              <span className="font-medium">{formatDate(task.updated_at)}</span>
            </div>

            {task.parent_id && (
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Parent:</span>
                <span className="font-medium font-mono text-xs">
                  {task.parent_id}
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Dependencies */}
        {task.dependencies.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Dependencies
            </h4>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="space-y-1">
                {task.dependencies.map((dep, index) => (
                  <div
                    key={index}
                    className="text-sm font-mono text-xs text-gray-700"
                  >
                    {dep}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Children */}
        {task.children.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Child Tasks
            </h4>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="space-y-1">
                {task.children.map((child, index) => (
                  <div
                    key={index}
                    className="text-sm font-mono text-xs text-gray-700"
                  >
                    {child}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        {Object.keys(task.content).length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Task Content
            </h4>
            <div className="bg-gray-50 rounded-lg p-3">
              <pre className="text-xs text-gray-700 whitespace-pre-wrap overflow-x-auto">
                {JSON.stringify(task.content, null, 2)}
              </pre>
            </div>
          </div>
        )}

        {/* Metadata */}
        {task.metadata && Object.keys(task.metadata).length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">Metadata</h4>
            <div className="bg-gray-50 rounded-lg p-3">
              <div className="space-y-2">
                {Object.entries(task.metadata).map(([key, value]) => (
                  <div key={key} className="flex justify-between text-sm">
                    <span className="text-gray-600">{key}:</span>
                    <span className="font-medium text-right ml-2">
                      {typeof value === "string"
                        ? value
                        : JSON.stringify(value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Actions */}
        {task.status === "running" && (
          <div className="pt-4 border-t border-gray-200">
            <button
              onClick={() => onCancel(task.task_id)}
              className="w-full px-4 py-2 text-sm font-medium text-red-700 bg-red-50 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
            >
              Cancel Task
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

export default TaskDetails
