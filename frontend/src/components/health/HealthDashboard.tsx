import React, { useEffect, useState } from "react"
import { apiService } from "../../services/api"
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CpuChipIcon,
  ServerIcon,
} from "@heroicons/react/24/outline"

interface HealthData {
  status: string
  database: Record<string, any>
  ai_providers: Record<string, any>
  research_system: Record<string, any>
  mcp_server: Record<string, any>
  errors: Record<string, any>
}

interface SystemHealth {
  status: "healthy" | "warning" | "error" | "degraded"
  uptime: string
  lastUpdated: string
  services: {
    name: string
    status: "online" | "offline" | "degraded" | "disabled" | "error"
    responseTime?: number
    lastCheck: string
    details?: Record<string, any>
  }[]
}

const HealthDashboard: React.FC = () => {
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    status: "healthy",
    uptime: "Loading...",
    lastUpdated: new Date().toISOString(),
    services: [],
  })
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchHealthData = async () => {
    try {
      setError(null)
      const healthData: HealthData = await apiService.getHealth()

      // Convert backend health data to frontend format
      const services = [
        {
          name: "Database",
          status: (healthData.database.status === "healthy"
            ? "online"
            : healthData.database.status === "disabled"
            ? "disabled"
            : "error") as
            | "online"
            | "offline"
            | "degraded"
            | "disabled"
            | "error",
          lastCheck: new Date().toISOString(),
          details: healthData.database,
        },
        {
          name: "AI Providers",
          status: (healthData.ai_providers.status === "healthy"
            ? "online"
            : healthData.ai_providers.status === "disabled"
            ? "disabled"
            : "error") as
            | "online"
            | "offline"
            | "degraded"
            | "disabled"
            | "error",
          lastCheck: new Date().toISOString(),
          details: healthData.ai_providers,
        },
        {
          name: "Research System",
          status: (healthData.research_system.status === "healthy"
            ? "online"
            : healthData.research_system.status === "disabled"
            ? "disabled"
            : "error") as
            | "online"
            | "offline"
            | "degraded"
            | "disabled"
            | "error",
          lastCheck: new Date().toISOString(),
          details: healthData.research_system,
        },
        {
          name: "MCP Server",
          status: (healthData.mcp_server.status === "healthy"
            ? "online"
            : healthData.mcp_server.status === "offline"
            ? "offline"
            : healthData.mcp_server.status === "error"
            ? "error"
            : "disabled") as
            | "online"
            | "offline"
            | "degraded"
            | "disabled"
            | "error",
          lastCheck: new Date().toISOString(),
          details: healthData.mcp_server,
        },
      ]

      setSystemHealth({
        status: healthData.status as any,
        uptime: "System Running", // Backend doesn't provide uptime yet
        lastUpdated: new Date().toISOString(),
        services,
      })
      setIsLoading(false)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to fetch health data"
      )
      setIsLoading(false)
    }
  }

  useEffect(() => {
    // Initial fetch
    fetchHealthData()

    // Set up periodic refresh every 30 seconds
    const interval = setInterval(fetchHealthData, 30000)

    return () => clearInterval(interval)
  }, [])

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "online":
      case "healthy":
        return <CheckCircleIcon className="h-5 w-5 text-green-500" />
      case "degraded":
      case "warning":
        return <ExclamationTriangleIcon className="h-5 w-5 text-yellow-500" />
      case "offline":
      case "error":
        return <XCircleIcon className="h-5 w-5 text-red-500" />
      case "disabled":
        return <ClockIcon className="h-5 w-5 text-gray-400" />
      default:
        return <ClockIcon className="h-5 w-5 text-gray-500" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case "online":
      case "healthy":
        return "text-green-600 bg-green-50"
      case "degraded":
      case "warning":
        return "text-yellow-600 bg-yellow-50"
      case "offline":
      case "error":
        return "text-red-600 bg-red-50"
      case "disabled":
        return "text-gray-600 bg-gray-50"
      default:
        return "text-gray-600 bg-gray-50"
    }
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">System Health</h1>
        <div className="flex items-center space-x-2">
          <button
            onClick={fetchHealthData}
            disabled={isLoading}
            className="px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50"
          >
            {isLoading ? "Refreshing..." : "Refresh"}
          </button>
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <ClockIcon className="h-4 w-4" />
            <span>
              Last updated:{" "}
              {new Date(systemHealth.lastUpdated).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>

      {error && (
        <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
          <div className="flex">
            <XCircleIcon className="h-5 w-5 text-red-400" />
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">
                Error loading health data
              </h3>
              <div className="mt-2 text-sm text-red-700">
                <p>{error}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">System Status</p>
              <div className="flex items-center space-x-2 mt-1">
                {getStatusIcon(systemHealth.status)}
                <span
                  className={`text-lg font-semibold capitalize ${getStatusColor(
                    systemHealth.status
                  )}`}
                >
                  {systemHealth.status}
                </span>
              </div>
            </div>
            <CpuChipIcon className="h-12 w-12 text-gray-400" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">Uptime</p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">
                {systemHealth.uptime}
              </p>
            </div>
            <ClockIcon className="h-12 w-12 text-gray-400" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-600">
                Active Services
              </p>
              <p className="text-2xl font-semibold text-gray-900 mt-1">
                {
                  systemHealth.services.filter((s) => s.status === "online")
                    .length
                }{" "}
                / {systemHealth.services.length}
              </p>
            </div>
            <ServerIcon className="h-12 w-12 text-gray-400" />
          </div>
        </div>
      </div>

      {/* Services Status */}
      <div className="bg-white rounded-lg shadow">
        <div className="px-6 py-4 border-b border-gray-200">
          <h2 className="text-lg font-semibold text-gray-900">
            Services Status
          </h2>
        </div>
        {isLoading ? (
          <div className="px-6 py-8 text-center">
            <ClockIcon className="h-8 w-8 text-gray-400 mx-auto mb-2" />
            <p className="text-gray-500">Loading health data...</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-200">
            {systemHealth.services.map((service) => (
              <div key={service.name} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    {getStatusIcon(service.status)}
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {service.name}
                      </p>
                      <p className="text-xs text-gray-500">
                        Last checked:{" "}
                        {new Date(service.lastCheck).toLocaleTimeString()}
                      </p>
                      {/* Show MCP Server specific details */}
                      {service.name === "MCP Server" && service.details && (
                        <div className="mt-1 text-xs text-gray-600">
                          {service.details.connected && (
                            <div>
                              Connected to {service.details.host}:
                              {service.details.port}
                              {service.details.server_stats && (
                                <span className="ml-2">
                                  •{" "}
                                  {service.details.server_stats.active_tasks ||
                                    0}{" "}
                                  active tasks
                                </span>
                              )}
                            </div>
                          )}
                          {service.details.reason && (
                            <div className="text-gray-500">
                              {service.details.reason}
                            </div>
                          )}
                        </div>
                      )}
                      {/* Show AI Providers details */}
                      {service.name === "AI Providers" &&
                        service.details?.providers && (
                          <div className="mt-1 text-xs text-gray-600">
                            Available: {service.details.providers.join(", ")}
                          </div>
                        )}
                      {/* Show Research System details */}
                      {service.name === "Research System" &&
                        service.details && (
                          <div className="mt-1 text-xs text-gray-600">
                            {service.details.mcp_connected
                              ? "MCP Connected"
                              : "MCP Disconnected"}
                            {service.details.active_tasks !== undefined && (
                              <span className="ml-2">
                                • {service.details.active_tasks} active contexts
                              </span>
                            )}
                          </div>
                        )}
                    </div>
                  </div>
                  <div className="flex items-center space-x-4">
                    {service.responseTime && (
                      <div className="text-right">
                        <p className="text-sm font-medium text-gray-900">
                          {service.responseTime}ms
                        </p>
                        <p className="text-xs text-gray-500">Response time</p>
                      </div>
                    )}
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize ${getStatusColor(
                        service.status
                      )}`}
                    >
                      {service.status}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default HealthDashboard
