import React from "react"

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Future: Add navigation bar here */}
      <main>{children}</main>
      {/* Future: Add footer here */}
    </div>
  )
}

export default Layout
