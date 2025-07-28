import React from "react"
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar"
import { AppSidebar } from "@/components/app-sidebar"

interface LayoutProps {
  children: React.ReactNode
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  return (
    <SidebarProvider>
      <AppSidebar />
      <main className="w-full min-h-screen bg-background">
        <div className="sticky top-0 z-10 bg-background border-b border-border p-2">
          <SidebarTrigger />
        </div>
        <div className="flex-1">{children}</div>
      </main>
    </SidebarProvider>
  )
}

export default Layout
