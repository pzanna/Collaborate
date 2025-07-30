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
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  apiClient,
  type ResearchPlan,
  type UpdateResearchPlanRequest,
} from "@/utils/api"
import { ROUTES } from "@/utils/routes"

export function ResearchPlanDetails() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [researchPlan, setResearchPlan] = useState<ResearchPlan | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [isEditing, setIsEditing] = useState(false)
  const [isApproving, setIsApproving] = useState(false)
  const [editFormData, setEditFormData] = useState({
    name: "",
    description: "",
    plan_structure: "",
  })

  // Load research plan on component mount
  useEffect(() => {
    if (!id) {
      navigate(ROUTES.PROJECTS)
      return
    }
    loadResearchPlan()
  }, [id, navigate])

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

    // Convert the plan structure object to a formatted string
    let formatted = ""
    if (planStructure.sections && Array.isArray(planStructure.sections)) {
      formatted += planStructure.sections.join("\n") + "\n\n"
    }
    if (planStructure.details) {
      formatted += planStructure.details
    }

    return formatted
  }

  const parsePlanStructure = (structureText: string): Record<string, any> => {
    // Simple parsing - in a real app this might be more sophisticated
    const lines = structureText.split("\n")
    const sections = lines.filter((line) => line.trim().match(/^\d+\./))
    const details = lines
      .filter((line) => !line.trim().match(/^\d+\./) && line.trim())
      .join("\n")

    return {
      sections: sections.length > 0 ? sections : undefined,
      details: details || undefined,
    }
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

      const updateData: UpdateResearchPlanRequest = {
        name: editFormData.name,
        description: editFormData.description,
        plan_structure: parsePlanStructure(editFormData.plan_structure),
      }

      const updatedPlan = await apiClient.updateResearchPlan(id, updateData)
      setResearchPlan(updatedPlan)
      setIsEditing(false)
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update research plan"
      )
      console.error("Error updating research plan:", err)
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
    <div className="px-6 py-8 space-y-6 max-w-4xl mx-auto">
      {/* Research Plan Information */}
      <div className="space-y-4">
        <div>
          {isEditing ? (
            <div className="space-y-4">
              <div>
                <Label htmlFor="edit-name">Research Plan Name</Label>
                <Input
                  id="edit-name"
                  value={editFormData.name}
                  onChange={(e) =>
                    setEditFormData({ ...editFormData, name: e.target.value })
                  }
                />
              </div>
              <div>
                <Label htmlFor="edit-description">Description</Label>
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
              <h1 className="text-3xl font-bold">{researchPlan.name}</h1>
              {researchPlan.description && (
                <p className="text-muted-foreground mt-2 text-lg">
                  {researchPlan.description}
                </p>
              )}
            </>
          )}
        </div>

        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
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
            {researchPlan.status}
          </span>
          {researchPlan.plan_approved && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
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
        <CardHeader>
          <CardTitle>Research Plan</CardTitle>
          <CardDescription>
            {isEditing
              ? "Edit the research plan content below"
              : "Current research plan content"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {isEditing ? (
              <div>
                <Label htmlFor="plan-content">Plan Content</Label>
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
              <div className="bg-gray-50 p-4 rounded-md">
                <pre className="whitespace-pre-wrap text-sm">
                  {formatPlanStructure(researchPlan.plan_structure) ||
                    "No research plan content available."}
                </pre>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <div className="flex justify-between items-center">
        <div className="flex space-x-2">
          {isEditing ? (
            <>
              <Button onClick={handleSaveEdit}>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </Button>
              <Button variant="outline" onClick={handleCancelEdit}>
                <X className="h-4 w-4 mr-2" />
                Cancel
              </Button>
            </>
          ) : (
            <>
              <Button
                onClick={handleEdit}
                disabled={researchPlan.plan_approved}
              >
                <Edit className="h-4 w-4 mr-2" />
                Edit
              </Button>
              <Button variant="destructive" onClick={handleDelete}>
                <Trash2 className="h-4 w-4 mr-2" />
                Delete
              </Button>
            </>
          )}
        </div>

        {!isEditing && !researchPlan.plan_approved && (
          <Button
            onClick={handleApprove}
            disabled={isApproving}
            className="bg-green-600 hover:bg-green-700"
          >
            {isApproving ? (
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            ) : (
              <Check className="h-4 w-4 mr-2" />
            )}
            Approve
          </Button>
        )}
      </div>

      {/* Statistics */}
      <Card>
        <CardHeader>
          <CardTitle>Statistics</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <div className="text-2xl font-bold">
                {researchPlan.tasks_count || 0}
              </div>
              <div className="text-sm text-muted-foreground">Tasks</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {researchPlan.completed_tasks || 0}
              </div>
              <div className="text-sm text-muted-foreground">Completed</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                {researchPlan.progress?.toFixed(0) || 0}%
              </div>
              <div className="text-sm text-muted-foreground">Progress</div>
            </div>
            <div>
              <div className="text-2xl font-bold">
                ${researchPlan.actual_cost?.toFixed(0) || 0}
              </div>
              <div className="text-sm text-muted-foreground">Cost</div>
            </div>
          </div>
        </CardContent>
      </Card>
      {/* Back to Projects Button - Centered in Container */}
      <div className="flex justify-center pt-4">
        <Button
          variant="outline"
          onClick={() =>
            navigate(ROUTES.TOPIC_DETAILS.replace(":id", researchPlan.topic_id))
          }
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Topic
        </Button>
      </div>
    </div>
  )
}
