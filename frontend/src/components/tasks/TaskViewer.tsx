import React, { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "../ui/card"
import { Badge } from "../ui/badge"
import { Button } from "../ui/button"
import {
  ArrowPathIcon,
  PlayIcon,
  PauseIcon,
  XMarkIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
} from "@heroicons/react/24/outline"
import { Input } from "../ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select"
import TaskGraph from "./TaskGraph"
import TaskDetails from "./TaskDetails"

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

interface TaskGraphData {
  tasks: Task[]
  connections: Array<{
    from: string
    to: string
    type: string
  }>
  statistics: {
    total_tasks: number
    status_breakdown: Record<string, number>
    agent_breakdown: Record<string, number>
    connection_count: number
  }
}

interface TaskViewerProps {
  className?: string
}

const TaskViewer: React.FC<TaskViewerProps> = ({ className = "" }) => {
  const [taskData, setTaskData] = useState<TaskGraphData | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState("")
  const [statusFilter, setStatusFilter] = useState("all")
  const [agentFilter, setAgentFilter] = useState("all")
  const [viewMode, setViewMode] = useState<"list" | "graph">("list")
  const [autoRefresh, setAutoRefresh] = useState(true)
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [ws, setWs] = useState<WebSocket | null>(null)

  // Fetch task data from API
  const fetchTasks = useCallback(async () => {
    try {
      setIsLoading(true)
      const response = await fetch("/api/tasks/active")
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data: TaskGraphData = await response.json()
      setTaskData(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch tasks")
      console.error("Failed to fetch tasks:", err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // WebSocket connection for real-time updates (disabled for now)
  useEffect(() => {
    // Temporarily disabled to prevent connection errors
    // TODO: Re-enable when backend WebSocket endpoints are available
    console.log("WebSocket connection disabled")
  }, [])

  // Initial data fetch
  useEffect(() => {
    fetchTasks()
  }, [fetchTasks])

  // Filter tasks based on search and filters
  const filteredTasks =
    taskData?.tasks.filter((task) => {
      const matchesSearch =
        searchTerm === "" ||
        task.task_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        task.agent_type.toLowerCase().includes(searchTerm.toLowerCase()) ||
        task.stage.toLowerCase().includes(searchTerm.toLowerCase())

      const matchesStatus =
        statusFilter === "all" || task.status === statusFilter
      const matchesAgent =
        agentFilter === "all" || task.agent_type === agentFilter

      return matchesSearch && matchesStatus && matchesAgent
    }) || []

  const handleTaskSelect = (task: Task) => {
    setSelectedTask(task)

    // Request detailed task information via WebSocket (disabled)
    // if (ws && ws.readyState === WebSocket.OPEN) {
    //   ws.send(
    //     JSON.stringify({
    //       type: "get_task_details",
    //       task_id: task.task_id,
    //     })
    //   )
    // }
  }

  const handleTaskCancel = async (taskId: string) => {
    try {
      const response = await fetch(`/api/tasks/${taskId}/cancel`, {
        method: "POST",
      })

      if (!response.ok) {
        throw new Error(`Failed to cancel task: ${response.statusText}`)
      }

      // Also send via WebSocket for immediate feedback (disabled)
      // if (ws && ws.readyState === WebSocket.OPEN) {
      //   ws.send(
      //     JSON.stringify({
      //       type: "cancel_task",
      //       task_id: taskId,
      //     })
      //   )
      // }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to cancel task")
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "pending":
        return "bg-yellow-100 text-yellow-800"
      case "running":
        return "bg-blue-100 text-blue-800"
      case "completed":
        return "bg-green-100 text-green-800"
      case "failed":
        return "bg-red-100 text-red-800"
      case "cancelled":
        return "bg-gray-100 text-gray-800"
      default:
        return "bg-gray-100 text-gray-800"
    }
  }

  const uniqueStatuses = Array.from(
    new Set(taskData?.tasks.map((t) => t.status) || [])
  )
  const uniqueAgents = Array.from(
    new Set(taskData?.tasks.map((t) => t.agent_type) || [])
  )

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Task Viewer</h1>
          <p className="text-gray-600">
            Monitor and manage active research tasks
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setAutoRefresh(!autoRefresh)}
          >
            {autoRefresh ? (
              <PauseIcon className="w-4 h-4" />
            ) : (
              <PlayIcon className="w-4 h-4" />
            )}
            {autoRefresh ? "Pause" : "Resume"}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={fetchTasks}
            disabled={isLoading}
          >
            <ArrowPathIcon
              className={`w-4 h-4 ${isLoading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
      </div>

      {/* Statistics */}
      {taskData?.statistics && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold">
                {taskData.statistics.total_tasks}
              </div>
              <div className="text-sm text-gray-600">Total Tasks</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-blue-600">
                {taskData.statistics.status_breakdown.running || 0}
              </div>
              <div className="text-sm text-gray-600">Running</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-green-600">
                {taskData.statistics.status_breakdown.completed || 0}
              </div>
              <div className="text-sm text-gray-600">Completed</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4">
              <div className="text-2xl font-bold text-red-600">
                {taskData.statistics.status_breakdown.failed || 0}
              </div>
              <div className="text-sm text-gray-600">Failed</div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters and Search */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <MagnifyingGlassIcon className="w-4 h-4 text-gray-500" />
              <Input
                placeholder="Search tasks..."
                value={searchTerm}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                  setSearchTerm(e.target.value)
                }
                className="w-64"
              />
            </div>

            <div className="flex items-center gap-2">
              <FunnelIcon className="w-4 h-4 text-gray-500" />
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  {uniqueStatuses.map((status) => (
                    <SelectItem key={status} value={status}>
                      {status}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Select value={agentFilter} onValueChange={setAgentFilter}>
                <SelectTrigger className="w-32">
                  <SelectValue placeholder="Agent" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Agents</SelectItem>
                  {uniqueAgents.map((agent) => (
                    <SelectItem key={agent} value={agent}>
                      {agent}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2">
              <Button
                variant={viewMode === "list" ? "default" : "outline"}
                size="sm"
                onClick={() => setViewMode("list")}
              >
                List
              </Button>
              <Button
                variant={viewMode === "graph" ? "default" : "outline"}
                size="sm"
                onClick={() => setViewMode("graph")}
              >
                Graph
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <XMarkIcon className="w-5 h-5 text-red-500" />
            <span className="text-red-700">{error}</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Task List/Graph */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>
                {viewMode === "list" ? "Task List" : "Task Graph"}(
                {filteredTasks.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <ArrowPathIcon className="w-8 h-8 animate-spin text-gray-500" />
                  <span className="ml-2 text-gray-600">Loading tasks...</span>
                </div>
              ) : viewMode === "list" ? (
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {filteredTasks.map((task) => (
                    <div
                      key={task.task_id}
                      className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                        selectedTask?.task_id === task.task_id
                          ? "border-blue-500 bg-blue-50"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                      onClick={() => handleTaskSelect(task)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <Badge className={getStatusColor(task.status)}>
                            {task.status}
                          </Badge>
                          <span className="font-medium">{task.task_id}</span>
                          <span className="text-sm text-gray-600">
                            {task.agent_type}
                          </span>
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="text-xs text-gray-500">
                            {task.stage}
                          </span>
                          {task.status === "running" && (
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={(e: React.MouseEvent) => {
                                e.stopPropagation()
                                handleTaskCancel(task.task_id)
                              }}
                            >
                              <XMarkIcon className="w-3 h-3" />
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}

                  {filteredTasks.length === 0 && (
                    <div className="text-center py-8 text-gray-500">
                      No tasks found
                    </div>
                  )}
                </div>
              ) : (
                <TaskGraph
                  tasks={filteredTasks}
                  connections={taskData?.connections || []}
                  onTaskSelect={handleTaskSelect}
                  selectedTaskId={selectedTask?.task_id}
                />
              )}
            </CardContent>
          </Card>
        </div>

        {/* Task Details */}
        <div>
          <TaskDetails task={selectedTask} onCancel={handleTaskCancel} />
        </div>
      </div>

      {/* Connection Status */}
      <div className="flex items-center justify-between text-sm text-gray-500">
        <div>
          WebSocket:{" "}
          {ws?.readyState === WebSocket.OPEN ? (
            <span className="text-green-600">Connected</span>
          ) : (
            <span className="text-red-600">Disconnected</span>
          )}
        </div>

        <div>
          Auto-refresh:{" "}
          {autoRefresh ? (
            <span className="text-green-600">Enabled</span>
          ) : (
            <span className="text-gray-600">Disabled</span>
          )}
        </div>
      </div>
    </div>
  )
}

export default TaskViewer
