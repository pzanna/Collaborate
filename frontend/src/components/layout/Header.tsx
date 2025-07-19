import React, { useState } from "react"
import { useSelector, useDispatch } from "react-redux"
import { useNavigate, useLocation } from "react-router-dom"
import { RootState } from "../../store/store"
import { toggleSidebar } from "../../store/slices/uiSlice"
import { setCurrentConversation } from "../../store/slices/chatSlice"
import NewConversationModal from "../modals/NewConversationModal"
import {
  Bars3Icon,
  XMarkIcon,
  ChatBubbleLeftIcon,
  BeakerIcon,
  FolderIcon,
  HeartIcon,
  PlusIcon,
} from "@heroicons/react/24/outline"

const Header: React.FC = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()
  const { sidebarOpen } = useSelector((state: RootState) => state.ui)
  const { connectionStatus } = useSelector((state: RootState) => state.chat)
  const [showNewConversationModal, setShowNewConversationModal] =
    useState(false)

  const handleNewConversation = () => {
    setShowNewConversationModal(true)
  }

  const handleConversationCreated = (conversationId: string) => {
    dispatch(setCurrentConversation(conversationId))
    navigate(`/chat/${conversationId}`)
  }

  const getPageTitle = () => {
    if (location.pathname.startsWith("/chat")) {
      return "Chat Workspace"
    } else if (location.pathname.startsWith("/research")) {
      return "Research Workspace"
    } else if (location.pathname.startsWith("/projects")) {
      return "Projects"
    } else if (location.pathname.startsWith("/health")) {
      return "System Health"
    }
    return "Collaborate AI"
  }

  const getPageIcon = () => {
    if (location.pathname.startsWith("/chat")) {
      return ChatBubbleLeftIcon
    } else if (location.pathname.startsWith("/research")) {
      return BeakerIcon
    } else if (location.pathname.startsWith("/projects")) {
      return FolderIcon
    } else if (location.pathname.startsWith("/health")) {
      return HeartIcon
    }
    return ChatBubbleLeftIcon
  }

  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case "connected":
        return "bg-green-500"
      case "connecting":
        return "bg-yellow-500"
      case "error":
        return "bg-red-500"
      default:
        return "bg-gray-400"
    }
  }

  return (
    <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
      <div className="flex items-center space-x-4">
        {/* Sidebar toggle */}
        <button
          onClick={() => dispatch(toggleSidebar())}
          className="p-2 rounded-md text-gray-500 hover:text-gray-900 hover:bg-gray-100"
        >
          {sidebarOpen ? (
            <XMarkIcon className="h-5 w-5" />
          ) : (
            <Bars3Icon className="h-5 w-5" />
          )}
        </button>

        {/* Page title with icon */}
        <div className="flex items-center space-x-2">
          {React.createElement(getPageIcon(), {
            className: "h-6 w-6 text-blue-600",
          })}
          <h1 className="text-xl font-semibold text-gray-900">
            {getPageTitle()}
          </h1>
        </div>

        {/* Connection status */}
        <div className="flex items-center space-x-2">
          <div
            className={`w-2 h-2 rounded-full ${getConnectionStatusColor()}`}
          />
          <span className="text-sm text-gray-500 capitalize">
            {connectionStatus}
          </span>
        </div>
      </div>

      <div className="flex items-center space-x-3">
        {/* Quick actions */}
        <button
          onClick={() => navigate("/chat")}
          className={`p-2 rounded-md transition-colors ${
            location.pathname.startsWith("/chat")
              ? "text-blue-600 bg-blue-50"
              : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
          }`}
          title="Chat Workspace"
        >
          <ChatBubbleLeftIcon className="h-5 w-5" />
        </button>

        <button
          onClick={() => navigate("/research")}
          className={`p-2 rounded-md transition-colors ${
            location.pathname.startsWith("/research")
              ? "text-blue-600 bg-blue-50"
              : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
          }`}
          title="Research Workspace"
        >
          <BeakerIcon className="h-5 w-5" />
        </button>

        <button
          onClick={() => navigate("/projects")}
          className={`p-2 rounded-md transition-colors ${
            location.pathname.startsWith("/projects")
              ? "text-blue-600 bg-blue-50"
              : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
          }`}
          title="Projects"
        >
          <FolderIcon className="h-5 w-5" />
        </button>

        <button
          onClick={() => navigate("/health")}
          className={`p-2 rounded-md transition-colors ${
            location.pathname.startsWith("/health")
              ? "text-blue-600 bg-blue-50"
              : "text-gray-500 hover:text-gray-900 hover:bg-gray-100"
          }`}
          title="System Health"
        >
          <HeartIcon className="h-5 w-5" />
        </button>

        {/* New conversation button */}
        <button
          onClick={handleNewConversation}
          className="bg-blue-500 hover:bg-blue-600 text-white px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2 transition-colors"
          title="Create New Chat"
        >
          <PlusIcon className="h-4 w-4" />
          <span>New Chat</span>
        </button>
      </div>

      {/* New Conversation Modal */}
      <NewConversationModal
        isOpen={showNewConversationModal}
        onClose={() => setShowNewConversationModal(false)}
        onConversationCreated={handleConversationCreated}
      />
    </header>
  )
}

export default Header
