import * as React from "react"
import {
  BookOpen,
  Bot,
  FileText,
  Search,
  Settings2,
  SquareTerminal,
  Users,
  Database,
  Brain,
  Activity,
} from "lucide-react"
import { ROUTES } from "@/utils/routes"

import { NavMain } from "@/components/nav-main"
import { NavProjects } from "@/components/nav-projects"
import { NavUser } from "@/components/nav-user"
import { EuniceLogo } from "@/components/eunice-logo"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarRail,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar"
import { useAuth } from "@/hooks/useAuth"

// Eunice application data
const data = {
  user: {
    name: "Researcher",
    email: "researcher@eunice.ai",
    avatar: "/avatars/researcher.jpg",
  },
  navMain: [
    {
      title: "Dashboard",
      url: "/",
      icon: SquareTerminal,
      isActive: true,
      items: [
        {
          title: "Overview",
          url: "/dashboard",
        },
        {
          title: "Recent Projects",
          url: "/dashboard/recent",
        },
        {
          title: "Activity",
          url: "/dashboard/activity",
        },
      ],
    },
    {
      title: "Literature Search",
      url: "/literature",
      icon: Search,
      items: [
        {
          title: "Search Papers",
          url: "/literature/search",
        },
        {
          title: "Advanced Query",
          url: "/literature/advanced",
        },
        {
          title: "Screening",
          url: "/literature/screening",
        },
        {
          title: "PRISMA Flow",
          url: "/literature/prisma",
        },
      ],
    },
    {
      title: "AI Agents",
      url: "/agents",
      icon: Bot,
      items: [
        {
          title: "Planning Agent",
          url: "/agents/planning",
        },
        {
          title: "Literature Agent",
          url: "/agents/literature",
        },
        {
          title: "Analysis Agent",
          url: "/agents/analysis",
        },
        {
          title: "Writing Agent",
          url: "/agents/writing",
        },
      ],
    },
    {
      title: "Research Projects",
      url: "/projects",
      icon: FileText,
      items: [
        {
          title: "Active Projects",
          url: "/projects/active",
        },
        {
          title: "Templates",
          url: "/projects/templates",
        },
        {
          title: "Collaboration",
          url: "/projects/collaboration",
        },
        {
          title: "Export",
          url: "/projects/export",
        },
      ],
    },
    {
      title: "Documentation",
      url: "/docs",
      icon: BookOpen,
      items: [
        {
          title: "Getting Started",
          url: "/docs/getting-started",
        },
        {
          title: "API Reference",
          url: "/docs/api",
        },
        {
          title: "Tutorials",
          url: "/docs/tutorials",
        },
        {
          title: "Best Practices",
          url: "/docs/best-practices",
        },
      ],
    },
    {
      title: "Settings",
      url: "/settings",
      icon: Settings2,
      items: [
        {
          title: "General",
          url: "/settings/general",
        },
        {
          title: "AI Models",
          url: "/settings/ai-models",
        },
        {
          title: "Data Sources",
          url: "/settings/data-sources",
        },
        {
          title: "Integrations",
          url: "/settings/integrations",
        },
      ],
    },
  ],
  projects: [
    {
      name: "Neuroscience Meta-Analysis",
      url: "/projects/neuroscience-meta",
      icon: Brain,
    },
    {
      name: "Clinical Trial Review",
      url: "/projects/clinical-trials",
      icon: Users,
    },
    {
      name: "Database Integration",
      url: "/projects/database-integration",
      icon: Database,
    },
  ],
}

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const { user } = useAuth()

  // Transform auth user data to match NavUser component expectations
  const userData = user
    ? {
        name: `${user.first_name} ${user.last_name}`,
        email: user.email,
        avatar: user.profile_image_url
          ? `http://localhost:8013${user.profile_image_url}`
          : "/avatars/researcher.jpg", // Default avatar fallback
      }
    : data.user // Fallback to static data

  return (
    <Sidebar collapsible="icon" {...props}>
      <SidebarHeader>
        <EuniceLogo />
      </SidebarHeader>
      <SidebarContent>
        <NavMain items={data.navMain} />
        <NavProjects projects={data.projects} />
        {user?.role === "admin" && (
          <SidebarGroup className="group-data-[collapsible=icon]:hidden">
            <SidebarGroupLabel>System</SidebarGroupLabel>
            <SidebarMenu>
              <SidebarMenuItem>
                <SidebarMenuButton asChild>
                  <a href={ROUTES.SYSTEM_HEALTH}>
                    <Activity />
                    <span>System Health</span>
                  </a>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroup>
        )}
      </SidebarContent>
      <SidebarFooter>
        <NavUser user={userData} />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
