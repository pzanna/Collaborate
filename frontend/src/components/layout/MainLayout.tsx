import React, { ReactNode } from "react"
import { useSelector, useDispatch } from "react-redux"
import { RootState } from "../../store/store"
import { toggleSidebar } from "../../store/slices/uiSlice"
import Sidebar from "./Sidebar"
import Header from "./Header"

interface MainLayoutProps {
  children: ReactNode
}

const MainLayout: React.FC<MainLayoutProps> = ({ children }) => {
  const dispatch = useDispatch()
  const { sidebarOpen } = useSelector((state: RootState) => state.ui)

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <div
        className={`${
          sidebarOpen ? "w-80" : "w-16"
        } transition-all duration-300 ease-in-out bg-white border-r border-gray-200 flex flex-col`}
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

export default MainLayout
