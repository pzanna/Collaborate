import React, { useState, useEffect } from "react"
import {
  BeakerIcon,
  ClipboardDocumentListIcon,
  DocumentTextIcon,
  PlayIcon,
} from "@heroicons/react/24/outline"
import { apiService, Project } from "../../services/api"
import ResearchPlanViewer from "./ResearchPlanViewer"

interface ResearchTask {
  id: string
  title: string
  status: "pending" | "running" | "completed" | "error" | "waiting_approval"
  stage?: string
  query: string
  results?: string
  createdAt: Date
}

const ResearchWorkspace: React.FC = () => {
  const [tasks, setTasks] = useState<ResearchTask[]>([])
  const [newQuery, setNewQuery] = useState("")
  const [projects, setProjects] = useState<Project[]>([])
  const [selectedProjectId, setSelectedProjectId] = useState<string>("")
  const [isLoadingProjects, setIsLoadingProjects] = useState(true)
  const [isLoadingTasks, setIsLoadingTasks] = useState(true)
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null)

  // Load projects on component mount
  useEffect(() => {
    const loadProjects = async () => {
      try {
        const projectsData = await apiService.getProjects()
        setProjects(projectsData)
        // Auto-select first project if available
        if (projectsData.length > 0) {
          setSelectedProjectId(projectsData[0].id)
        }
      } catch (error) {
        console.error("Failed to load projects:", error)
      } finally {
        setIsLoadingProjects(false)
      }
    }

    loadProjects()
  }, [])

  // Load existing research tasks
  useEffect(() => {
    const loadTasks = async () => {
      try {
        setIsLoadingTasks(true)
        const response = await fetch("/api/research-tasks?limit=50")
        if (response.ok) {
          const apiTasks = await response.json()

          // Convert API tasks to our local task format
          const convertedTasks: ResearchTask[] = apiTasks.map(
            (apiTask: any) => ({
              id: apiTask.task_id,
              title:
                apiTask.name ||
                apiTask.query?.substring(0, 50) +
                  (apiTask.query?.length > 50 ? "..." : ""),
              status: mapApiStatusToUIStatus(apiTask.status, apiTask.stage),
              stage: apiTask.stage,
              query: apiTask.query,
              createdAt: new Date(apiTask.created_at),
            })
          )

          setTasks(convertedTasks)

          // Auto-select the most recent task if none selected
          if (convertedTasks.length > 0 && !selectedTaskId) {
            setSelectedTaskId(convertedTasks[0].id)
          }
        }
      } catch (error) {
        console.error("Failed to load research tasks:", error)
      } finally {
        setIsLoadingTasks(false)
      }
    }

    loadTasks()
  }, [selectedTaskId])

  // Helper function to map API status to UI status
  const mapApiStatusToUIStatus = (
    apiStatus: string,
    stage?: string
  ): ResearchTask["status"] => {
    if (apiStatus === "completed") return "completed"
    if (apiStatus === "failed") return "error"
    if (apiStatus === "waiting_approval" || stage === "planning_complete")
      return "waiting_approval"
    if (apiStatus === "running" || apiStatus === "pending") return "running"
    return "pending"
  }

  const startResearch = async () => {
    if (!newQuery.trim()) return
    if (!selectedProjectId) {
      alert("Please select a project first")
      return
    }

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
      // Start research task via API with project_id
      const response = await fetch("/api/research/start", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          project_id: selectedProjectId, // Add project_id
          conversation_id: "research_session",
          query: query,
          name: `Research: ${query.substring(0, 50)}${
            query.length > 50 ? "..." : ""
          }`, // Add task name
          research_mode: "comprehensive",
          max_results: 10,
        }),
      })

      if (response.ok) {
        const result = await response.json()

        // Update task with server task ID
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

  // Refresh a specific task from the server
  const refreshTask = async (taskId: string) => {
    try {
      const response = await fetch(`/api/research/task/${taskId}`)
      if (response.ok) {
        const apiTask = await response.json()

        const updatedTask: ResearchTask = {
          id: apiTask.task_id,
          title:
            apiTask.name ||
            apiTask.query?.substring(0, 50) +
              (apiTask.query?.length > 50 ? "..." : ""),
          status: mapApiStatusToUIStatus(apiTask.status, apiTask.stage),
          stage: apiTask.stage,
          query: apiTask.query,
          results: apiTask.results
            ? JSON.stringify(apiTask.results, null, 2)
            : undefined,
          createdAt: new Date(apiTask.created_at),
        }

        setTasks((prev) =>
          prev.map((task) => (task.id === taskId ? updatedTask : task))
        )

        return updatedTask
      }
    } catch (error) {
      console.error("Error refreshing task:", error)
    }
    return null
  }

  const pollTaskStatus = async (taskId: string, localTaskId: string) => {
    const maxPolls = 30 // 5 minutes max
    let pollCount = 0

    const poll = async () => {
      try {
        const response = await fetch(`/api/research/task/${taskId}`)
        if (response.ok) {
          const task = await response.json()

          // Map status from API response
          let uiStatus: ResearchTask["status"] = "running"
          if (task.status === "completed") {
            uiStatus = "completed"
          } else if (task.status === "failed") {
            uiStatus = "error"
          } else if (
            task.status === "waiting_approval" ||
            task.stage === "planning_complete"
          ) {
            uiStatus = "waiting_approval"
          } else if (task.status === "running" || task.status === "pending") {
            uiStatus = "running"
          }

          if (task.status === "completed" || task.status === "failed") {
            // Task completed or failed
            setTasks((prev) =>
              prev.map((t) =>
                t.id === localTaskId || t.id === taskId
                  ? {
                      ...t,
                      status: uiStatus,
                      stage: task.stage,
                      results: task.results
                        ? JSON.stringify(task.results, null, 2)
                        : task.status === "failed"
                        ? "Research failed"
                        : undefined,
                    }
                  : t
              )
            )
          } else if (uiStatus === "waiting_approval") {
            // Task is waiting for plan approval
            setTasks((prev) =>
              prev.map((t) =>
                t.id === localTaskId || t.id === taskId
                  ? { ...t, status: "waiting_approval", stage: task.stage }
                  : t
              )
            )
            // Don't continue polling for tasks waiting approval
            return
          } else if (pollCount < maxPolls) {
            // Task still running - update status and continue polling
            setTasks((prev) =>
              prev.map((t) =>
                t.id === localTaskId || t.id === taskId
                  ? {
                      ...t,
                      status: uiStatus,
                      stage: task.stage,
                      results: task.progress
                        ? `Progress: ${Math.round(task.progress)}%`
                        : undefined,
                    }
                  : t
              )
            )
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
      case "waiting_approval":
        return "text-yellow-500 bg-yellow-100"
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
      case "waiting_approval":
        return ClipboardDocumentListIcon
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

        {/* Project selector */}
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Project
          </label>
          {isLoadingProjects ? (
            <div className="flex items-center space-x-2 p-2">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-gray-600">Loading projects...</span>
            </div>
          ) : projects.length === 0 ? (
            <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
              <p className="text-yellow-800 text-sm">
                No projects available. Please create a project first.
              </p>
            </div>
          ) : (
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="">Select a project...</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          )}
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
            disabled={!newQuery.trim() || !selectedProjectId}
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
        <div className="w-1/4 bg-white border-r border-gray-200 p-4 overflow-y-auto">
          <h3 className="text-lg font-semibold mb-4">Research Tasks</h3>

          {isLoadingTasks ? (
            <div className="text-center text-gray-500 mt-8">
              <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p>Loading research tasks...</p>
            </div>
          ) : tasks.length === 0 ? (
            <div className="text-center text-gray-500 mt-8">
              <BeakerIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>No research tasks yet</p>
              <p className="text-sm">Start a new research query above</p>
            </div>
          ) : (
            <div className="space-y-3">
              {tasks.map((task) => {
                const StatusIcon = getStatusIcon(task.status)
                const isSelected = selectedTaskId === task.id
                return (
                  <div
                    key={task.id}
                    onClick={() => setSelectedTaskId(task.id)}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      isSelected
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:bg-gray-50"
                    }`}
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
                          {task.status === "waiting_approval"
                            ? "awaiting approval"
                            : task.status}
                        </span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Research Plan panel */}
        <div className="w-1/2 border-r border-gray-200 overflow-y-auto">
          {selectedTaskId ? (
            <div className="p-4">
              <ResearchPlanViewer
                taskId={selectedTaskId}
                onPlanApproved={() => {
                  // Refresh the specific task when plan is approved
                  refreshTask(selectedTaskId).then((updatedTask) => {
                    // If task status changed from waiting_approval to running, restart polling
                    if (updatedTask && updatedTask.status === "running") {
                      pollTaskStatus(selectedTaskId, selectedTaskId)
                    }
                  })
                }}
              />
            </div>
          ) : (
            <div className="p-4 text-center text-gray-500 mt-8">
              <ClipboardDocumentListIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Select a research task to view its plan</p>
              <p className="text-sm">
                Click on a task from the left panel to see details and manage
                the research plan
              </p>
            </div>
          )}
        </div>

        {/* Results panel */}
        <div className="flex-1 p-4 overflow-y-auto">
          <h3 className="text-lg font-semibold mb-4">Research Results</h3>

          {selectedTaskId ? (
            (() => {
              const selectedTask = tasks.find((t) => t.id === selectedTaskId)
              return selectedTask?.results ? (
                <div className="bg-white border border-gray-200 rounded-lg p-4">
                  <h4 className="font-semibold text-gray-900 mb-2">
                    {selectedTask.title}
                  </h4>
                  <div className="text-sm text-gray-600 whitespace-pre-wrap">
                    {selectedTask.results}
                  </div>
                </div>
              ) : selectedTask?.status === "completed" ? (
                <div className="text-center text-gray-500 mt-8">
                  <DocumentTextIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>Research completed but no results available</p>
                  <p className="text-sm">
                    The research task finished but didn't produce visible
                    results
                  </p>
                </div>
              ) : (
                <div className="text-center text-gray-500 mt-8">
                  <DocumentTextIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
                  <p>No results yet</p>
                  <p className="text-sm">
                    {selectedTask?.status === "running"
                      ? "Research is in progress..."
                      : selectedTask?.status === "waiting_approval"
                      ? "Waiting for plan approval..."
                      : selectedTask?.status === "error"
                      ? "Research failed"
                      : "Complete the research task to see results"}
                  </p>
                </div>
              )
            })()
          ) : (
            <div className="text-center text-gray-500 mt-8">
              <DocumentTextIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
              <p>Select a task to view results</p>
              <p className="text-sm">
                Choose a research task from the left panel to see its results
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default ResearchWorkspace
