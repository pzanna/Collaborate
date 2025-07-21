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

interface Connection {
  from: string
  to: string
  type: string
}

interface TaskGraphProps {
  tasks: Task[]
  connections: Connection[]
  onTaskSelect: (task: Task) => void
  selectedTaskId?: string
  className?: string
}

const TaskGraph: React.FC<TaskGraphProps> = ({
  tasks,
  connections,
  onTaskSelect,
  selectedTaskId,
  className = "",
}) => {
  // For now, implement a simple network visualization
  // In a full implementation, you'd use a library like D3.js, vis.js, or react-flow

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "pending":
        return "#fbbf24"
      case "running":
        return "#3b82f6"
      case "completed":
        return "#10b981"
      case "failed":
        return "#ef4444"
      case "cancelled":
        return "#6b7280"
      default:
        return "#6b7280"
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
    <div
      className={`relative w-full h-96 border border-gray-200 rounded-lg overflow-hidden ${className}`}
    >
      {tasks.length === 0 ? (
        <div className="flex items-center justify-center h-full text-gray-500">
          No tasks to display
        </div>
      ) : (
        <div className="p-4">
          <div className="text-center text-gray-600 mb-4">
            Interactive Task Graph
          </div>

          {/* Simple grid layout for tasks */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {tasks.map((task, index) => (
              <div
                key={task.task_id}
                className={`relative p-3 border rounded-lg cursor-pointer transition-all ${
                  selectedTaskId === task.task_id
                    ? "border-blue-500 bg-blue-50 shadow-md"
                    : "border-gray-200 hover:border-gray-300 hover:shadow-sm"
                }`}
                style={{
                  borderLeftColor: getStatusColor(task.status),
                  borderLeftWidth: "4px",
                }}
                onClick={() => onTaskSelect(task)}
              >
                <div className="flex items-start gap-2">
                  <span className="text-lg">
                    {getAgentIcon(task.agent_type)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">
                      {task.task_id}
                    </div>
                    <div className="text-xs text-gray-600 truncate">
                      {task.agent_type}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {task.stage}
                    </div>
                  </div>
                </div>

                {/* Connection indicators */}
                <div className="flex justify-between items-center mt-2 text-xs text-gray-400">
                  <span>
                    {task.dependencies.length > 0 &&
                      `↑${task.dependencies.length}`}
                  </span>
                  <span>
                    {task.children.length > 0 && `↓${task.children.length}`}
                  </span>
                </div>

                {/* Status indicator */}
                <div
                  className="absolute top-1 right-1 w-3 h-3 rounded-full"
                  style={{ backgroundColor: getStatusColor(task.status) }}
                  title={task.status}
                />
              </div>
            ))}
          </div>

          {/* Connection summary */}
          {connections.length > 0 && (
            <div className="mt-4 text-sm text-gray-600 text-center">
              {connections.length} connections between tasks
            </div>
          )}

          {/* Note about full graph view */}
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="text-sm text-blue-800">
              📊 <strong>Graph Visualization</strong>
            </div>
            <div className="text-xs text-blue-600 mt-1">
              This is a simplified view. A full interactive network graph would
              show task dependencies and relationships using a library like
              D3.js or React Flow.
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default TaskGraph
