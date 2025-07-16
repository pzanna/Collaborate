import React, { useEffect, useState } from "react"
import { useSelector, useDispatch } from "react-redux"
import { useNavigate } from "react-router-dom"
import { RootState, AppDispatch } from "../../store/store"
import {
  loadConversations,
  setCurrentConversation,
  removeConversation,
} from "../../store/slices/chatSlice"
import { setProjects } from "../../store/slices/projectsSlice"
import { apiService } from "../../services/api"
import { formatDistanceToNow } from "date-fns"
import {
  ChatBubbleLeftIcon,
  FolderIcon,
  PlusIcon,
  StarIcon,
  TrashIcon,
  EllipsisVerticalIcon,
} from "@heroicons/react/24/outline"
import { StarIcon as StarIconSolid } from "@heroicons/react/24/solid"
import NewConversationModal from "../modals/NewConversationModal"

const Sidebar: React.FC = () => {
  const dispatch = useDispatch<AppDispatch>()
  const navigate = useNavigate()
  const [isNewConversationModalOpen, setIsNewConversationModalOpen] =
    useState(false)
  const [deletingConversationId, setDeletingConversationId] = useState<
    string | null
  >(null)

  const { conversations, currentConversationId } = useSelector(
    (state: RootState) => state.chat
  )
  const { projects, selectedProjectId } = useSelector(
    (state: RootState) => state.projects
  )

  useEffect(() => {
    // Load initial data
    loadProjects()
    loadConversationsData()
  }, [])

  const loadProjects = async () => {
    try {
      const projects = await apiService.getProjects()
      dispatch(setProjects(projects))
    } catch (error) {
      console.error("Failed to load projects:", error)
    }
  }

  const loadConversationsData = async () => {
    try {
      await dispatch(loadConversations())
    } catch (error) {
      console.error("Failed to load conversations:", error)
    }
  }

  const handleConversationClick = (conversationId: string) => {
    dispatch(setCurrentConversation(conversationId))
    navigate(`/conversation/${conversationId}`)
  }

  const handleDeleteConversation = async (conversationId: string) => {
    if (
      !window.confirm(
        "Are you sure you want to delete this conversation? This action cannot be undone."
      )
    ) {
      return
    }

    setDeletingConversationId(conversationId)

    try {
      const response = await fetch(`/api/conversations/${conversationId}`, {
        method: "DELETE",
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || "Failed to delete conversation")
      }

      dispatch(removeConversation(conversationId))

      // If this was the current conversation, navigate away
      if (currentConversationId === conversationId) {
        navigate("/")
      }
    } catch (error) {
      console.error("Failed to delete conversation:", error)
      alert("Failed to delete conversation. Please try again.")
    } finally {
      setDeletingConversationId(null)
    }
  }

  const handleNewConversation = () => {
    setIsNewConversationModalOpen(true)
  }

  const handleConversationCreated = (conversationId: string) => {
    navigate(`/conversation/${conversationId}`)
  }

  const recentConversations = conversations.slice(0, 10)

  return (
    <div className="flex flex-col h-full">
      {/* Workspace header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">
          🤝 Collaborate AI
        </h2>
        <p className="text-sm text-gray-500">Multi-AI Chat Platform</p>
      </div>

      {/* Navigation sections */}
      <div className="flex-1 overflow-y-auto">
        {/* Quick Actions */}
        <div className="p-4 border-b border-gray-200">
          <button
            onClick={handleNewConversation}
            className="w-full bg-blue-500 hover:bg-blue-600 text-white px-3 py-2 rounded-md text-sm font-medium flex items-center justify-center space-x-2"
          >
            <PlusIcon className="h-4 w-4" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* Starred Conversations */}
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
            ⭐ Starred
          </h3>
          <div className="space-y-1">
            <div className="text-sm text-gray-400 italic">
              No starred conversations yet
            </div>
          </div>
        </div>

        {/* Recent Conversations */}
        <div className="p-4 border-b border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
            💬 Recent Chats
          </h3>
          <div className="space-y-1">
            {recentConversations.length > 0 ? (
              recentConversations.map((conversation) => (
                <div
                  key={conversation.id}
                  className={`group relative rounded-md hover:bg-gray-100 transition-colors ${
                    currentConversationId === conversation.id
                      ? "bg-blue-50 border border-blue-200"
                      : ""
                  }`}
                >
                  <button
                    onClick={() => handleConversationClick(conversation.id)}
                    className="w-full text-left p-2 pr-8"
                  >
                    <div className="flex items-center space-x-2">
                      <ChatBubbleLeftIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {conversation.title}
                        </p>
                        <p className="text-xs text-gray-500">
                          {conversation.message_count} messages •{" "}
                          {formatDistanceToNow(
                            new Date(conversation.updated_at),
                            {
                              addSuffix: true,
                            }
                          )}
                        </p>
                      </div>
                      {conversation.message_count > 0 && (
                        <div className="w-2 h-2 bg-blue-500 rounded-full flex-shrink-0" />
                      )}
                    </div>
                  </button>

                  {/* Delete button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteConversation(conversation.id)
                    }}
                    disabled={deletingConversationId === conversation.id}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-600 transition-all disabled:opacity-50"
                    title="Delete conversation"
                  >
                    {deletingConversationId === conversation.id ? (
                      <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-600 rounded-full animate-spin" />
                    ) : (
                      <TrashIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              ))
            ) : (
              <div className="text-sm text-gray-400 italic">
                No conversations yet
              </div>
            )}
          </div>
        </div>

        {/* Projects */}
        <div className="p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
              📁 Projects
            </h3>
            <button
              onClick={() => navigate("/projects")}
              className="text-xs text-blue-500 hover:text-blue-600"
            >
              View all
            </button>
          </div>
          <div className="space-y-1">
            {projects.slice(0, 5).map((project) => (
              <button
                key={project.id}
                onClick={() => {
                  // TODO: Filter conversations by project
                  console.log("Select project:", project.id)
                }}
                className="w-full text-left p-2 rounded-md hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <FolderIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {project.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {project.conversation_count} conversations
                    </p>
                  </div>
                </div>
              </button>
            ))}

            {projects.length === 0 && (
              <div className="text-sm text-gray-400 italic">
                No projects yet
              </div>
            )}
          </div>
        </div>

        {/* AI Status */}
        <div className="p-4 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-3">
            🤖 AI Providers
          </h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">OpenAI</span>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <span className="text-xs text-gray-500">online</span>
              </div>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-700">xAI</span>
              <div className="flex items-center space-x-1">
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <span className="text-xs text-gray-500">online</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* New Conversation Modal */}
      <NewConversationModal
        isOpen={isNewConversationModalOpen}
        onClose={() => setIsNewConversationModalOpen(false)}
        onConversationCreated={handleConversationCreated}
      />
    </div>
  )
}

export default Sidebar
