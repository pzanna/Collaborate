import React, { useEffect, useState } from "react"
import { useSelector } from "react-redux"
import { RootState } from "../../store/store"
import {
  CheckCircleIcon,
  XCircleIcon,
  ExclamationTriangleIcon,
  ClockIcon,
  CpuChipIcon,
  CloudIcon,
} from "@heroicons/react/24/outline"

interface SystemHealth {
  status: "healthy" | "warning" | "error"
  uptime: string
  lastUpdated: string
  services: {
    name: string
    status: "online" | "offline" | "degraded"
    responseTime?: number
    lastCheck: string
  }[]
}

const HealthDashboard: React.FC = () => {
  const { connectionStatus } = useSelector((state: RootState) => state.chat)
  const [systemHealth, setSystemHealth] = useState<SystemHealth>({
    status: "healthy",
    uptime: "2h 34m",
    lastUpdated: new Date().toISOString(),
    services: [
      {
        name: "WebSocket Connection",
        status: connectionStatus === "connected" ? "online" : "offline",
        responseTime: 45,
        lastCheck: new Date().toISOString(),
      },
      {
        name: "OpenAI API",
        status: "online",
        responseTime: 120,
        lastCheck: new Date().toISOString(),
      },
      {
        name: "xAI API",
        status: "online",
        responseTime: 98,
        lastCheck: new Date().toISOString(),
      },
      {
        name: "Database",
        status: "online",
        responseTime: 12,
        lastCheck: new Date().toISOString(),
      },
    ],
  })

  useEffect(() => {
    const interval = setInterval(() => {
      setSystemHealth((prev) => ({
        ...prev,
        lastUpdated: new Date().toISOString(),
        services: prev.services.map((service) => ({
          ...service,
          status:
            service.name === "WebSocket Connection"
              ? connectionStatus === "connected"
                ? "online"
                : "offline"
              : service.status,
          lastCheck: new Date().toISOString(),
        })),
      }))
    }, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [connectionStatus])

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
      default:
        return "text-gray-600 bg-gray-50"
    }
  }

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-900">System Health</h1>
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <ClockIcon className="h-4 w-4" />
          <span>
            Last updated:{" "}
            {new Date(systemHealth.lastUpdated).toLocaleTimeString()}
          </span>
        </div>
      </div>

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
                Connection Status
              </p>
              <div className="flex items-center space-x-2 mt-1">
                {getStatusIcon(connectionStatus)}
                <span
                  className={`text-lg font-semibold capitalize ${getStatusColor(
                    connectionStatus
                  )}`}
                >
                  {connectionStatus}
                </span>
              </div>
            </div>
            <CloudIcon className="h-12 w-12 text-gray-400" />
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
      </div>
    </div>
  )
}

export default HealthDashboard
