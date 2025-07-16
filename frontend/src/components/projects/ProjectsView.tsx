import React, { useEffect, useState } from "react"
import { useSelector, useDispatch } from "react-redux"
import { RootState, AppDispatch } from "../../store/store"
import {
  setProjects,
  setLoading,
  setError,
} from "../../store/slices/projectsSlice"
import { apiService } from "../../services/api"
import { formatDistanceToNow } from "date-fns"
import {
  FolderIcon,
  PlusIcon,
  EllipsisVerticalIcon,
  ChatBubbleLeftIcon,
} from "@heroicons/react/24/outline"

const ProjectsView: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>()
  const { projects, isLoading, error } = useSelector(
    (state: RootState) => state.projects
  )
  const [showCreateModal, setShowCreateModal] = useState(false)

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    dispatch(setLoading(true))
    try {
      const projectsData = await apiService.getProjects()
      dispatch(setProjects(projectsData))
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load projects"
      dispatch(setError(errorMessage))
    }
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
              className="bg-white rounded-lg shadow hover:shadow-md transition-shadow duration-200 p-6"
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
                <button className="text-gray-400 hover:text-gray-600">
                  <EllipsisVerticalIcon className="h-5 w-5" />
                </button>
              </div>

              <p className="text-gray-600 mb-4 text-sm">
                {project.description}
              </p>

              <div className="flex items-center justify-between text-sm text-gray-500">
                <div className="flex items-center space-x-1">
                  <ChatBubbleLeftIcon className="h-4 w-4" />
                  <span>{project.conversation_count} conversations</span>
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

      {/* Create Project Modal placeholder */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Create New Project
            </h2>
            <p className="text-gray-600 mb-4">
              Project creation functionality coming soon...
            </p>
            <div className="flex justify-end">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ProjectsView
