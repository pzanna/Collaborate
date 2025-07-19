import React, { useState, useEffect, useCallback } from "react"

interface DebugPlan {
  plan_id: string
  context_id: string
  prompt: string
  raw_response: string
  parsed_tasks: Array<{
    task_id: string
    agent: string
    action: string
    [key: string]: any
  }>
  created_at: string
  execution_status: string
  modifications: Array<{
    timestamp: string
    type: string
    changes: Record<string, any>
  }>
}

interface DebugUIProps {
  className?: string
}

const DebugUI: React.FC<DebugUIProps> = ({ className = "" }) => {
  const [plans, setPlans] = useState<DebugPlan[]>([])
  const [selectedPlan, setSelectedPlan] = useState<DebugPlan | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [modifications, setModifications] = useState<Record<string, any>>({})

  // Fetch plans list
  const fetchPlans = useCallback(async () => {
    try {
      setIsLoading(true)
      const response = await fetch("/api/debug/plans")
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const data = await response.json()
      setPlans(data.plans || [])
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch plans")
      console.error("Failed to fetch plans:", err)
    } finally {
      setIsLoading(false)
    }
  }, [])

  // Fetch latest plan
  const fetchLatestPlan = useCallback(async () => {
    try {
      const response = await fetch("/api/debug/plans/latest")
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const plan = await response.json()
      setSelectedPlan(plan)
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch latest plan"
      )
      console.error("Failed to fetch latest plan:", err)
    }
  }, [])

  // Fetch specific plan
  const fetchPlan = async (planId: string) => {
    try {
      const response = await fetch(`/api/debug/plans/${planId}`)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }
      const plan = await response.json()
      setSelectedPlan(plan)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch plan")
      console.error("Failed to fetch plan:", err)
    }
  }

  // Apply modifications to a plan
  const applyModifications = async () => {
    if (!selectedPlan || Object.keys(modifications).length === 0) return

    try {
      const response = await fetch(
        `/api/debug/plans/${selectedPlan.plan_id}/modify`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify(modifications),
        }
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      // Refresh the plan to see changes
      await fetchPlan(selectedPlan.plan_id)
      setModifications({})
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to apply modifications"
      )
      console.error("Failed to apply modifications:", err)
    }
  }

  useEffect(() => {
    fetchPlans()
    fetchLatestPlan()
  }, [fetchPlans, fetchLatestPlan])

  const formatDate = (dateString: string) => {
    try {
      return new Date(dateString).toLocaleString()
    } catch {
      return dateString
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case "planning":
        return "bg-yellow-100 text-yellow-800 border-yellow-200"
      case "executing":
        return "bg-blue-100 text-blue-800 border-blue-200"
      case "completed":
        return "bg-green-100 text-green-800 border-green-200"
      case "failed":
        return "bg-red-100 text-red-800 border-red-200"
      default:
        return "bg-gray-100 text-gray-800 border-gray-200"
    }
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Debug UI</h1>
          <p className="text-gray-600">
            Inspect and modify RM AI plans and decisions
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={fetchLatestPlan}
            className="px-4 py-2 text-sm font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors"
          >
            Load Latest Plan
          </button>

          <button
            onClick={fetchPlans}
            disabled={isLoading}
            className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors disabled:opacity-50"
          >
            {isLoading ? "Loading..." : "Refresh"}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <div className="flex items-center gap-2">
            <span className="text-red-500">⚠️</span>
            <span className="text-red-700">{error}</span>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Plans List */}
        <div className="lg:col-span-1">
          <div className="border border-gray-200 rounded-lg">
            <div className="border-b border-gray-200 p-4">
              <h2 className="text-lg font-semibold">Recent Plans</h2>
            </div>

            <div className="p-4 space-y-2 max-h-96 overflow-y-auto">
              {plans.map((plan) => (
                <div
                  key={plan.plan_id}
                  className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                    selectedPlan?.plan_id === plan.plan_id
                      ? "border-blue-500 bg-blue-50"
                      : "border-gray-200 hover:border-gray-300"
                  }`}
                  onClick={() => fetchPlan(plan.plan_id)}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium truncate">
                      {plan.plan_id}
                    </span>
                    <span
                      className={`px-2 py-1 text-xs font-medium rounded border ${getStatusColor(
                        plan.execution_status
                      )}`}
                    >
                      {plan.execution_status}
                    </span>
                  </div>

                  <div className="text-xs text-gray-600">
                    Context: {plan.context_id}
                  </div>

                  <div className="text-xs text-gray-500 mt-1">
                    {formatDate(plan.created_at)}
                  </div>

                  {plan.modifications && plan.modifications.length > 0 && (
                    <div className="text-xs text-orange-600 mt-1">
                      {plan.modifications.length} modification(s)
                    </div>
                  )}
                </div>
              ))}

              {plans.length === 0 && !isLoading && (
                <div className="text-center py-8 text-gray-500">
                  No plans found
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Plan Details */}
        <div className="lg:col-span-2">
          {!selectedPlan ? (
            <div className="border border-gray-200 rounded-lg p-6">
              <div className="text-center text-gray-500">
                <div className="text-lg font-medium mb-2">No Plan Selected</div>
                <div className="text-sm">
                  Select a plan from the list to view details and make
                  modifications
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Plan Header */}
              <div className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-semibold">
                    {selectedPlan.plan_id}
                  </h2>
                  <span
                    className={`px-3 py-1 text-sm font-medium rounded border ${getStatusColor(
                      selectedPlan.execution_status
                    )}`}
                  >
                    {selectedPlan.execution_status}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">Context ID:</span>
                    <div className="font-mono text-xs">
                      {selectedPlan.context_id}
                    </div>
                  </div>

                  <div>
                    <span className="text-gray-600">Created:</span>
                    <div>{formatDate(selectedPlan.created_at)}</div>
                  </div>
                </div>
              </div>

              {/* Prompt */}
              <div className="border border-gray-200 rounded-lg">
                <div className="border-b border-gray-200 p-4">
                  <h3 className="text-lg font-medium">Original Prompt</h3>
                </div>
                <div className="p-4">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap overflow-x-auto bg-gray-50 p-3 rounded">
                    {selectedPlan.prompt}
                  </pre>
                </div>
              </div>

              {/* Raw Response */}
              <div className="border border-gray-200 rounded-lg">
                <div className="border-b border-gray-200 p-4">
                  <h3 className="text-lg font-medium">RM AI Raw Response</h3>
                </div>
                <div className="p-4">
                  <pre className="text-sm text-gray-700 whitespace-pre-wrap overflow-x-auto bg-gray-50 p-3 rounded max-h-64">
                    {selectedPlan.raw_response}
                  </pre>
                </div>
              </div>

              {/* Parsed Tasks */}
              <div className="border border-gray-200 rounded-lg">
                <div className="border-b border-gray-200 p-4">
                  <h3 className="text-lg font-medium">Parsed Tasks</h3>
                </div>
                <div className="p-4">
                  <div className="space-y-3">
                    {selectedPlan.parsed_tasks.map((task, index) => (
                      <div key={index} className="bg-gray-50 p-3 rounded-lg">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium">{task.task_id}</span>
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                              {task.agent}
                            </span>
                            <span className="px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                              {task.action}
                            </span>
                          </div>
                        </div>

                        {Object.keys(task).filter(
                          (key) => !["task_id", "agent", "action"].includes(key)
                        ).length > 0 && (
                          <pre className="text-xs text-gray-600 mt-2">
                            {JSON.stringify(
                              Object.fromEntries(
                                Object.entries(task).filter(
                                  ([key]) =>
                                    !["task_id", "agent", "action"].includes(
                                      key
                                    )
                                )
                              ),
                              null,
                              2
                            )}
                          </pre>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </div>

              {/* Modifications */}
              {selectedPlan.modifications &&
                selectedPlan.modifications.length > 0 && (
                  <div className="border border-gray-200 rounded-lg">
                    <div className="border-b border-gray-200 p-4">
                      <h3 className="text-lg font-medium">
                        Applied Modifications
                      </h3>
                    </div>
                    <div className="p-4">
                      <div className="space-y-3">
                        {selectedPlan.modifications.map((mod, index) => (
                          <div
                            key={index}
                            className="bg-orange-50 border border-orange-200 p-3 rounded-lg"
                          >
                            <div className="flex items-center justify-between mb-2">
                              <span className="font-medium">{mod.type}</span>
                              <span className="text-xs text-gray-500">
                                {formatDate(mod.timestamp)}
                              </span>
                            </div>
                            <pre className="text-xs text-gray-700">
                              {JSON.stringify(mod.changes, null, 2)}
                            </pre>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}

              {/* Modification Interface */}
              <div className="border border-gray-200 rounded-lg">
                <div className="border-b border-gray-200 p-4">
                  <h3 className="text-lg font-medium">Make Modifications</h3>
                </div>
                <div className="p-4">
                  <div className="space-y-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-2">
                        Modification JSON
                      </label>
                      <textarea
                        className="w-full h-32 p-3 border border-gray-300 rounded-lg font-mono text-sm"
                        placeholder='{"type": "task_override", "task_id": "task_1", "changes": {"priority": "high"}}'
                        value={JSON.stringify(modifications, null, 2)}
                        onChange={(e) => {
                          try {
                            const parsed = JSON.parse(e.target.value || "{}")
                            setModifications(parsed)
                          } catch {
                            // Invalid JSON, keep as string for now
                          }
                        }}
                      />
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={applyModifications}
                        disabled={Object.keys(modifications).length === 0}
                        className="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-blue-600 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        Apply Modifications
                      </button>

                      <button
                        onClick={() => setModifications({})}
                        className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-50 border border-gray-200 rounded-lg hover:bg-gray-100 transition-colors"
                      >
                        Clear
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default DebugUI
