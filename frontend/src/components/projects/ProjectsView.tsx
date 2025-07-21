import React, { useEffect, useState, useCallback } from "react"
import { useSelector, useDispatch } from "react-redux"
import { useNavigate } from "react-router-dom"
import { RootState, AppDispatch } from "../../store/store"
import {
  setProjects,
  setLoading,
  setError,
  removeProject,
  addProject,
} from "../../store/slices/projectsSlice"
import { apiService } from "../../services/api"
import { hierarchicalAPI } from "../../services/hierarchicalAPI"
import { formatDistanceToNow } from "date-fns"
import { FolderIcon, PlusIcon, TrashIcon } from "@heroicons/react/24/outline"

const ProjectsView: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const { projects, isLoading, error } = useSelector(
    (state: RootState) => state.projects
  )
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(
    null
  )
  const [createFormData, setCreateFormData] = useState({
    name: "",
    description: "",
  })
  const [isCreating, setIsCreating] = useState(false)
  const [researchTopicsCounts, setResearchTopicsCounts] = useState<
    Record<string, number>
  >({})

  const loadProjects = useCallback(async () => {
    dispatch(setLoading(true))
    try {
      const projectsData = await apiService.getProjects()
      dispatch(setProjects(projectsData))

      // Load research topics counts for each project
      const topicsCounts: Record<string, number> = {}
      await Promise.all(
        projectsData.map(async (project) => {
          try {
            const topics = await hierarchicalAPI.getResearchTopics(project.id)
            topicsCounts[project.id] = topics.length
          } catch (error) {
            console.warn(
              `Failed to load topics for project ${project.id}:`,
              error
            )
            topicsCounts[project.id] = 0
          }
        })
      )
      setResearchTopicsCounts(topicsCounts)
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load projects"
      dispatch(setError(errorMessage))
    }
  }, [dispatch])

  useEffect(() => {
    loadProjects()
  }, [loadProjects])

  const handleProjectClick = (projectId: string) => {
    navigate(`/projects/${projectId}`)
  }

  const handleDeleteProject = async (
    projectId: string,
    projectName: string
  ) => {
    if (
      !window.confirm(
        `Are you sure you want to delete the project "${projectName}"? This will also delete all conversations and messages in this project. This action cannot be undone.`
      )
    ) {
      return
    }

    setDeletingProjectId(projectId)

    try {
      await apiService.deleteProject(projectId)
      dispatch(removeProject(projectId))
    } catch (error) {
      console.error("Failed to delete project:", error)
      const errorMessage =
        error instanceof Error ? error.message : "Failed to delete project"
      dispatch(setError(errorMessage))
    } finally {
      setDeletingProjectId(null)
    }
  }

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!createFormData.name.trim()) {
      return
    }

    setIsCreating(true)

    try {
      const newProject = await apiService.createProject(createFormData)
      dispatch(addProject(newProject))
      setShowCreateModal(false)
      setCreateFormData({ name: "", description: "" })
    } catch (error) {
      console.error("Failed to create project:", error)
      const errorMessage =
        error instanceof Error ? error.message : "Failed to create project"
      dispatch(setError(errorMessage))
    } finally {
      setIsCreating(false)
    }
  }

  const handleCloseCreateModal = () => {
    setShowCreateModal(false)
    setCreateFormData({ name: "", description: "" })
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Projects</h1>
        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium flex items-center space-x-2"
        >
          <PlusIcon className="h-4 w-4" />
          <span>New Project</span>
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}

      {projects.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <FolderIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            No Projects Yet
          </h3>
          <p className="text-gray-600 mb-4">
            Create your first project to organize your conversations
          </p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-md text-sm font-medium"
          >
            Create Project
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => (
            <div
              key={project.id}
              className="bg-white rounded-lg shadow hover:shadow-md transition-shadow duration-200 p-6 group relative cursor-pointer"
              onClick={() => handleProjectClick(project.id)}
            >
              <div className="flex justify-between items-start mb-4">
                <div className="flex items-center space-x-3">
                  <FolderIcon className="h-8 w-8 text-blue-500" />
                  <div>
                    <h3 className="text-lg font-semibold text-gray-900">
                      {project.name}
                    </h3>
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    handleDeleteProject(project.id, project.name)
                  }}
                  disabled={deletingProjectId === project.id}
                  className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-600 transition-all disabled:opacity-50"
                  title="Delete project"
                >
                  {deletingProjectId === project.id ? (
                    <div className="w-5 h-5 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
                  ) : (
                    <TrashIcon className="h-5 w-5" />
                  )}
                </button>
              </div>

              <p className="text-gray-600 mb-4 text-sm">
                {project.description}
              </p>

              <div className="flex items-center justify-between text-sm text-gray-500">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-1">
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 5H7a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"
                      />
                    </svg>
                    <span>
                      {researchTopicsCounts[project.id] || 0} Research Topics
                    </span>
                  </div>
                </div>
                <span>
                  {formatDistanceToNow(new Date(project.created_at), {
                    addSuffix: true,
                  })}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Create New Project
            </h2>
            <form onSubmit={handleCreateProject}>
              <div className="mb-4">
                <label
                  htmlFor="projectName"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Project Name *
                </label>
                <input
                  type="text"
                  id="projectName"
                  value={createFormData.name}
                  onChange={(e) =>
                    setCreateFormData({
                      ...createFormData,
                      name: e.target.value,
                    })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter project name"
                  required
                />
              </div>
              <div className="mb-6">
                <label
                  htmlFor="projectDescription"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Description
                </label>
                <textarea
                  id="projectDescription"
                  value={createFormData.description}
                  onChange={(e) =>
                    setCreateFormData({
                      ...createFormData,
                      description: e.target.value,
                    })
                  }
                  rows={3}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  placeholder="Enter project description (optional)"
                />
              </div>
              <div className="flex justify-end space-x-3">
                <button
                  type="button"
                  onClick={handleCloseCreateModal}
                  className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
                  disabled={isCreating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreating || !createFormData.name.trim()}
                  className="px-4 py-2 text-sm font-medium text-white bg-blue-500 hover:bg-blue-600 rounded-md disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {isCreating ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Creating...</span>
                    </>
                  ) : (
                    <span>Create Project</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProjectsView
