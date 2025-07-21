import React, { useState, useEffect, useCallback } from "react"
import {
  DocumentTextIcon,
  PencilIcon,
  CheckIcon,
  XMarkIcon,
  ClockIcon,
  ExclamationTriangleIcon,
} from "@heroicons/react/24/outline"

interface ResearchPlan {
  raw_plan?: string
  objectives?: string[] | string
  key_areas?: string[] | string
  questions?: string[] | string
  sources?: string[] | string
  outcomes?: string[] | string
}

interface ResearchPlanData {
  task_id: string
  research_plan: ResearchPlan | null
  plan_approved: boolean
  created_at: string
  updated_at: string
}

interface Props {
  taskId: string
  onPlanApproved?: () => void
}

const ResearchPlanViewer: React.FC<Props> = ({ taskId, onPlanApproved }) => {
  const [planData, setPlanData] = useState<ResearchPlanData | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [editedPlan, setEditedPlan] = useState<ResearchPlan>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Helper function to convert array to text for editing
  const arrayToText = (arr: string[] | string | undefined): string => {
    if (!arr) return ""

    if (Array.isArray(arr)) {
      return arr.join("\n")
    } else if (typeof arr === "string") {
      return arr
    } else {
      return String(arr)
    }
  }

  // Helper function to convert text to array for saving
  const textToArray = (text: string): string[] => {
    return text
      .split("\n")
      .map((line) => line.trim())
      .filter((line) => line.length > 0)
  }

  // Helper function to render array as list
  const renderArrayAsList = (
    arr: string[] | string | undefined
  ): React.ReactNode => {
    // Handle different data types that might be passed
    let items: string[] = []

    if (!arr) {
      return null
    }

    if (Array.isArray(arr)) {
      items = arr
    } else if (typeof arr === "string") {
      // If it's a string, split by newlines and clean up
      items = arr
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
    } else {
      // Fallback: convert to string and handle as text
      items = String(arr)
        .split("\n")
        .map((line) => line.trim())
        .filter((line) => line.length > 0)
    }

    if (items.length === 0) return null

    return (
      <div className="space-y-2">
        {items.map((item, index) => (
          <div
            key={index}
            className="flex items-start space-x-3 p-2 rounded-md bg-white border border-gray-100"
          >
            <span className="flex-shrink-0 w-2 h-2 bg-blue-500 rounded-full mt-2"></span>
            <span className="text-sm text-gray-700 leading-relaxed">
              {item}
            </span>
          </div>
        ))}
      </div>
    )
  }

  const loadPlan = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      const response = await fetch(`/api/research/task/${taskId}/plan`)
      if (response.ok) {
        const data = await response.json()
        setPlanData(data)
        if (data.research_plan) {
          setEditedPlan(data.research_plan)
        }
      } else if (response.status === 404) {
        setPlanData({
          task_id: taskId,
          research_plan: null,
          plan_approved: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
      } else {
        throw new Error("Failed to load research plan")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error occurred")
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    loadPlan()
  }, [loadPlan])

  const handleSavePlan = async () => {
    try {
      setSaving(true)
      setError(null)

      const response = await fetch(`/api/research/task/${taskId}/plan`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          research_plan: editedPlan,
        }),
      })

      if (response.ok) {
        await loadPlan() // Reload the plan data
        setEditing(false)
      } else {
        throw new Error("Failed to save research plan")
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save plan")
    } finally {
      setSaving(false)
    }
  }

  const handleApprovePlan = async (approved: boolean) => {
    try {
      setError(null)

      const response = await fetch(
        `/api/research/task/${taskId}/plan/approve`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ approved }),
        }
      )

      if (response.ok) {
        await loadPlan() // Reload the plan data
        if (approved && onPlanApproved) {
          onPlanApproved()
        }
      } else {
        throw new Error(
          `Failed to ${approved ? "approve" : "reject"} research plan`
        )
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update approval status"
      )
    }
  }

  const handleCancelEdit = () => {
    setEditing(false)
    if (planData?.research_plan) {
      setEditedPlan(planData.research_plan)
    }
    setError(null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="flex items-center space-x-2">
          <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <span className="text-gray-600">Loading research plan...</span>
        </div>
      </div>
    )
  }

  if (!planData?.research_plan) {
    return (
      <div className="text-center p-8 text-gray-500">
        <DocumentTextIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
        <p>No research plan available yet</p>
        <p className="text-sm">
          The plan will appear here once the planning stage is complete
        </p>
      </div>
    )
  }

  const plan = planData.research_plan

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <DocumentTextIcon className="h-6 w-6 text-blue-600" />
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                Research Plan
              </h3>
              <p className="text-sm text-gray-500">
                {planData.plan_approved ? (
                  <span className="inline-flex items-center space-x-1 text-green-600">
                    <CheckIcon className="h-4 w-4" />
                    <span>Approved</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center space-x-1 text-yellow-600">
                    <ClockIcon className="h-4 w-4" />
                    <span>Waiting for approval</span>
                  </span>
                )}
              </p>
            </div>
          </div>

          {!planData.plan_approved && !editing && (
            <button
              onClick={() => setEditing(true)}
              className="inline-flex items-center space-x-2 px-3 py-2 text-sm border border-gray-300 rounded-md hover:bg-gray-50"
            >
              <PencilIcon className="h-4 w-4" />
              <span>Edit Plan</span>
            </button>
          )}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div className="p-4 bg-red-50 border-b border-red-200">
          <div className="flex items-center space-x-2 text-red-800">
            <ExclamationTriangleIcon className="h-4 w-4" />
            <span className="text-sm">{error}</span>
          </div>
        </div>
      )}

      {/* Plan content */}
      <div className="p-4 space-y-4">
        {/* Show structured sections if available, otherwise show raw plan */}
        {plan.objectives ||
        plan.key_areas ||
        plan.questions ||
        plan.sources ||
        plan.outcomes ? (
          <>
            {/* Objectives */}
            {(plan.objectives || editing) && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">
                  Research Objectives
                </h4>
                {editing ? (
                  <div>
                    <textarea
                      value={arrayToText(editedPlan.objectives)}
                      onChange={(e) =>
                        setEditedPlan((prev) => ({
                          ...prev,
                          objectives: textToArray(e.target.value),
                        }))
                      }
                      className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter research objectives (one per line)..."
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter each objective on a separate line
                    </p>
                  </div>
                ) : (
                  <div className="bg-gray-50 p-3 rounded-md">
                    {renderArrayAsList(plan.objectives)}
                  </div>
                )}
              </div>
            )}

            {/* Key Areas */}
            {(plan.key_areas || editing) && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">
                  Key Areas to Investigate
                </h4>
                {editing ? (
                  <div>
                    <textarea
                      value={arrayToText(editedPlan.key_areas)}
                      onChange={(e) =>
                        setEditedPlan((prev) => ({
                          ...prev,
                          key_areas: textToArray(e.target.value),
                        }))
                      }
                      className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter key areas to investigate (one per line)..."
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter each area on a separate line
                    </p>
                  </div>
                ) : (
                  <div className="bg-gray-50 p-3 rounded-md">
                    {renderArrayAsList(plan.key_areas)}
                  </div>
                )}
              </div>
            )}

            {/* Questions */}
            {(plan.questions || editing) && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">
                  Specific Questions
                </h4>
                {editing ? (
                  <div>
                    <textarea
                      value={arrayToText(editedPlan.questions)}
                      onChange={(e) =>
                        setEditedPlan((prev) => ({
                          ...prev,
                          questions: textToArray(e.target.value),
                        }))
                      }
                      className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter specific questions to answer (one per line)..."
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter each question on a separate line
                    </p>
                  </div>
                ) : (
                  <div className="bg-gray-50 p-3 rounded-md">
                    {renderArrayAsList(plan.questions)}
                  </div>
                )}
              </div>
            )}

            {/* Sources */}
            {(plan.sources || editing) && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">
                  Information Sources
                </h4>
                {editing ? (
                  <div>
                    <textarea
                      value={arrayToText(editedPlan.sources)}
                      onChange={(e) =>
                        setEditedPlan((prev) => ({
                          ...prev,
                          sources: textToArray(e.target.value),
                        }))
                      }
                      className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter information sources to consult (one per line)..."
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter each source on a separate line
                    </p>
                  </div>
                ) : (
                  <div className="bg-gray-50 p-3 rounded-md">
                    {renderArrayAsList(plan.sources)}
                  </div>
                )}
              </div>
            )}

            {/* Expected Outcomes */}
            {(plan.outcomes || editing) && (
              <div>
                <h4 className="text-sm font-medium text-gray-900 mb-2">
                  Expected Outcomes
                </h4>
                {editing ? (
                  <div>
                    <textarea
                      value={arrayToText(editedPlan.outcomes)}
                      onChange={(e) =>
                        setEditedPlan((prev) => ({
                          ...prev,
                          outcomes: textToArray(e.target.value),
                        }))
                      }
                      className="w-full h-24 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      placeholder="Enter expected outcomes (one per line)..."
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      Enter each outcome on a separate line
                    </p>
                  </div>
                ) : (
                  <div className="bg-gray-50 p-3 rounded-md">
                    {renderArrayAsList(plan.outcomes)}
                  </div>
                )}
              </div>
            )}
          </>
        ) : plan.raw_plan ? (
          /* Show raw plan if no structured sections available */
          <div>
            <h4 className="text-sm font-medium text-gray-900 mb-2">
              Complete Plan
            </h4>
            {editing ? (
              <textarea
                value={editedPlan.raw_plan || ""}
                onChange={(e) =>
                  setEditedPlan((prev) => ({
                    ...prev,
                    raw_plan: e.target.value,
                  }))
                }
                className="w-full h-32 px-3 py-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                placeholder="Enter the complete research plan..."
              />
            ) : (
              <p className="text-sm text-gray-700 whitespace-pre-wrap bg-gray-50 p-3 rounded-md">
                {plan.raw_plan}
              </p>
            )}
          </div>
        ) : (
          /* No plan data available */
          <div className="text-center p-8 text-gray-500">
            <DocumentTextIcon className="h-12 w-12 mx-auto mb-4 text-gray-300" />
            <p>No plan content available</p>
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="border-t border-gray-200 p-4">
        {editing ? (
          <div className="flex items-center justify-between">
            <button
              onClick={handleCancelEdit}
              className="px-4 py-2 text-sm text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <div className="flex items-center space-x-3">
              <button
                onClick={handleSavePlan}
                disabled={saving}
                className="inline-flex items-center space-x-2 px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              >
                {saving && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                <span>Save Changes</span>
              </button>
            </div>
          </div>
        ) : !planData.plan_approved ? (
          <div className="flex items-center justify-end space-x-3">
            <button
              onClick={() => handleApprovePlan(false)}
              className="inline-flex items-center space-x-2 px-4 py-2 text-sm text-red-700 border border-red-300 rounded-md hover:bg-red-50"
            >
              <XMarkIcon className="h-4 w-4" />
              <span>Reject</span>
            </button>
            <button
              onClick={() => handleApprovePlan(true)}
              className="inline-flex items-center space-x-2 px-4 py-2 text-sm bg-green-600 text-white rounded-md hover:bg-green-700"
            >
              <CheckIcon className="h-4 w-4" />
              <span>Approve Plan</span>
            </button>
          </div>
        ) : (
          <div className="text-center text-sm text-gray-500">
            This research plan has been approved and research can proceed.
          </div>
        )}
      </div>
    </div>
  )
}

export default ResearchPlanViewer
