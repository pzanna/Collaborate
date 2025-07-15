import React, { ReactNode } from "react"
import { useSelector, useDispatch } from "react-redux"
import { RootState } from "../../store/store"
import { toggleSidebar, setCurrentView } from "../../store/slices/uiSlice"
import Sidebar from "./Sidebar"
import Header from "./Header"
import {
  Bars3Icon,
  ChatBubbleLeftIcon,
  FolderIcon,
  HeartIcon,
} from "@heroicons/react/24/outline"

interface ChatLayoutProps {
  children: ReactNode
}

const ChatLayout: React.FC<ChatLayoutProps> = ({ children }) => {
  const dispatch = useDispatch()
  const { sidebarOpen, currentView } = useSelector(
    (state: RootState) => state.ui
  )

  const navigationItems = [
    { id: "chat", label: "Chat", icon: ChatBubbleLeftIcon, path: "/" },
    { id: "projects", label: "Projects", icon: FolderIcon, path: "/projects" },
    { id: "health", label: "Health", icon: HeartIcon, path: "/health" },
  ]

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? "w-80" : "w-0"
        } transition-all duration-300 ease-in-out overflow-hidden bg-white border-r border-gray-200 flex flex-col`}
      >
        <Sidebar />
      </div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <Header />

        {/* Content */}
        <main className="flex-1 overflow-hidden">{children}</main>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 bg-black bg-opacity-50"
          onClick={() => dispatch(toggleSidebar())}
        />
      )}
    </div>
  )
}

export default ChatLayout
