import React, { useState } from "react"
import {
  BeakerIcon,
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  PlayIcon,
} from "@heroicons/react/24/outline"

interface ResearchTask {
  id: string
  title: string
  status: "pending" | "running" | "completed" | "error"
  query: string
  results?: string
  createdAt: Date
}

const ResearchWorkspace: React.FC = () => {
  const [tasks, setTasks] = useState<ResearchTask[]>([])
  const [newQuery, setNewQuery] = useState("")

  const startResearch = async () => {
    if (!newQuery.trim()) return

    const newTask: ResearchTask = {
      id: Date.now().toString(),
      title: `Research: ${newQuery.substring(0, 50)}${
        newQuery.length > 50 ? "..." : ""
      }`,
      status: "pending",
      query: newQuery,
      createdAt: new Date(),
    }

    setTasks((prev) => [newTask, ...prev])
    const query = newQuery
    setNewQuery("")

    try {
      // Start research task via API
      const response = await fetch("/api/research/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_id: "research_session",
          query: query,
          research_mode: "comprehensive",
          max_results: 10,
        }),
      })

      if (response.ok) {
        const result = await response.json()

        // Update task with server task ID and status
        setTasks((prev) =>
          prev.map((task) =>
            task.id === newTask.id
              ? { ...task, id: result.task_id, status: "running" }
              : task
          )
        )

        // Poll for task completion
        pollTaskStatus(result.task_id, newTask.id)
      } else {
        // Handle error
        setTasks((prev) =>
          prev.map((task) =>
            task.id === newTask.id
              ? {
                  ...task,
                  status: "error",
                  results: "Failed to start research task",
                }
              : task
          )
        )
      }
    } catch (error) {
      console.error("Error starting research:", error)
      setTasks((prev) =>
        prev.map((task) =>
          task.id === newTask.id
            ? { ...task, status: "error", results: "Network error" }
            : task
        )
      )
    }
  }

  const pollTaskStatus = async (taskId: string, localTaskId: string) => {
    const maxPolls = 30 // 5 minutes max
    let pollCount = 0

    const poll = async () => {
      try {
        const response = await fetch(`/api/research/task/${taskId}`)
        if (response.ok) {
          const task = await response.json()

          if (task.status === "completed" || task.status === "failed") {
            // Task completed
            setTasks((prev) =>
              prev.map((t) =>
                t.id === localTaskId || t.id === taskId
                  ? {
                      ...t,
                      status:
                        task.status === "completed" ? "completed" : "error",
                      results: task.results
                        ? JSON.stringify(task.results, null, 2)
                        : task.status === "failed"
                        ? "Research failed"
                        : undefined,
                    }
                  : t
              )
            )
          } else if (pollCount < maxPolls) {
            // Continue polling
            pollCount++
            setTimeout(poll, 10000) // Poll every 10 seconds
          } else {
            // Timeout
            setTasks((prev) =>
              prev.map((t) =>
                t.id === localTaskId || t.id === taskId
                  ? { ...t, status: "error", results: "Research timed out" }
                  : t
              )
            )
          }
        }
      } catch (error) {
        console.error("Error polling task status:", error)
      }
    }

    // Start polling after a short delay
    setTimeout(poll, 2000)
  }

  const getStatusColor = (status: ResearchTask["status"]) => {
    switch (status) {
      case "pending":
        return "text-gray-500 bg-gray-100"
      case "running":
        return "text-blue-500 bg-blue-100"
      case "completed":
        return "text-green-500 bg-green-100"
      case "error":
        return "text-red-500 bg-red-100"
    }
  }

  const getStatusIcon = (status: ResearchTask["status"]) => {
    switch (status) {
      case "pending":
        return ClipboardDocumentListIcon
      case "running":
        return PlayIcon
      case "completed":
        return DocumentTextIcon
      case "error":
        return DocumentTextIcon
    }
  }

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <BeakerIcon className="h-8 w-8 text-blue-600" />
          <div>
            <h1 className="text-2xl font-bold text-gray-900">
              Research Workspace
            </h1>
            <p className="text-gray-600">AI-powered research and analysis</p>
          </div>
        </div>

        {/* Research input */}
        <div className="flex space-x-4">
          <input
            type="text"
            value={newQuery}
            onChange={(e) => setNewQuery(e.target.value)}
            placeholder="Enter your research query..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            onKeyPress={(e) => e.key === "Enter" && startResearch()}
          />
          <button
            onClick={startResearch}
            disabled={!newQuery.trim()}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            <BeakerIcon className="h-5 w-5" />
            <span>Start Research</span>
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Tasks panel */}
        <div className="w-1/3 bg-white border-r border-gray-200 p-4 overflow-y-auto">
          <h3 className="text-lg font-semibold mb-4">Research Tasks</h3>

          {tasks.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <BeakerIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No research tasks yet</p>
              <p className="text-sm">Start a new research query above</p>
            </div>
          ) : (
            <div className="space-y-3">
              {tasks.map((task) => {
                const StatusIcon = getStatusIcon(task.status)
                return (
                  <div
                    key={task.id}
                    className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50"
                  >
                    <div className="flex items-start space-x-3">
                      <StatusIcon className="h-5 w-5 mt-0.5 text-gray-400" />
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {task.title}
                        </h4>
                        <p className="text-xs text-gray-500 mt-1">
                          {task.createdAt.toLocaleTimeString()}
                        </p>
                        <span
                          className={`inline-block px-2 py-1 text-xs rounded-full mt-2 ${getStatusColor(
                            task.status
                          )}`}
                        >
                          {task.status}
                        </span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Results panel */}
        <div className="flex-1 p-4 overflow-y-auto">
          <h3 className="text-lg font-semibold mb-4">Research Results</h3>

          {tasks.filter((t) => t.results).length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <DocumentTextIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No results yet</p>
              <p className="text-sm">
                Complete research tasks will appear here
              </p>
            </div>
          ) : (
            <div className="space-y-6">
              {tasks
                .filter((task) => task.results)
                .map((task) => (
                  <div
                    key={task.id}
                    className="bg-white border border-gray-200 rounded-lg p-4"
                  >
                    <h4 className="font-semibold text-gray-900 mb-2">
                      {task.title}
                    </h4>
                    <div className="text-sm text-gray-600 whitespace-pre-wrap">
                      {task.results}
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

export default ResearchWorkspace
