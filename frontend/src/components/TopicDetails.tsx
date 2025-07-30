import { useState, useEffect } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { 
  Plus, 
  Trash2, 
  ArrowLeft,
  Calendar,
  AlertCircle,
  Loader2,
  FolderOpen,
  FileText
} from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
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
  type CreateResearchPlanRequest 
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
        apiClient.getResearchPlans(id)
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
      setError(err instanceof Error ? err.message : "Failed to create research plan")
      console.error("Error creating research plan:", err)
    }
  }

  const handleDeleteResearchPlan = async (plan: ResearchPlan) => {
    if (!window.confirm(`Are you sure you want to delete "${plan.name}"?`)) {
      return
    }

    try {
      await apiClient.deleteResearchPlan(plan.id)
      setResearchPlans(researchPlans.filter(p => p.id !== plan.id))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete research plan")
      console.error("Error deleting research plan:", err)
    }
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
      {/* Header with Back Button */}
      <div className="flex items-center space-x-4">
        <Button 
          onClick={() => navigate(-1)} 
          variant="outline"
          size="sm"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back
        </Button>
      </div>

      {/* Topic Information */}
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold">{topic.name}</h1>
          {topic.description && (
            <p className="text-muted-foreground mt-2 text-lg">
              {topic.description}
            </p>
          )}
        </div>
        
        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
          <div className="flex items-center">
            <Calendar className="h-4 w-4 mr-2" />
            Created {new Date(topic.created_at).toLocaleDateString()}
          </div>
        </div>
      </div>

      {/* Research Plans Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Research Plans</h2>
            <p className="text-muted-foreground mt-1">
              Research plans within this topic
            </p>
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
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    placeholder="Describe this research plan..."
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  />
                </div>
                {error && (
                  <div className="text-sm text-red-600 flex items-center space-x-1">
                    <AlertCircle className="h-4 w-4" />
                    <span>{error}</span>
                  </div>
                )}
                <div className="flex justify-end space-x-2">
                  <Button variant="outline" onClick={() => setCreateDialogOpen(false)}>
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
        {error && !createDialogOpen && (
          <Card className="border-red-200 bg-red-50">
            <CardContent className="pt-6">
              <div className="flex items-center space-x-2 text-red-700">
                <AlertCircle className="h-4 w-4" />
                <span>{error}</span>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Research Plans Grid */}
        {researchPlans.length === 0 ? (
          <Card className="border-dashed border-2">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
              <h3 className="text-lg font-semibold mb-2">No research plans yet</h3>
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {researchPlans.map((plan) => (
              <Card 
                key={plan.id} 
                className="hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => navigate(getResearchPlanDetailsPath(plan.id))}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg flex items-center">
                      <FileText className="h-5 w-5 mr-2" />
                      {plan.name}
                    </CardTitle>
                    <div className="flex space-x-1">
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
                  {plan.description && (
                    <CardDescription className="line-clamp-2">
                      {plan.description}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4 mr-2" />
                      Created {new Date(plan.created_at).toLocaleDateString()}
                    </div>
                    
                    <div className="text-sm">
                      <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        plan.status === 'active' 
                          ? 'bg-green-100 text-green-800'
                          : plan.status === 'completed'
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
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
                      <div className="text-sm text-muted-foreground">
                        Tasks: {plan.tasks_count || 0} 
                        {plan.tasks_count && plan.completed_tasks ? ` (${plan.completed_tasks} completed)` : ''}
                      </div>
                      {plan.progress !== undefined && plan.progress > 0 && (
                        <div className="text-sm text-muted-foreground">
                          Progress: {plan.progress.toFixed(0)}%
                        </div>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}