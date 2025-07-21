import React from "react"
import { useDispatch } from "react-redux"
import { useNavigate, useLocation } from "react-router-dom"
import { toggleSidebar } from "../../store/slices/uiSlice"
import {
  XMarkIcon,
  FolderIcon,
  BeakerIcon,
  ClipboardDocumentListIcon,
  HeartIcon,
  BugAntIcon,
} from "@heroicons/react/24/outline"

const Sidebar: React.FC = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    { id: "projects", label: "Projects", icon: FolderIcon, path: "/projects" },
    { id: "research", label: "Research", icon: BeakerIcon, path: "/research" },
    {
      id: "tasks",
      label: "Tasks",
      icon: ClipboardDocumentListIcon,
      path: "/tasks",
    },
    { id: "debug", label: "Debug", icon: BugAntIcon, path: "/debug" },
    { id: "health", label: "Health", icon: HeartIcon, path: "/health" },
  ]

  const isActivePath = (path: string) => {
    return (
      location.pathname === path || location.pathname.startsWith(path + "/")
    )
  }

  return (
    <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">Eunice</h2>
        <button
          onClick={() => dispatch(toggleSidebar())}
          className="p-1 rounded-lg hover:bg-gray-100 transition-colors"
        >
          <XMarkIcon className="h-5 w-5 text-gray-500" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4">
        <ul className="space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon
            const isActive = isActivePath(item.path)

            return (
              <li key={item.id}>
                <button
                  onClick={() => navigate(item.path)}
                  className={`w-full flex items-center space-x-3 px-3 py-2 rounded-lg text-left transition-colors ${
                    isActive
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                >
                  <Icon className="h-5 w-5" />
                  <span className="font-medium">{item.label}</span>
                </button>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-gray-200">
        <div className="text-xs text-gray-500 text-center">
          Multi-Agent Research System
        </div>
      </div>
    </div>
  )
}

export default Sidebar
