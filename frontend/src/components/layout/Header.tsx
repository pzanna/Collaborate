import React from "react"
import { useSelector, useDispatch } from "react-redux"
import { useNavigate, useLocation } from "react-router-dom"
import { RootState } from "../../store/store"
import { toggleSidebar } from "../../store/slices/uiSlice"
import { Bars3Icon, ChevronRightIcon } from "@heroicons/react/24/outline"

interface BreadcrumbItem {
  label: string
  path: string
  isActive?: boolean
}

const Header: React.FC = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()

  const { sidebarOpen } = useSelector((state: RootState) => state.ui)

  // Generate breadcrumbs based on current route
  const generateBreadcrumbs = (): BreadcrumbItem[] => {
    const pathSegments = location.pathname.split("/").filter(Boolean)
    const breadcrumbs: BreadcrumbItem[] = []

    // Always start with Home
    breadcrumbs.push({
      label: "Home",
      path: "/",
      isActive: pathSegments.length === 0,
    })

    // Build hierarchical breadcrumbs based on the new structure
    if (pathSegments.length > 0) {
      switch (pathSegments[0]) {
        case "projects":
          breadcrumbs.push({
            label: "Projects",
            path: "/projects",
            isActive: pathSegments.length === 1,
          })

          if (pathSegments.length > 1) {
            const projectId = pathSegments[1]
            breadcrumbs.push({
              label: `Project ${projectId.slice(0, 8)}...`,
              path: `/projects/${projectId}`,
              isActive: pathSegments.length === 2,
            })

            if (pathSegments.length > 2 && pathSegments[2] === "topics") {
              breadcrumbs.push({
                label: "Topics",
                path: `/projects/${projectId}/topics`,
                isActive: pathSegments.length === 3,
              })
            }
          }
          break

        case "topics":
          if (pathSegments.length > 1) {
            const topicId = pathSegments[1]
            breadcrumbs.push({
              label: "Topics",
              path: "/topics",
              isActive: false,
            })
            breadcrumbs.push({
              label: `Topic ${topicId.slice(0, 8)}...`,
              path: `/topics/${topicId}`,
              isActive: pathSegments.length === 2,
            })

            if (pathSegments.length > 2 && pathSegments[2] === "plans") {
              breadcrumbs.push({
                label: "Plans",
                path: `/topics/${topicId}/plans`,
                isActive: pathSegments.length === 3,
              })
            }
          }
          break

        case "plans":
          if (pathSegments.length > 1) {
            const planId = pathSegments[1]
            breadcrumbs.push({
              label: "Plans",
              path: "/plans",
              isActive: false,
            })
            breadcrumbs.push({
              label: `Plan ${planId.slice(0, 8)}...`,
              path: `/plans/${planId}`,
              isActive: pathSegments.length === 2,
            })

            if (pathSegments.length > 2 && pathSegments[2] === "tasks") {
              breadcrumbs.push({
                label: "Tasks",
                path: `/plans/${planId}/tasks`,
                isActive: pathSegments.length === 3,
              })
            }
          }
          break

        case "tasks":
          if (pathSegments.length > 1) {
            const taskId = pathSegments[1]
            breadcrumbs.push({
              label: "Tasks",
              path: "/tasks",
              isActive: false,
            })
            breadcrumbs.push({
              label: `Task ${taskId.slice(0, 8)}...`,
              path: `/tasks/${taskId}`,
              isActive: pathSegments.length === 2,
            })
          }
          break

        case "research":
          breadcrumbs.push({
            label: "Research",
            path: "/research",
            isActive: pathSegments.length === 1,
          })
          break

        case "debug":
          breadcrumbs.push({
            label: "Debug",
            path: "/debug",
            isActive: pathSegments.length === 1,
          })
          break

        default:
          breadcrumbs.push({
            label:
              pathSegments[0].charAt(0).toUpperCase() +
              pathSegments[0].slice(1),
            path: `/${pathSegments[0]}`,
            isActive: pathSegments.length === 1,
          })
      }
    }

    return breadcrumbs
  }

  const breadcrumbs = generateBreadcrumbs()

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

        {/* Hierarchical Breadcrumbs */}
        <nav className="flex items-center space-x-2" aria-label="Breadcrumb">
          {breadcrumbs.map((breadcrumb, index) => (
            <div key={breadcrumb.path} className="flex items-center">
              {index > 0 && (
                <ChevronRightIcon className="h-4 w-4 text-gray-400 mx-2" />
              )}
              <button
                onClick={() => navigate(breadcrumb.path)}
                className={`text-sm font-medium transition-colors ${
                  breadcrumb.isActive
                    ? "text-blue-600"
                    : "text-gray-500 hover:text-gray-700"
                }`}
                aria-current={breadcrumb.isActive ? "page" : undefined}
              >
                {breadcrumb.label}
              </button>
            </div>
          ))}
        </nav>
      </div>

      <div className="flex items-center space-x-4">
        <div className="text-lg text-gray-500">Eunice Research System</div>
      </div>
    </div>
  )
}

export default Header
