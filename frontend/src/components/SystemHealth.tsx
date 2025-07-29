import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import {
  ArrowLeft,
  Activity,
  Server,
  Database,
  Cpu,
  HardDrive,
  CheckCircle,
  XCircle,
  AlertCircle,
} from "lucide-react"
import { ROUTES } from "@/utils/routes"

interface ContainerStatus {
  name: string
  status: "running" | "stopped" | "error"
  uptime: string
  port?: string
  health: "healthy" | "unhealthy" | "starting"
}

interface SystemInfo {
  platform: string
  totalContainers: number
  runningContainers: number
  memory: {
    used: string
    total: string
  }
  disk: {
    used: string
    total: string
  }
}

export function SystemHealth() {
  const navigate = useNavigate()
  const API_BASE_URL = "http://localhost:8013"

  const [containers, setContainers] = useState<ContainerStatus[]>([])
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

  useEffect(() => {
    fetchSystemInfo()
    const interval = setInterval(() => {
      fetchSystemInfo()
    }, 10000) // Refresh every 10 seconds

    return () => clearInterval(interval)
  }, [])

  const getStoredToken = (key: string): string | null => {
    return localStorage.getItem(key)
  }

  const fetchSystemInfo = async () => {
    try {
      // Only show loading on initial load
      if (!systemInfo) {
        setLoading(true)
      }
      setError("")

      const accessToken = getStoredToken("access_token")
      if (!accessToken) {
        // Redirect to login if no token is available
        navigate("/login")
        return
      }

      // Call the real system health API endpoint
      const response = await fetch(`${API_BASE_URL}/system/health`, {
        method: "GET",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          "Content-Type": "application/json",
        },
      })

      if (!response.ok) {
        if (response.status === 401) {
          // Token expired or invalid - redirect to login
          navigate("/login")
          return
        } else if (response.status === 403) {
          throw new Error("Forbidden - Admin role required")
        } else {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
      }

      const data = await response.json()

      // Update system info to match our interface
      const realSystemInfo: SystemInfo = {
        platform: data.system_info?.platform || "Unknown",
        totalContainers: data.containers?.length || 0,
        runningContainers:
          data.containers?.filter((c: any) => c.status === "running").length ||
          0,
        memory: {
          used: data.system_info?.memory?.used || "0%",
          total: data.system_info?.memory?.total || "100%",
        },
        disk: {
          used: data.system_info?.disk?.used || "0%",
          total: data.system_info?.disk?.total || "100%",
        },
      }

      setSystemInfo(realSystemInfo)
      setContainers(data.containers || [])
      setLastUpdated(new Date())
    } catch (err) {
      console.error("Error fetching system info:", err)
      setError(
        err instanceof Error ? err.message : "Failed to fetch system data"
      )
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "running":
        return <CheckCircle className="h-4 w-4 text-green-600" />
      case "stopped":
        return <XCircle className="h-4 w-4 text-red-600" />
      case "error":
        return <AlertCircle className="h-4 w-4 text-red-600" />
      default:
        return <AlertCircle className="h-4 w-4 text-yellow-600" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "running":
        return (
          <Badge variant="default" className="bg-green-600">
            Running
          </Badge>
        )
      case "stopped":
        return <Badge variant="destructive">Stopped</Badge>
      case "error":
        return <Badge variant="destructive">Error</Badge>
      default:
        return <Badge variant="secondary">Unknown</Badge>
    }
  }

  const getHealthBadge = (health: string) => {
    switch (health) {
      case "healthy":
        return (
          <Badge variant="default" className="bg-green-600">
            Healthy
          </Badge>
        )
      case "unhealthy":
        return <Badge variant="destructive">Unhealthy</Badge>
      case "starting":
        return <Badge variant="secondary">Starting</Badge>
      default:
        return <Badge variant="outline">Unknown</Badge>
    }
  }

  return (
    <div className="px-20 pt-8 space-y-6">
      <div className="text-center space-y-2">
        <h1 className="text-2xl font-bold">System Health</h1>
        <p className="text-muted-foreground">
          Monitor system status and container health
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4" />
            <span>{error}</span>
          </div>
        </div>
      )}

      {systemInfo && (
        <>
          {/* System Overview */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="text-center p-0">
                <CardTitle className="text-sm font-medium flex items-center justify-center gap-2">
                  <Server className="h-4 w-4 text-muted-foreground" />
                  Platform
                </CardTitle>
              </CardHeader>
              <CardContent className="text-center p-0">
                <div className="text-2xl font-bold">{systemInfo.platform}</div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="text-center p-0">
                <CardTitle className="text-sm font-medium flex items-center justify-center gap-2">
                  <Database className="h-4 w-4 text-muted-foreground" />
                  Total Containers
                </CardTitle>
              </CardHeader>
              <CardContent className="text-center p-0">
                <div className="text-2xl font-bold">
                  {systemInfo.totalContainers}
                </div>
                <p className="text-xs text-muted-foreground">
                  {systemInfo.runningContainers} running
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="text-center p-0">
                <CardTitle className="text-sm font-medium flex items-center justify-center gap-2">
                  <Cpu className="h-4 w-4 text-muted-foreground" />
                  Memory Usage
                </CardTitle>
              </CardHeader>
              <CardContent className="text-center p-0">
                <div className="text-2xl font-bold">
                  {systemInfo.memory.used}
                </div>
                <p className="text-xs text-muted-foreground">
                  of {systemInfo.memory.total}
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="text-center p-0">
                <CardTitle className="text-sm font-medium flex items-center justify-center gap-2">
                  <HardDrive className="h-4 w-4 text-muted-foreground" />
                  Disk Usage
                </CardTitle>
              </CardHeader>
              <CardContent className="text-center p-0">
                <div className="text-2xl font-bold">{systemInfo.disk.used}</div>
                <p className="text-xs text-muted-foreground">
                  of {systemInfo.disk.total}
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Container Status */}
          <Card>
            <CardHeader className="text-center text-xl">
              <CardTitle>Container Status</CardTitle>
              <CardDescription>
                Current status of all system containers
                {lastUpdated && (
                  <span className="block mt-1 text-xs">
                    Last updated: {lastUpdated.toLocaleTimeString()}
                  </span>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {containers.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  No container data available
                </div>
              ) : (
                <div className="space-y-4">
                  {containers.map((container) => (
                    <div
                      key={container.name}
                      className="flex items-center justify-between p-3 border rounded-lg"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="flex items-center space-x-2">
                          {getStatusIcon(container.status)}
                          <span className="font-medium">{container.name}</span>
                        </div>
                        {container.port && (
                          <Badge variant="outline">:{container.port}</Badge>
                        )}
                      </div>

                      <div className="flex items-center space-x-4">
                        {container.uptime && (
                          <span className="text-sm text-muted-foreground">
                            {container.uptime}
                          </span>
                        )}
                        <div className="flex items-center space-x-2">
                          {getStatusBadge(container.status)}
                          {container.health && getHealthBadge(container.health)}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {loading && !systemInfo && (
        <div className="text-center py-8">
          <div className="inline-flex items-center space-x-2">
            <Activity className="h-4 w-4 animate-spin" />
            <span>Loading system information...</span>
          </div>
        </div>
      )}

      {/* Back to Dashboard button at bottom */}
      <div className="flex justify-center pt-2 pb-8">
        <Button variant="outline" onClick={() => navigate(ROUTES.WELCOME)}>
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Dashboard
        </Button>
      </div>
    </div>
  )
}
