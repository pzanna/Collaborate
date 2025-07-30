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
  FolderOpen
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
  type Project, 
  type Topic, 
  type CreateTopicRequest, 
  type UpdateTopicRequest 
} from "@/utils/api"
import { ROUTES } from "@/utils/routes"

export function ProjectDetails() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  
  const [project, setProject] = useState<Project | null>(null)
  const [topics, setTopics] = useState<Topic[]>([])
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

  // Load project and topics on component mount
  useEffect(() => {
    if (!id) {
      navigate(ROUTES.PROJECTS)
      return
    }
    loadProjectData()
  }, [id, navigate])

  const loadProjectData = async () => {
    if (!id) return
    
    try {
      setLoading(true)
      setError(null)
      
      // Load project and topics in parallel
      const [projectData, topicsData] = await Promise.all([
        apiClient.getProject(id),
        apiClient.getTopics(id)
      ])
      
      setProject(projectData)
      setTopics(topicsData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load project data")
      console.error("Error loading project data:", err)
    } finally {
      setLoading(false)
    }
  }

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

      const updatedTopic = await apiClient.updateTopic(id, editingTopic.id, updateData)
      setTopics(topics.map(t => t.id === updatedTopic.id ? updatedTopic : t))
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
      setTopics(topics.filter(t => t.id !== topic.id))
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
      {/* Header with Back Button */}
      <div className="flex items-center space-x-4">
        <Button 
          onClick={() => navigate(ROUTES.PROJECTS)} 
          variant="outline"
          size="sm"
        >
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Projects
        </Button>
      </div>

      {/* Project Information */}
      <div className="space-y-4">
        <div>
          <h1 className="text-3xl font-bold">{project.name}</h1>
          {project.description && (
            <p className="text-muted-foreground mt-2 text-lg">
              {project.description}
            </p>
          )}
        </div>
        
        <div className="flex items-center space-x-4 text-sm text-muted-foreground">
          <div className="flex items-center">
            <Calendar className="h-4 w-4 mr-2" />
            Created {new Date(project.created_at).toLocaleDateString()}
          </div>
          <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
            project.status === 'active' 
              ? 'bg-green-100 text-green-800' 
              : 'bg-gray-100 text-gray-800'
          }`}>
            {project.status}
          </span>
        </div>
      </div>

      {/* Topics Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Topics</h2>
            <p className="text-muted-foreground mt-1">
              Research topics within this project
            </p>
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
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  />
                </div>
                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    placeholder="Describe this topic..."
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
                  <Button onClick={handleCreateTopic}>
                    Create Topic
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {topics.map((topic) => (
              <Card key={topic.id} className="hover:shadow-md transition-shadow">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{topic.name}</CardTitle>
                    <div className="flex space-x-1">
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => openEditDialog(topic)}
                      >
                        <Edit className="h-4 w-4" />
                      </Button>
                      <Button 
                        variant="ghost" 
                        size="sm"
                        onClick={() => handleDeleteTopic(topic)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                  {topic.description && (
                    <CardDescription className="line-clamp-2">
                      {topic.description}
                    </CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="flex items-center text-sm text-muted-foreground">
                      <Calendar className="h-4 w-4 mr-2" />
                      Created {new Date(topic.created_at).toLocaleDateString()}
                    </div>
                    
                    {/* Plans and Tasks count */}
                    <div className="pt-2 border-t">
                      <div className="text-sm text-muted-foreground">
                        Plans: {topic.plans_count || 0} • Tasks: {topic.tasks_count || 0}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

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
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                placeholder="Describe this topic..."
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
              <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleEditTopic}>
                Save Changes
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}