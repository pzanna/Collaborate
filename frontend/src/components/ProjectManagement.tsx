import { useState, useEffect } from "react"
import { 
  Plus, 
  Edit, 
  Trash2, 
  FolderOpen,
  Calendar,
  AlertCircle,
  Loader2
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
  type CreateProjectRequest, 
  type UpdateProjectRequest 
} from "@/utils/api"

export function ProjectManagement() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [editingProject, setEditingProject] = useState<Project | null>(null)
  const [formData, setFormData] = useState<CreateProjectRequest>({
    name: "",
    description: "",
  })

  // Load projects on component mount
  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      setLoading(true)
      setError(null)
      const projectData = await apiClient.getProjects()
      setProjects(projectData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects")
      console.error("Error loading projects:", err)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateProject = async () => {
    try {
      if (!formData.name.trim()) {
        setError("Project name is required")
        return
      }

      const newProject = await apiClient.createProject(formData)
      setProjects([...projects, newProject])
      setFormData({ name: "", description: "" })
      setCreateDialogOpen(false)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create project")
      console.error("Error creating project:", err)
    }
  }

  const handleEditProject = async () => {
    try {
      if (!editingProject || !formData.name.trim()) {
        setError("Project name is required")
        return
      }

      const updateData: UpdateProjectRequest = {
        name: formData.name,
        description: formData.description,
      }

      const updatedProject = await apiClient.updateProject(editingProject.id, updateData)
      setProjects(projects.map(p => p.id === updatedProject.id ? updatedProject : p))
      setEditDialogOpen(false)
      setEditingProject(null)
      setFormData({ name: "", description: "" })
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update project")
      console.error("Error updating project:", err)
    }
  }

  const handleDeleteProject = async (project: Project) => {
    if (!window.confirm(`Are you sure you want to delete "${project.name}"?`)) {
      return
    }

    try {
      await apiClient.deleteProject(project.id)
      setProjects(projects.filter(p => p.id !== project.id))
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete project")
      console.error("Error deleting project:", err)
    }
  }

  const openEditDialog = (project: Project) => {
    setEditingProject(project)
    setFormData({
      name: project.name,
      description: project.description || "",
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
          <span>Loading projects...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="px-6 py-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Project Management</h1>
          <p className="text-muted-foreground mt-1">
            Manage your research projects, plans, and tasks
          </p>
        </div>
        
        <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={resetForm}>
              <Plus className="h-4 w-4 mr-2" />
              New Project
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Project</DialogTitle>
              <DialogDescription>
                Create a new research project to organize your work.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label htmlFor="name">Project Name</Label>
                <Input
                  id="name"
                  placeholder="Enter project name..."
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Describe your project..."
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
                <Button onClick={handleCreateProject}>
                  Create Project
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

      {/* Projects Grid */}
      {projects.length === 0 ? (
        <Card className="border-dashed border-2">
          <CardContent className="flex flex-col items-center justify-center py-12">
            <FolderOpen className="h-12 w-12 text-muted-foreground mb-4" />
            <h3 className="text-lg font-semibold mb-2">No projects yet</h3>
            <p className="text-muted-foreground text-center mb-4">
              Get started by creating your first research project
            </p>
            <Button onClick={() => setCreateDialogOpen(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Create Project
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <Card key={project.id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-lg">{project.name}</CardTitle>
                  <div className="flex space-x-1">
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => openEditDialog(project)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => handleDeleteProject(project)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                {project.description && (
                  <CardDescription className="line-clamp-2">
                    {project.description}
                  </CardDescription>
                )}
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div className="flex items-center text-sm text-muted-foreground">
                    <Calendar className="h-4 w-4 mr-2" />
                    Created {new Date(project.created_at).toLocaleDateString()}
                  </div>
                  
                  <div className="text-sm">
                    <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                      project.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {project.status}
                    </span>
                  </div>

                  {/* Placeholder for plans and tasks - will be implemented later */}
                  <div className="pt-2 border-t">
                    <div className="text-xs text-muted-foreground">
                      Plans: 0 • Tasks: 0
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Edit Project Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Project</DialogTitle>
            <DialogDescription>
              Update your project information.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="edit-name">Project Name</Label>
              <Input
                id="edit-name"
                placeholder="Enter project name..."
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="edit-description">Description</Label>
              <Textarea
                id="edit-description"
                placeholder="Describe your project..."
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
              <Button onClick={handleEditProject}>
                Save Changes
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}