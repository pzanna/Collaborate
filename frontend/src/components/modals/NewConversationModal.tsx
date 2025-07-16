import React, { useState } from "react"
import { useSelector, useDispatch } from "react-redux"
import { RootState, AppDispatch } from "../../store/store"
import { createNewConversation } from "../../store/slices/chatSlice"
import { XMarkIcon } from "@heroicons/react/24/outline"

interface NewConversationModalProps {
  isOpen: boolean
  onClose: () => void
  onConversationCreated?: (conversationId: string) => void
}

const NewConversationModal: React.FC<NewConversationModalProps> = ({
  isOpen,
  onClose,
  onConversationCreated,
}) => {
  const dispatch = useDispatch<AppDispatch>()
  const { projects, selectedProjectId } = useSelector(
    (state: RootState) => state.projects
  )
  const [title, setTitle] = useState("")
  const [projectId, setProjectId] = useState(selectedProjectId || "")
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!title.trim()) {
      setError("Conversation title is required")
      return
    }

    if (!projectId) {
      setError("Please select a project")
      return
    }

    setIsCreating(true)
    setError(null)

    try {
      const result = await dispatch(
        createNewConversation({
          title: title.trim(),
          project_id: projectId,
        })
      )

      if (createNewConversation.fulfilled.match(result)) {
        // Reset form
        setTitle("")
        setError(null)

        // Call callback if provided
        if (onConversationCreated) {
          onConversationCreated(result.payload.id)
        }

        onClose()
      } else {
        throw new Error(
          result.error?.message || "Failed to create conversation"
        )
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create conversation"
      )
    } finally {
      setIsCreating(false)
    }
  }

  const handleClose = () => {
    if (!isCreating) {
      setTitle("")
      setError(null)
      onClose()
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="flex items-center justify-between p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            New Conversation
          </h2>
          <button
            onClick={handleClose}
            disabled={isCreating}
            className="text-gray-400 hover:text-gray-600 disabled:opacity-50"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6">
          {error && (
            <div className="mb-4 p-3 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}

          <div className="mb-4">
            <label
              htmlFor="title"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Conversation Title
            </label>
            <input
              type="text"
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              placeholder="Enter conversation title..."
              disabled={isCreating}
              autoFocus
            />
          </div>

          <div className="mb-6">
            <label
              htmlFor="project"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Project
            </label>
            <select
              id="project"
              value={projectId}
              onChange={(e) => setProjectId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              disabled={isCreating}
            >
              <option value="">Select a project...</option>
              {projects.map((project) => (
                <option key={project.id} value={project.id}>
                  {project.name}
                </option>
              ))}
            </select>
          </div>

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={handleClose}
              disabled={isCreating}
              className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 rounded-md disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isCreating || !title.trim() || !projectId}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-md disabled:opacity-50"
            >
              {isCreating ? "Creating..." : "Create Conversation"}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default NewConversationModal
