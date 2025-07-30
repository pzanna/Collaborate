import { useState, useEffect } from "react"
import { apiClient, type Project } from "@/utils/api"

export function useProjects() {
  const [projects, setProjects] = useState<Project[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadProjects = async () => {
    try {
      setLoading(true)
      setError(null)
      const projectData = await apiClient.getProjects()
      setProjects(projectData)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load projects")
      console.error("Error loading projects:", err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadProjects()
  }, [])

  return {
    projects,
    loading,
    error,
    refetch: loadProjects,
  }
}