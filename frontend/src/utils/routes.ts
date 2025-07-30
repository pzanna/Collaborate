/**
 * Application routes configuration
 */

export const ROUTES = {
  HOME: "/",
  WELCOME: "/welcome",
  AUTH: "/auth",
  LOGIN: "/login",
  REGISTER: "/register",
  TWO_FACTOR: "/2fa-setup",
  PROFILE: "/profile",
  SYSTEM_HEALTH: "/system-health",
  PROJECTS: "/projects",
  PROJECT_DETAILS: "/projects/:id",
  // Future routes can be added here
  // RESEARCH: '/research',
  // TASKS: '/tasks',
} as const

export type RouteKey = keyof typeof ROUTES
export type RoutePath = (typeof ROUTES)[RouteKey]

/**
 * Navigation helper functions
 */
export const getRoutePath = (routeKey: RouteKey): string => {
  return ROUTES[routeKey]
}

/**
 * Generate a project details path with a specific project ID
 */
export const getProjectDetailsPath = (projectId: string): string => {
  return `/projects/${projectId}`
}
