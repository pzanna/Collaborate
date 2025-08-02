import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  Edit,
  Trash2,
  ArrowLeft,
  Calendar,
  AlertCircle,
  Loader2,
  Save,
  X,
  Check,
  Sparkles,
  DollarSign,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  apiClient,
  type ResearchPlan,
  type UpdateResearchPlanRequest,
  type GenerateAIResearchPlanRequest,
  type ExecuteResearchRequest,
} from "@/utils/api"
import { ROUTES, getProjectDetailsPath } from "@/utils/routes"

// Component to display structured research plan content
function PlanStructureDisplay({
  planStructure,
}: {
  planStructure: Record<string, any>
}) {
  if (!planStructure) return null

  return (
    <div className="space-y-6">
      {planStructure.objectives && Array.isArray(planStructure.objectives) && (
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
          <h4 className="font-semibold text-blue-900 mb-3 flex items-center">
            📋 Research Objectives
          </h4>
          <ul className="space-y-2">
            {planStructure.objectives.map(
              (objective: string, index: number) => (
                <li key={index} className="flex items-start">
                  <span className="w-6 h-6 bg-blue-100 text-blue-800 rounded-full text-xs font-medium flex items-center justify-center mr-3 flex-shrink-0">
                    {index + 1}
                  </span>
                  <span className="text-sm text-gray-700">{objective}</span>
                </li>
              )
            )}
          </ul>
        </div>
      )}

      {planStructure.key_areas && Array.isArray(planStructure.key_areas) && (
        <div className="bg-green-50 p-4 rounded-lg border border-green-200">
          <h4 className="font-semibold text-green-900 mb-3 flex items-center">
            🎯 Key Research Areas
          </h4>
          <ul className="space-y-2">
            {planStructure.key_areas.map((area: string, index: number) => (
              <li key={index} className="flex items-start">
                <span className="w-6 h-6 bg-green-100 text-green-800 rounded-full text-xs font-medium flex items-center justify-center mr-3 flex-shrink-0">
                  {index + 1}
                </span>
                <span className="text-sm text-gray-700">{area}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {planStructure.questions && Array.isArray(planStructure.questions) && (
        <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
          <h4 className="font-semibold text-purple-900 mb-3 flex items-center">
            ❓ Research Questions
          </h4>
          <ul className="space-y-2">
            {planStructure.questions.map((question: string, index: number) => (
              <li key={index} className="flex items-start">
                <span className="w-6 h-6 bg-purple-100 text-purple-800 rounded-full text-xs font-medium flex items-center justify-center mr-3 flex-shrink-0">
                  {index + 1}
                </span>
                <span className="text-sm text-gray-700">{question}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {planStructure.sources && Array.isArray(planStructure.sources) && (
        <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
          <h4 className="font-semibold text-yellow-900 mb-3 flex items-center">
            📚 Data Sources
          </h4>
          <div className="flex flex-wrap gap-2">
            {planStructure.sources.map((source: string, index: number) => (
              <span
                key={index}
                className="inline-block bg-yellow-100 text-yellow-800 text-xs font-medium px-2.5 py-0.5 rounded-full"
              >
                {source}
              </span>
            ))}
          </div>
        </div>
      )}

      {planStructure.timeline && (
        <div className="bg-orange-50 p-4 rounded-lg border border-orange-200">
          <h4 className="font-semibold text-orange-900 mb-3 flex items-center">
            ⏱️ Timeline
          </h4>
          <div className="space-y-2">
            {planStructure.timeline.total_days && (
              <div className="text-sm">
                <span className="font-medium text-gray-700">
                  Total Duration:
                </span>{" "}
                <span className="text-orange-700 font-semibold">
                  {planStructure.timeline.total_days} days
                </span>
              </div>
            )}
            {planStructure.timeline.phases && (
              <div>
                <span className="font-medium text-gray-700 text-sm">
                  Phases:
                </span>
                <div className="mt-2 grid grid-cols-2 md:grid-cols-4 gap-2">
                  {Object.entries(planStructure.timeline.phases).map(
                    ([phase, days]) => (
                      <div
                        key={phase}
                        className="bg-orange-100 p-2 rounded text-center"
                      >
                        <div className="text-xs font-medium text-orange-800 capitalize">
                          {phase.replace("_", " ")}
                        </div>
                        <div className="text-sm font-semibold text-orange-900">
                          {String(days)} days
                        </div>
                      </div>
                    )
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {planStructure.outcomes && Array.isArray(planStructure.outcomes) && (
        <div className="bg-indigo-50 p-4 rounded-lg border border-indigo-200">
          <h4 className="font-semibold text-indigo-900 mb-3 flex items-center">
            🎯 Expected Outcomes
          </h4>
          <ul className="space-y-2">
            {planStructure.outcomes.map((outcome: string, index: number) => (
              <li key={index} className="flex items-start">
                <span className="w-6 h-6 bg-indigo-100 text-indigo-800 rounded-full text-xs font-medium flex items-center justify-center mr-3 flex-shrink-0">
                  {index + 1}
                </span>
                <span className="text-sm text-gray-700">{outcome}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

export function ResearchPlanDetails() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [researchPlan, setResearchPlan] = useState<ResearchPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [isStartingResearch, setIsStartingResearch] = useState(false)
  const [researchExecuted, setResearchExecuted] = useState(false)
  const [showAIDialog, setShowAIDialog] = useState(false)
  const [showCostDialog, setShowCostDialog] = useState(false)
  const [showDepthDialog, setShowDepthDialog] = useState(false)
  const [selectedDepth, setSelectedDepth] = useState<
    "undergraduate" | "masters" | "phd"
  >("masters")
  const [isGeneratingAI, setIsGeneratingAI] = useState(false)
  const [aiPlanData, setAiPlanData] = useState<ResearchPlan | null>(null)
  const [editFormData, setEditFormData] = useState({
    name: "",
    description: "",
    plan_structure: "",
  })
  const [aiFormData, setAiFormData] = useState({
    name: "",
    description: "",
    plan_type: "comprehensive",
  })

  // Load research plan on component mount
  useEffect(() => {
    if (!id) {
      navigate(ROUTES.PROJECTS)
      return
    }
    loadResearchPlan()
  }, [id, navigate])

  // Check if research has been executed based on plan status or metadata
  useEffect(() => {
    if (researchPlan) {
      // Check if plan status is "completed" or if there's execution metadata
      const statusCompleted = researchPlan.status === "completed"
      const executionMetadata =
        researchPlan.metadata?.execution_started || false

      // Research is considered executed if status is completed OR execution has started
      setResearchExecuted(statusCompleted || executionMetadata)
    }
  }, [researchPlan])

  // Currency conversion (USD to AUD - using approximate rate)
  const USD_TO_AUD_RATE = 1.55 // This would typically come from an API

  const convertToAUD = (usdAmount: number): number => {
    return usdAmount * USD_TO_AUD_RATE
  }

  const formatAUD = (amount: number): string => {
    return `$${amount.toFixed(2)}`
  }

  const getCostBreakdown = () => {
    if (!researchPlan) return null

    const estimatedCostUSD = researchPlan.estimated_cost || 0
    const actualCostUSD = researchPlan.actual_cost || 0

    // Extract cost estimate from metadata if available
    const metadata = researchPlan.metadata || {}
    const costEstimate = metadata.cost_estimate || {}

    // Create breakdown structure
    const breakdown = {
      estimated: {
        total_usd: estimatedCostUSD,
        total_aud: convertToAUD(estimatedCostUSD),
        ai_operations: {
          usd: costEstimate.estimated_cost || estimatedCostUSD * 0.1,
          aud: convertToAUD(
            costEstimate.estimated_cost || estimatedCostUSD * 0.1
          ),
          complexity: costEstimate.complexity || "MEDIUM",
        },
        traditional_costs: {
          database_access: {
            usd: estimatedCostUSD * 0.3,
            aud: convertToAUD(estimatedCostUSD * 0.3),
          },
          analysis_software: {
            usd: estimatedCostUSD * 0.2,
            aud: convertToAUD(estimatedCostUSD * 0.2),
          },
          expert_consultation: {
            usd: estimatedCostUSD * 0.4,
            aud: convertToAUD(estimatedCostUSD * 0.4),
          },
        },
      },
      actual: {
        total_usd: actualCostUSD,
        total_aud: convertToAUD(actualCostUSD),
        ai_operations: {
          usd: actualCostUSD * 0.1,
          aud: convertToAUD(actualCostUSD * 0.1),
        },
        other_costs: {
          usd: actualCostUSD * 0.9,
          aud: convertToAUD(actualCostUSD * 0.9),
        },
      },
      optimization_suggestions: costEstimate.optimization_suggestions || [
        "Consider breaking down into smaller sub-tasks",
        "Use caching to avoid redundant analysis",
        "Optimize AI model usage for cost efficiency",
      ],
    }

    return breakdown
  }

  const loadResearchPlan = async () => {
    if (!id) return

    try {
      setLoading(true)
      setError(null)

      const planData = await apiClient.getResearchPlan(id)
      setResearchPlan(planData)

      // Initialize edit form data
      setEditFormData({
        name: planData.name,
        description: planData.description || "",
        plan_structure: formatPlanStructure(planData.plan_structure),
      })
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load research plan"
      )
      console.error("Error loading research plan:", err)
    } finally {
      setLoading(false)
    }
  }

  const formatPlanStructure = (planStructure?: Record<string, any>): string => {
    if (!planStructure) return ""

    let formatted = ""

    // Handle AI-generated plan structure format
    if (planStructure.objectives && Array.isArray(planStructure.objectives)) {
      formatted += "📋 OBJECTIVES:\n"
      planStructure.objectives.forEach((obj: string, index: number) => {
        formatted += `${index + 1}. ${obj}\n`
      })
      formatted += "\n"
    }

    if (planStructure.key_areas && Array.isArray(planStructure.key_areas)) {
      formatted += "🎯 KEY RESEARCH AREAS:\n"
      planStructure.key_areas.forEach((area: string, index: number) => {
        formatted += `${index + 1}. ${area}\n`
      })
      formatted += "\n"
    }

    if (planStructure.questions && Array.isArray(planStructure.questions)) {
      formatted += "❓ RESEARCH QUESTIONS:\n"
      planStructure.questions.forEach((question: string, index: number) => {
        formatted += `${index + 1}. ${question}\n`
      })
      formatted += "\n"
    }

    if (planStructure.sources && Array.isArray(planStructure.sources)) {
      formatted += "📚 DATA SOURCES:\n"
      planStructure.sources.forEach((source: string, index: number) => {
        formatted += `${index + 1}. ${source}\n`
      })
      formatted += "\n"
    }

    if (planStructure.timeline) {
      formatted += "⏱️ TIMELINE:\n"
      if (planStructure.timeline.total_days) {
        formatted += `Total Duration: ${planStructure.timeline.total_days} days\n`
      }
      if (planStructure.timeline.phases) {
        formatted += "Phases:\n"
        Object.entries(planStructure.timeline.phases).forEach(
          ([phase, days]) => {
            formatted += `  • ${phase
              .replace("_", " ")
              .toUpperCase()}: ${days} days\n`
          }
        )
      }
      formatted += "\n"
    }

    if (planStructure.outcomes && Array.isArray(planStructure.outcomes)) {
      formatted += "🎯 EXPECTED OUTCOMES:\n"
      planStructure.outcomes.forEach((outcome: string, index: number) => {
        formatted += `${index + 1}. ${outcome}\n`
      })
      formatted += "\n"
    }

    // Fallback for legacy format
    if (!formatted) {
      if (planStructure.sections && Array.isArray(planStructure.sections)) {
        formatted += planStructure.sections.join("\n") + "\n\n"
      }
      if (planStructure.details) {
        formatted += planStructure.details
      }
    }

    return formatted
  }

  const parsePlanStructure = (structureText: string): Record<string, any> => {
    if (!structureText.trim()) {
      return {}
    }

    // Try to parse the structured format used by the display component
    const result: Record<string, any> = {}
    const lines = structureText.split("\n")
    let currentSection = ""
    let currentItems: string[] = []

    for (const line of lines) {
      const trimmedLine = line.trim()

      if (trimmedLine.startsWith("📋 OBJECTIVES:")) {
        if (currentSection && currentItems.length > 0) {
          result[currentSection] = currentItems
        }
        currentSection = "objectives"
        currentItems = []
      } else if (trimmedLine.startsWith("🎯 KEY RESEARCH AREAS:")) {
        if (currentSection && currentItems.length > 0) {
          result[currentSection] = currentItems
        }
        currentSection = "key_areas"
        currentItems = []
      } else if (trimmedLine.startsWith("❓ RESEARCH QUESTIONS:")) {
        if (currentSection && currentItems.length > 0) {
          result[currentSection] = currentItems
        }
        currentSection = "questions"
        currentItems = []
      } else if (trimmedLine.startsWith("📚 DATA SOURCES:")) {
        if (currentSection && currentItems.length > 0) {
          result[currentSection] = currentItems
        }
        currentSection = "sources"
        currentItems = []
      } else if (trimmedLine.startsWith("🎯 EXPECTED OUTCOMES:")) {
        if (currentSection && currentItems.length > 0) {
          result[currentSection] = currentItems
        }
        currentSection = "outcomes"
        currentItems = []
      } else if (trimmedLine.startsWith("⏱️ TIMELINE:")) {
        if (currentSection && currentItems.length > 0) {
          result[currentSection] = currentItems
        }
        currentSection = "timeline"
        currentItems = []
      } else if (trimmedLine.match(/^\d+\./)) {
        // Extract numbered list item
        const item = trimmedLine.replace(/^\d+\.\s*/, "")
        if (item && currentSection) {
          currentItems.push(item)
        }
      } else if (trimmedLine && currentSection === "timeline") {
        // Handle timeline content specially
        if (!result.timeline) {
          result.timeline = {}
        }
        if (trimmedLine.startsWith("Total Duration:")) {
          const days = trimmedLine.match(/(\d+)\s*days/)
          if (days) {
            result.timeline.total_days = parseInt(days[1])
          }
        }
        // Could add more timeline parsing here if needed
      }
    }

    // Don't forget the last section
    if (currentSection && currentItems.length > 0) {
      result[currentSection] = currentItems
    }

    // Fallback for simple text format
    if (Object.keys(result).length === 0 && structureText.trim()) {
      const sections = lines.filter((line) => line.trim().match(/^\d+\./))
      const details = lines
        .filter((line) => !line.trim().match(/^\d+\./) && line.trim())
        .join("\n")

      return {
        sections: sections.length > 0 ? sections : undefined,
        details: details || structureText.trim(),
      }
    }

    return result
  }

  const handleEdit = () => {
    setIsEditing(true)
    setError(null)
  }

  const handleCancelEdit = () => {
    if (!researchPlan) return

    // Reset form data to original values
    setEditFormData({
      name: researchPlan.name,
      description: researchPlan.description || "",
      plan_structure: formatPlanStructure(researchPlan.plan_structure),
    })
    setIsEditing(false)
    setError(null)
  }

  const handleSaveEdit = async () => {
    try {
      if (!editFormData.name.trim() || !id) {
        setError("Research plan name is required")
        return
      }

      setIsSaving(true)
      setError(null)

      const updateData: UpdateResearchPlanRequest = {
        name: editFormData.name,
        description: editFormData.description,
        plan_structure: parsePlanStructure(editFormData.plan_structure),
      }

      const updatedPlan = await apiClient.updateResearchPlan(id, updateData)

      // Update the research plan state
      setResearchPlan(updatedPlan)

      // Update the edit form data to match the saved plan to ensure consistency
      setEditFormData({
        name: updatedPlan.name,
        description: updatedPlan.description || "",
        plan_structure: formatPlanStructure(updatedPlan.plan_structure),
      })

      // Only exit edit mode after everything is properly updated
      setIsEditing(false)
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update research plan"
      )
      console.error("Error updating research plan:", err)
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (
      !researchPlan ||
      !window.confirm(`Are you sure you want to delete "${researchPlan.name}"?`)
    ) {
      return
    }

    try {
      await apiClient.deleteResearchPlan(researchPlan.id)
      navigate(-1) // Go back to previous page
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete research plan"
      )
      console.error("Error deleting research plan:", err)
    }
  }

  const handleApprove = async () => {
    if (!researchPlan) return

    setIsApproving(true)
    try {
      const approvedPlan = await apiClient.approveResearchPlan(researchPlan.id)
      setResearchPlan(approvedPlan)
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to approve research plan"
      )
      console.error("Error approving research plan:", err)
    } finally {
      setIsApproving(false)
    }
  }

  const handleStartResearch = async () => {
    if (!researchPlan) return

    setIsStartingResearch(true)
    try {
      const executeRequest: ExecuteResearchRequest = {
        task_type: "literature_review", // Default to literature review
        depth: selectedDepth, // Use selected depth
      }

      const response = await apiClient.executeResearch(
        researchPlan.topic_id,
        executeRequest
      )

      // Update the research plan metadata to mark execution as started
      try {
        const updatedMetadata = {
          ...researchPlan.metadata,
          execution_started: true,
          execution_id: response.execution_id,
          execution_timestamp: new Date().toISOString(),
        }

        const updateRequest: UpdateResearchPlanRequest = {
          metadata: updatedMetadata,
        }

        const updatedPlan = await apiClient.updateResearchPlan(
          researchPlan.id,
          updateRequest
        )
        setResearchPlan(updatedPlan)
      } catch (metadataError) {
        console.warn("Failed to update research plan metadata:", metadataError)
        // Continue anyway since the main execution succeeded
      }

      // Mark research as executed and close the dialog
      setResearchExecuted(true)
      setShowDepthDialog(false)
      setError(null)

      // Show success message
      console.log("Research execution started successfully:", response)

      // Start polling for status updates to detect completion
      startStatusPolling()

      // You could add a success notification here or redirect to progress page
      // For now, we'll just disable the button to show it's been executed
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to start research execution"
      )
      console.error("Error starting research execution:", err)
    } finally {
      setIsStartingResearch(false)
    }
  }

  const handleConfirmDepthAndStartResearch = () => {
    setShowDepthDialog(false)
    handleStartResearch()
  }

  const startStatusPolling = () => {
    // Poll every 30 seconds to check for completion
    const pollInterval = setInterval(async () => {
      try {
        if (!id) return

        const updatedPlan = await apiClient.getResearchPlan(id)

        // Check if status has changed to completed
        if (
          updatedPlan.status === "completed" &&
          researchPlan?.status !== "completed"
        ) {
          console.log("Research plan completed!")
          setResearchPlan(updatedPlan)
          clearInterval(pollInterval) // Stop polling once completed
        }
      } catch (error) {
        console.warn("Failed to poll plan status:", error)
        // Continue polling even if individual requests fail
      }
    }, 30000) // Poll every 30 seconds

    // Auto-cleanup after 1 hour to prevent infinite polling
    setTimeout(() => {
      clearInterval(pollInterval)
    }, 3600000) // 1 hour
  }

  const handleConfirmAIGeneration = async () => {
    if (!researchPlan || !aiFormData.name.trim()) {
      setError("Plan name is required")
      return
    }

    setIsGeneratingAI(true)
    try {
      const request: GenerateAIResearchPlanRequest = {
        name: aiFormData.name,
        description: aiFormData.description,
        plan_type: aiFormData.plan_type,
        metadata: { generated_with_ai: true },
      }

      const response = await apiClient.generateAIResearchPlan(
        researchPlan.topic_id,
        request
      )
      setAiPlanData(response)
      setError(null)

      // Update the current plan with the AI-generated data
      setResearchPlan(response)
      setShowAIDialog(false)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Failed to generate AI research plan"
      )
      console.error("Error generating AI research plan:", err)
    } finally {
      setIsGeneratingAI(false)
    }
  }

  const handleCancelAIGeneration = () => {
    setShowAIDialog(false)
    setAiPlanData(null)
    setError(null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading research plan...</span>
        </div>
      </div>
    )
  }

  if (!researchPlan) {
    return (
      <div className="px-6 py-8 space-y-6 max-w-7xl mx-auto">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="h-4 w-4" />
              <span>Research plan not found</span>
            </div>
          </CardContent>
        </Card>
        <Button onClick={() => navigate(-1)} variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
      </div>
    )
  }

  return (
    <div className="px-6 pt-4 pb-8 space-y-6 max-w-4xl mx-auto">
      {/* Research Plan Information */}
      <div className="space-y-4">
        <div>
          {isEditing ? (
            <div className="space-y-6">
              <div>
                <Label htmlFor="edit-name" className="block text-center mb-3">
                  Research Plan Name
                </Label>
                <Input
                  id="edit-name"
                  value={editFormData.name}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, name: e.target.value })
                  }
                />
              </div>
              <div>
                <Label
                  htmlFor="edit-description"
                  className="block text-center mb-3"
                >
                  Description
                </Label>
                <Textarea
                  id="edit-description"
                  value={editFormData.description}
                  onChange={(e) =>
                    setEditFormData({
                      ...editFormData,
                      description: e.target.value,
                    })
                  }
                />
              </div>
            </div>
          ) : (
            <>
              <div className="text-center">
                <div className="text-xl font-semibold text-gray-900 mt-2">
                  Research Plan
                </div>
                <h1 className="text-3xl font-bold">{researchPlan.name}</h1>
              </div>
            </>
          )}
        </div>

        <div className="flex items-center justify-center space-x-4 text-sm text-muted-foreground">
          <div className="flex items-center">
            <Calendar className="h-4 w-4 mr-2" />
            Created {new Date(researchPlan.created_at).toLocaleDateString()}
          </div>
          <span
            className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
              researchPlan.status === "active"
                ? "bg-green-100 text-green-800"
                : researchPlan.status === "completed"
                ? "bg-blue-100 text-blue-800"
                : "bg-gray-100 text-gray-800"
            }`}
          >
            {researchPlan.status === "active"
              ? "In Progress"
              : researchPlan.status === "completed"
              ? "Complete"
              : researchPlan.status}
          </span>
          {researchPlan.plan_approved && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
              Approved
            </span>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Research Plan Content */}
      <Card>
        <CardContent>
          <div className="space-y-4">
            {isEditing ? (
              <div>
                <Label
                  htmlFor="plan-content"
                  className="block text-center mb-3"
                >
                  Plan Content
                </Label>
                <Textarea
                  id="plan-content"
                  className="min-h-[300px] font-mono text-sm"
                  placeholder="Enter your research plan content here..."
                  value={editFormData.plan_structure}
                  onChange={(e) =>
                    setEditFormData({
                      ...editFormData,
                      plan_structure: e.target.value,
                    })
                  }
                />
              </div>
            ) : (
              <div className="space-y-4">
                {researchPlan.plan_structure ? (
                  <PlanStructureDisplay
                    planStructure={researchPlan.plan_structure}
                  />
                ) : (
                  <div className="bg-gray-50 p-4 rounded-md text-center text-gray-500">
                    No research plan content available.
                  </div>
                )}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex justify-center items-center">
        <div className="flex space-x-6">
          {isEditing ? (
            <>
              <Button
                onClick={handleSaveEdit}
                disabled={isSaving}
                className="w-36 flex items-center justify-center"
              >
                {isSaving ? (
                  <Loader2 className="h-4 w-4 mr-0.5 animate-spin" />
                ) : (
                  <Save className="h-4 w-4 mr-0.5" />
                )}
                {isSaving ? "Saving..." : "Save"}
              </Button>
              <Button
                variant="outline"
                onClick={handleCancelEdit}
                disabled={isSaving}
                className="w-36 flex items-center justify-center"
              >
                <X className="h-4 w-4 mr-0.5" />
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button
                onClick={handleEdit}
                disabled={researchPlan.plan_approved}
                className="w-36 flex items-center justify-center"
              >
                <Edit className="h-4 w-4 mr-0.5" />
                Edit
              </Button>
              <Button
                variant="destructive"
                onClick={handleDelete}
                className="w-36 flex items-center justify-center"
              >
                <Trash2 className="h-4 w-4 mr-0.5" />
                Delete
              </Button>
              {!researchPlan.plan_approved && (
                <Button
                  onClick={handleApprove}
                  disabled={isApproving}
                  className="w-36 bg-green-600 hover:bg-green-700 flex items-center justify-center"
                >
                  {isApproving ? (
                    <Loader2 className="h-4 w-4 mr-0.5 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4 mr-0.5" />
                  )}
                  Approve
                </Button>
              )}
              {researchPlan.plan_approved && !researchExecuted && (
                <Button
                  onClick={() => setShowDepthDialog(true)}
                  disabled={isStartingResearch}
                  className="w-36 bg-blue-600 hover:bg-blue-700 flex items-center justify-center"
                >
                  {isStartingResearch ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4" />
                  )}
                  Start Research
                </Button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Status */}
      <Card>
        <CardHeader className="text-center">
          <CardTitle>Status</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold">
                {researchPlan.completed_tasks || 0} /{" "}
                {researchPlan.tasks_count || 0}
              </div>
              <div className="text-sm text-muted-foreground">Tasks</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {researchPlan.progress?.toFixed(0) || 0}%
              </div>
              <div className="text-sm text-muted-foreground">Progress</div>
            </div>
            <div className="text-center">
              <div
                className="text-2xl font-bold text-black hover:text-gray-700 cursor-pointer"
                onClick={() => setShowCostDialog(true)}
                title="Click to view cost breakdown"
              >
                {formatAUD(convertToAUD(researchPlan.estimated_cost || 0))}
              </div>
              <div className="text-sm text-muted-foreground">Estimated</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold">
                {formatAUD(convertToAUD(researchPlan.actual_cost || 0))}
              </div>
              <div className="text-sm text-muted-foreground">Actual</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Depth Selection Dialog */}
      <Dialog open={showDepthDialog} onOpenChange={setShowDepthDialog}>
        <DialogContent className="sm:max-w-[400px]">
          <DialogHeader>
            <DialogTitle>Research Depth Selection</DialogTitle>
            <DialogDescription>
              What depth of research would you like to perform?
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="depth-select">Select Research Depth</Label>
              <select
                id="depth-select"
                value={selectedDepth}
                onChange={(e) =>
                  setSelectedDepth(
                    e.target.value as "undergraduate" | "masters" | "phd"
                  )
                }
                className="w-full p-2 border border-input rounded-md bg-background"
              >
                <option value="undergraduate">Undergraduate</option>
                <option value="masters">Masters</option>
                <option value="phd">PhD</option>
              </select>
            </div>
          </div>

          <DialogFooter>
            <Button
              onClick={handleConfirmDepthAndStartResearch}
              disabled={isStartingResearch}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {isStartingResearch ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Starting Research...
                </>
              ) : (
                <>
                  <Check className="h-4 w-4" />
                  Start Research
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={() => setShowDepthDialog(false)}
              disabled={isStartingResearch}
            >
              Cancel
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* AI Generation Dialog */}
      <Dialog open={showAIDialog} onOpenChange={setShowAIDialog}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle className="flex items-center">
              <Sparkles className="h-5 w-5 mr-2 text-blue-500" />
              Generate AI Research Plan
            </DialogTitle>
            <DialogDescription>
              Use AI to generate a comprehensive research plan based on your
              topic and requirements.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label htmlFor="ai-plan-name">Plan Name</Label>
              <Input
                id="ai-plan-name"
                value={aiFormData.name}
                onChange={(e) =>
                  setAiFormData({ ...aiFormData, name: e.target.value })
                }
                placeholder="Enter a name for the researchplan"
              />
            </div>

            <div>
              <Label htmlFor="ai-plan-description">
                Description (Optional)
              </Label>
              <Textarea
                id="ai-plan-description"
                value={aiFormData.description}
                onChange={(e) =>
                  setAiFormData({ ...aiFormData, description: e.target.value })
                }
                placeholder="Provide additional context for the AI to consider"
                rows={3}
              />
            </div>

            <div>
              <Label htmlFor="ai-plan-type">Plan Type</Label>
              <select
                id="ai-plan-type"
                value={aiFormData.plan_type}
                onChange={(e) =>
                  setAiFormData({ ...aiFormData, plan_type: e.target.value })
                }
                className="w-full p-2 border border-input rounded-md bg-background"
              >
                <option value="comprehensive">Comprehensive</option>
                <option value="focused">Focused</option>
                <option value="exploratory">Exploratory</option>
              </select>
            </div>

            {aiPlanData && (
              <div className="bg-blue-50 p-4 rounded-md">
                {aiPlanData && aiPlanData.metadata?.cost_estimate && (
                  <div>
                    <div className="flex items-center mb-2">
                      <DollarSign className="h-4 w-4 mr-2 text-green-600" />
                      <span className="font-medium">Cost Estimate</span>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      Estimated cost: $
                      {aiPlanData.metadata.cost_estimate.estimated_cost.toFixed(
                        2
                      )}
                      (Complexity:{" "}
                      {aiPlanData.metadata.cost_estimate.complexity})
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleCancelAIGeneration}
              disabled={isGeneratingAI}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirmAIGeneration}
              disabled={isGeneratingAI || !aiFormData.name.trim()}
            >
              {isGeneratingAI ? (
                <>
                  <Loader2 className="h-4 w-4 mr-0.5 animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-0.5" />
                  Generate Plan
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Cost Breakdown Dialog */}
      <Dialog open={showCostDialog} onOpenChange={setShowCostDialog}>
        <DialogContent className="sm:max-w-[700px]">
          <DialogHeader className="text-center">
            <DialogTitle className="flex items-center justify-center">
              <DollarSign className="h-5 w-5 mr-2 text-green-600" />
              Cost Breakdown Analysis
            </DialogTitle>
            <DialogDescription className="text-center">
              Detailed breakdown of research plan costs in Australian dollars
            </DialogDescription>
          </DialogHeader>

          {(() => {
            const breakdown = getCostBreakdown()
            if (!breakdown) return <div>No cost data available</div>

            return (
              <div className="space-y-6">
                {/* Exchange Rate Info */}
                <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
                  <div className="text-sm text-blue-800 text-center">
                    <strong>Exchange Rate:</strong> 1 USD = {USD_TO_AUD_RATE}{" "}
                    AUD (approximate)
                  </div>
                </div>

                {/* Estimated Costs */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Estimated Costs
                  </h3>

                  <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                    <div className="flex justify-between items-center mb-3">
                      <h4 className="font-medium text-green-900">
                        Total Estimated Cost
                      </h4>
                      <div className="text-center">
                        <div className="text-lg font-bold text-green-800">
                          {formatAUD(breakdown.estimated.total_aud)}
                        </div>
                        <div className="text-sm text-green-600">
                          (${breakdown.estimated.total_usd.toFixed(2)} USD)
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* AI Operations Cost */}
                  <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                    <div className="flex justify-between items-center mb-2">
                      <h4 className="font-medium text-purple-900">
                        AI Operations
                      </h4>
                      <div className="text-center">
                        <div className="font-semibold text-purple-800">
                          {formatAUD(breakdown.estimated.ai_operations.aud)}
                        </div>
                        <div className="text-sm text-purple-600">
                          (${breakdown.estimated.ai_operations.usd.toFixed(2)}{" "}
                          USD)
                        </div>
                      </div>
                    </div>
                    <div className="text-sm text-purple-700">
                      Complexity Level:{" "}
                      <span className="font-medium">
                        {breakdown.estimated.ai_operations.complexity}
                      </span>
                    </div>
                  </div>

                  {/* Traditional Costs */}
                  <div className="space-y-3">
                    <h4 className="font-medium text-gray-900">
                      Traditional Research Costs
                    </h4>

                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="bg-yellow-50 p-3 rounded border border-yellow-200 text-center">
                        <div className="text-sm font-medium text-yellow-900">
                          Database Access
                        </div>
                        <div className="text-yellow-800 font-semibold">
                          {formatAUD(
                            breakdown.estimated.traditional_costs
                              .database_access.aud
                          )}
                        </div>
                        <div className="text-xs text-yellow-600">
                          ($
                          {breakdown.estimated.traditional_costs.database_access.usd.toFixed(
                            2
                          )}{" "}
                          USD)
                        </div>
                      </div>

                      <div className="bg-orange-50 p-3 rounded border border-orange-200 text-center">
                        <div className="text-sm font-medium text-orange-900">
                          Analysis Software
                        </div>
                        <div className="text-orange-800 font-semibold">
                          {formatAUD(
                            breakdown.estimated.traditional_costs
                              .analysis_software.aud
                          )}
                        </div>
                        <div className="text-xs text-orange-600">
                          ($
                          {breakdown.estimated.traditional_costs.analysis_software.usd.toFixed(
                            2
                          )}{" "}
                          USD)
                        </div>
                      </div>

                      <div className="bg-indigo-50 p-3 rounded border border-indigo-200 text-center">
                        <div className="text-sm font-medium text-indigo-900">
                          Expert Consultation
                        </div>
                        <div className="text-indigo-800 font-semibold">
                          {formatAUD(
                            breakdown.estimated.traditional_costs
                              .expert_consultation.aud
                          )}
                        </div>
                        <div className="text-xs text-indigo-600">
                          ($
                          {breakdown.estimated.traditional_costs.expert_consultation.usd.toFixed(
                            2
                          )}{" "}
                          USD)
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Actual Costs (if any) */}
                {breakdown.actual.total_usd > 0 && (
                  <div className="space-y-4">
                    <h3 className="text-lg font-semibold text-gray-900">
                      Actual Costs
                    </h3>

                    <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                      <div className="flex justify-between items-center mb-3">
                        <h4 className="font-medium text-red-900">
                          Total Actual Cost
                        </h4>
                        <div className="text-right">
                          <div className="text-lg font-bold text-red-800">
                            {formatAUD(breakdown.actual.total_aud)}
                          </div>
                          <div className="text-sm text-red-600">
                            (${breakdown.actual.total_usd.toFixed(2)} USD)
                          </div>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3 mt-3">
                        <div className="text-sm">
                          <span className="text-red-700">AI Operations:</span>
                          <span className="font-medium ml-1">
                            {formatAUD(breakdown.actual.ai_operations.aud)}
                          </span>
                        </div>
                        <div className="text-sm">
                          <span className="text-red-700">Other Costs:</span>
                          <span className="font-medium ml-1">
                            {formatAUD(breakdown.actual.other_costs.aud)}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Cost Optimization Suggestions */}
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Cost Optimization Suggestions
                  </h3>
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <ul className="space-y-2">
                      {breakdown.optimization_suggestions.map(
                        (suggestion: string, index: number) => (
                          <li key={index} className="flex items-start">
                            <span className="w-5 h-5 bg-gray-200 text-gray-700 rounded-full text-xs font-medium flex items-center justify-center mr-3 flex-shrink-0">
                              {index + 1}
                            </span>
                            <span className="text-sm text-gray-700">
                              {suggestion}
                            </span>
                          </li>
                        )
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            )
          })()}
        </DialogContent>
      </Dialog>

      {/* Back to Project Button - Centered in Container */}
      <div className="flex justify-center pt-4">
        <Button
          variant="outline"
          onClick={async () => {
            try {
              const topic = await apiClient.getTopicById(researchPlan.topic_id)
              navigate(getProjectDetailsPath(topic.project_id))
            } catch (error) {
              console.error("Failed to fetch topic:", error)
              // Fallback to projects list if topic fetch fails
              navigate(ROUTES.PROJECTS)
            }
          }}
        >
          <ArrowLeft className="h-4 w-4 mr-0.5" />
          Back to Project
        </Button>
      </div>
    </div>
  )
}
