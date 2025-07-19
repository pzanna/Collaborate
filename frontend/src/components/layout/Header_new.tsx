import React from "react"
import { useSelector, useDispatch } from "react-redux"
import { useNavigate, useLocation } from "react-router-dom"
import { RootState } from "../../store/store"
import { toggleSidebar } from "../../store/slices/uiSlice"
import {
  Bars3Icon,
  BeakerIcon,
  FolderIcon,
  HeartIcon,
  ClipboardDocumentListIcon,
  BugAntIcon,
} from "@heroicons/react/24/outline"

const Header: React.FC = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()

  const { sidebarOpen } = useSelector((state: RootState) => state.ui)

  const getPageInfo = () => {
    const path = location.pathname
    if (path.startsWith("/projects")) {
      return { title: "Projects", icon: FolderIcon }
    } else if (path.startsWith("/research")) {
      return { title: "Research", icon: BeakerIcon }
    } else if (path.startsWith("/tasks")) {
      return { title: "Task Viewer", icon: ClipboardDocumentListIcon }
    } else if (path.startsWith("/debug")) {
      return { title: "Debug UI", icon: BugAntIcon }
    } else if (path.startsWith("/health")) {
      return { title: "Health", icon: HeartIcon }
    }
    return { title: "Collaborate", icon: FolderIcon }
  }

  const { title, icon: Icon } = getPageInfo()

  return (
    <div className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4">
      <div className="flex items-center space-x-4">
        {!sidebarOpen && (
          <button
            onClick={() => dispatch(toggleSidebar())}
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
          >
            <Bars3Icon className="h-6 w-6 text-gray-600" />
          </button>
        )}

        <div className="flex items-center space-x-3">
          <Icon className="h-6 w-6 text-gray-600" />
          <h1 className="text-xl font-semibold text-gray-800">{title}</h1>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="text-sm text-gray-500">Multi-Agent Research System</div>
      </div>
    </div>
  )
}

export default Header
