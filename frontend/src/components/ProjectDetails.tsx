import { useState, useEffect, useCallback } from "react"
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
  type Project,
  type Topic,
  type CreateTopicRequest,
  type UpdateTopicRequest,
  type ResearchPlan,
} from "@/utils/api"
import {
  ROUTES,
  getTopicDetailsPath,
  getResearchPlanDetailsPath,
} from "@/utils/routes"

export function ProjectDetails() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()

  const [project, setProject] = useState<Project | null>(null)
  const [topics, setTopics] = useState<Topic[]>([])
  const [topicPlans, setTopicPlans] = useState<Record<string, ResearchPlan[]>>(
    {}
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingTopic, setEditingTopic] = useState<Topic | null>(null)
  const [formData, setFormData] = useState<CreateTopicRequest>({
    name: "",
    description: "",
    project_id: id || "",
  })

  const loadProjectData = useCallback(async () => {
    if (!id) return

    try {
      setLoading(true)
      setError(null)

      // Load project and topics in parallel
      const [projectData, topicsData] = await Promise.all([
        apiClient.getProject(id),
        apiClient.getTopics(id),
      ])

      setProject(projectData)
      setTopics(topicsData)

      // Load research plans for each topic
      const plansPromises = topicsData.map(async (topic) => {
        try {
          const plans = await apiClient.getResearchPlans(topic.id)
          return { topicId: topic.id, plans }
        } catch (err) {
          console.warn(`Failed to load plans for topic ${topic.id}:`, err)
          return { topicId: topic.id, plans: [] }
        }
      })

      const plansResults = await Promise.all(plansPromises)
      const plansMap = plansResults.reduce((acc, { topicId, plans }) => {
        acc[topicId] = plans
        return acc
      }, {} as Record<string, ResearchPlan[]>)

      setTopicPlans(plansMap)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load project data"
      )
      console.error("Error loading project data:", err)
    } finally {
      setLoading(false)
    }
  }, [id])

  // Load project and topics on component mount
  useEffect(() => {
    if (!id) {
      navigate(ROUTES.PROJECTS)
      return
    }
    loadProjectData()
  }, [id, navigate, loadProjectData])

  const handleCreateTopic = async () => {
    try {
      if (!formData.name.trim()) {
        setError("Topic name is required")
        return
      }

      const newTopic = await apiClient.createTopic(formData)
      setTopics([...topics, newTopic])
      setFormData({ name: "", description: "", project_id: id || "" })
      setCreateDialogOpen(false)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create topic")
      console.error("Error creating topic:", err)
    }
  }

  const handleEditTopic = async () => {
    try {
      if (!editingTopic || !formData.name.trim() || !id) {
        setError("Topic name is required")
        return
      }

      const updateData: UpdateTopicRequest = {
        name: formData.name,
        description: formData.description,
      }

      const updatedTopic = await apiClient.updateTopic(
        id,
        editingTopic.id,
        updateData
      )
      setTopics(
        topics.map((t) => (t.id === updatedTopic.id ? updatedTopic : t))
      )
      setEditDialogOpen(false)
      setEditingTopic(null)
      setFormData({ name: "", description: "", project_id: id })
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update topic")
      console.error("Error updating topic:", err)
    }
  }

  const handleDeleteTopic = async (topic: Topic) => {
    if (!window.confirm(`Are you sure you want to delete "${topic.name}"?`)) {
      return
    }

    try {
      if (!id) return
      await apiClient.deleteTopic(id, topic.id)
      setTopics(topics.filter((t) => t.id !== topic.id))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete topic")
      console.error("Error deleting topic:", err)
    }
  }

  const openEditDialog = (topic: Topic) => {
    setEditingTopic(topic)
    setFormData({
      name: topic.name,
      description: topic.description || "",
      project_id: id || "",
    })
    setEditDialogOpen(true)
  }

  const resetForm = () => {
    setFormData({ name: "", description: "", project_id: id || "" })
    setError(null)
  }

  const getTopicButtonProps = (topic: Topic) => {
    const plans = topicPlans[topic.id] || []
    const hasPlans = plans.length > 0

    if (hasPlans) {
      // If there are multiple plans, link to the first one
      const firstPlan = plans[0]
      return {
        text: "View Plan",
        variant: "outline" as const,
        onClick: () => navigate(getResearchPlanDetailsPath(firstPlan.id)),
      }
    } else {
      return {
        text: "Start Research",
        variant: "default" as const,
        onClick: () => navigate(getTopicDetailsPath(topic.id)),
        className: "bg-green-600 hover:bg-green-700",
      }
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="flex items-center space-x-2">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading project details...</span>
        </div>
      </div>
    )
  }

  if (!project) {
    return (
      <div className="px-6 py-8 space-y-6 max-w-7xl mx-auto">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center space-x-2 text-red-700">
              <AlertCircle className="h-4 w-4" />
              <span>Project not found</span>
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
          <h1 className="text-3xl font-bold">{project.name}</h1>
          {project.description && (
            <p className="text-muted-foreground mt-2 text-lg">
              {project.description}
            </p>
          )}
        </div>

        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm}>
              <Plus className="h-4 w-4 mr-2" />
              New Topic
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Topic</DialogTitle>
              <DialogDescription>
                Create a new research topic for this project.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">Topic Name</Label>
                <Input
                  id="name"
                  placeholder="Enter topic name..."
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
                  placeholder="Describe this topic..."
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
                <Button onClick={handleCreateTopic}>Create Topic</Button>
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
      {/* Topics Grid */}
      {topics.length === 0 ? (
        <Card className="border-dashed border-2">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No topics yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Get started by creating your first research topic for this project
            </p>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Topic
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Accordion type="multiple" className="w-full space-y-4">
          {topics.map((topic) => (
            <AccordionItem key={topic.id} value={topic.id.toString()}>
              <AccordionTrigger>
                <div className="flex items-center justify-between w-full">
                  <span className="font-medium text-lg">{topic.name}</span>
                  <div className="flex space-x-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        openEditDialog(topic)
                      }}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation()
                        handleDeleteTopic(topic)
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <div className="space-y-3">
                  {topic.description && (
                    <div className="text-muted-foreground">
                      {topic.description}
                    </div>
                  )}
                  <div className="flex items-center text-sm text-muted-foreground">
                    <Calendar className="h-4 w-4 mr-2" />
                    Created {new Date(topic.created_at).toLocaleDateString()}
                  </div>
                  <div>
                    {(() => {
                      const buttonProps = getTopicButtonProps(topic)
                      return (
                        <Button
                          variant={buttonProps.variant}
                          size="sm"
                          onClick={buttonProps.onClick}
                          className={buttonProps.className}
                        >
                          {buttonProps.text}
                        </Button>
                      )
                    })()}
                  </div>
                </div>
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      )}

      {/* Edit Topic Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Topic</DialogTitle>
            <DialogDescription>
              Update your topic information.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-name">Topic Name</Label>
              <Input
                id="edit-name"
                placeholder="Enter topic name..."
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
                placeholder="Describe this topic..."
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
              <Button onClick={handleEditTopic}>Save Changes</Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
      {/* Back to Dashboard Button - Centered in Container */}
      <div className="flex justify-center pt-4">
        <Button variant="outline" onClick={() => navigate(ROUTES.PROJECTS)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Projects
        </Button>
      </div>
    </div>
  )
}
