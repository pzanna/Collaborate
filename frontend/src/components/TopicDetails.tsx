import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import {
  Plus,
  Edit,
  Trash2,
  ArrowLeft,
  Calendar,
  AlertCircle,
  Loader2,
  FolderOpen,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent,
} from "@/components/ui/accordion"
import { Card, CardContent } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  apiClient,
  type Topic,
  type ResearchPlan,
  type CreateResearchPlanRequest,
  type UpdateResearchPlanRequest,
} from "@/utils/api"
import { ROUTES, getResearchPlanDetailsPath } from "@/utils/routes"

export function TopicDetails() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [topic, setTopic] = useState<Topic | null>(null)
  const [researchPlans, setResearchPlans] = useState<ResearchPlan[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingPlan, setEditingPlan] = useState<ResearchPlan | null>(null)
  const [formData, setFormData] = useState<CreateResearchPlanRequest>({
    name: "",
    description: "",
  })

  // Load topic and research plans on component mount
  useEffect(() => {
    if (!id) {
      navigate(ROUTES.PROJECTS)
      return
    }
    loadTopicData()
  }, [id, navigate])

  const loadTopicData = async () => {
    if (!id) return

    try {
      setLoading(true)
      setError(null)

      // Load topic and research plans in parallel
      const [topicData, plansData] = await Promise.all([
        apiClient.getTopicById(id),
        apiClient.getResearchPlans(id),
      ])

      setTopic(topicData)
      setResearchPlans(plansData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load topic data")
      console.error("Error loading topic data:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateResearchPlan = async () => {
    try {
      if (!formData.name.trim() || !id) {
        setError("Research plan name is required")
        return
      }

      const newPlan = await apiClient.createResearchPlan(id, formData)
      setResearchPlans([...researchPlans, newPlan])
      setFormData({ name: "", description: "" })
      setCreateDialogOpen(false)
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create research plan"
      )
      console.error("Error creating research plan:", err)
    }
  }

  const handleEditResearchPlan = async () => {
    try {
      if (!editingPlan || !formData.name.trim() || !id) {
        setError("Research plan name is required")
        return
      }

      const updateData: UpdateResearchPlanRequest = {
        name: formData.name,
        description: formData.description,
      }

      const updatedPlan = await apiClient.updateResearchPlan(
        editingPlan.id,
        updateData
      )
      setResearchPlans(
        researchPlans.map((p) => (p.id === updatedPlan.id ? updatedPlan : p))
      )
      setEditDialogOpen(false)
      setEditingPlan(null)
      setFormData({ name: "", description: "" })
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to update research plan"
      )
      console.error("Error updating research plan:", err)
    }
  }

  const handleDeleteResearchPlan = async (plan: ResearchPlan) => {
    if (!window.confirm(`Are you sure you want to delete "${plan.name}"?`)) {
      return
    }

    try {
      await apiClient.deleteResearchPlan(plan.id)
      setResearchPlans(researchPlans.filter((p) => p.id !== plan.id))
      setError(null)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to delete research plan"
      )
      console.error("Error deleting research plan:", err)
    }
  }

  const openEditDialog = (plan: ResearchPlan) => {
    setEditingPlan(plan)
    setFormData({
      name: plan.name,
      description: plan.description || "",
    })
    setEditDialogOpen(true)
  }

  const resetForm = () => {
    setFormData({ name: "", description: "" })
    setError(null)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading topic details...</span>
        </div>
      </div>
    )
  }

  if (!topic) {
    return (
      <div className="px-6 py-8 space-y-6 max-w-7xl mx-auto">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="h-4 w-4" />
              <span>Topic not found</span>
            </div>
          </CardContent>
        </Card>
        <Button onClick={() => navigate(ROUTES.PROJECTS)} variant="outline">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Projects
        </Button>
      </div>
    )
  }

  return (
    <div className="px-6 py-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">{topic.name}</h1>
          {topic.description && (
            <p className="text-muted-foreground mt-2 text-lg">
              {topic.description}
            </p>
          )}
        </div>

        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm}>
              <Plus className="h-4 w-4 mr-2" />
              New Research Plan
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Research Plan</DialogTitle>
              <DialogDescription>
                Create a new research plan for this topic.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">Research Plan Name</Label>
                <Input
                  id="name"
                  placeholder="Enter research plan name..."
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe this research plan..."
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                />
              </div>
              {error && (
                <div className="text-sm text-red-600 flex items-center space-x-1">
                  <AlertCircle className="h-4 w-4" />
                  <span>{error}</span>
                </div>
              )}
              <div className="flex justify-end space-x-2">
                <Button
                  variant="outline"
                  onClick={() => setCreateDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button onClick={handleCreateResearchPlan}>
                  Create Research Plan
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Error Display */}
      {error && !createDialogOpen && !editDialogOpen && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Research Plans Accordion */}
      {researchPlans.length === 0 ? (
        <Card className="border-dashed border-2">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">
              No research plans yet
            </h3>
            <p className="text-muted-foreground text-center mb-4">
              Get started by creating your first research plan for this topic
            </p>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Research Plan
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Accordion type="multiple" className="w-full space-y-4">
          {researchPlans.map((plan) => (
            <AccordionItem key={plan.id} value={plan.id.toString()}>
              <AccordionTrigger>
                <div className="flex items-center justify-between w-full">
                  <span className="font-medium text-lg">{plan.name}</span>
                  <div className="flex space-x-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        openEditDialog(plan)
                      }}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteResearchPlan(plan)
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-3">
                  {plan.description && (
                    <div className="text-muted-foreground">
                      {plan.description}
                    </div>
                  )}
                  <div className="flex items-center text-sm text-muted-foreground">
                    <Calendar className="h-4 w-4 mr-2" />
                    Created {new Date(plan.created_at).toLocaleDateString()}
                  </div>
                  <div className="text-sm">
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        plan.status === "active"
                          ? "bg-green-100 text-green-800"
                          : plan.status === "completed"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-gray-100 text-gray-800"
                      }`}
                    >
                      {plan.status}
                    </span>
                    {plan.plan_approved && (
                      <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 ml-2">
                        Approved
                      </span>
                    )}
                  </div>
                  {/* Tasks count */}
                  <div className="pt-2 border-t">
                    <div className="text-xs text-muted-foreground">
                      Tasks: {plan.tasks_count || 0}
                      {plan.tasks_count && plan.completed_tasks
                        ? ` (${plan.completed_tasks} completed)`
                        : ""}{" "}
                      • Progress:{" "}
                      {plan.progress !== undefined
                        ? plan.progress.toFixed(0)
                        : 0}
                      %
                    </div>
                  </div>
                  <div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() =>
                        navigate(getResearchPlanDetailsPath(plan.id))
                      }
                    >
                      View Research Plan
                    </Button>
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      )}

      {/* Edit Research Plan Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Research Plan</DialogTitle>
            <DialogDescription>
              Update your research plan information.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-name">Research Plan Name</Label>
              <Input
                id="edit-name"
                placeholder="Enter research plan name..."
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
              />
            </div>
            <div>
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                placeholder="Describe this research plan..."
                value={formData.description}
                onChange={(e) =>
                  setFormData({ ...formData, description: e.target.value })
                }
              />
            </div>
            {error && (
              <div className="text-sm text-red-600 flex items-center space-x-1">
                <AlertCircle className="h-4 w-4" />
                <span>{error}</span>
              </div>
            )}
            <div className="flex justify-end space-x-2">
              <Button
                variant="outline"
                onClick={() => setEditDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button onClick={handleEditResearchPlan}>Save Changes</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Back to Topics Button - Centered in Container */}
      <div className="flex justify-center pt-4">
        <Button
          variant="outline"
          onClick={() =>
            navigate(ROUTES.PROJECT_DETAILS.replace(":id", topic.project_id))
          }
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Topics
        </Button>
      </div>
    </div>
  )
}
