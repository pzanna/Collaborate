import React, { useState, useEffect } from "react"
import { apiClient } from "@/utils/api"

interface ConnectionStatusProps {
  className?: string
}

const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  className = "",
}) => {
  const [status, setStatus] = useState<
    "checking" | "connected" | "disconnected"
  >("checking")
  const [lastCheck, setLastCheck] = useState<string>("")

  useEffect(() => {
    const checkConnection = async () => {
      try {
        await apiClient.healthCheck()
        setStatus("connected")
        setLastCheck(new Date().toLocaleTimeString())
      } catch (error) {
        console.error("Backend connection failed:", error)
        setStatus("disconnected")
        setLastCheck(new Date().toLocaleTimeString())
      }
    }

    // Initial check
    checkConnection()

    // Check every 30 seconds
    const interval = setInterval(checkConnection, 30000)

    return () => clearInterval(interval)
  }, [])

  const getStatusColor = () => {
    switch (status) {
      case "connected":
        return "text-green-600 bg-green-50"
      case "disconnected":
        return "text-red-600 bg-red-50"
      default:
        return "text-yellow-600 bg-yellow-50"
    }
  }

  const getStatusText = () => {
    switch (status) {
      case "connected":
        return "Backend Connected"
      case "disconnected":
        return "Backend Disconnected"
      default:
        return "Checking Connection..."
    }
  }

  return (
    <div
      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getStatusColor()} ${className}`}
    >
      <div
        className={`w-2 h-2 rounded-full mr-2 ${
          status === "connected"
            ? "bg-green-500"
            : status === "disconnected"
            ? "bg-red-500"
            : "bg-yellow-500"
        }`}
      />
      {getStatusText()}
      {lastCheck && <span className="ml-2 opacity-75">({lastCheck})</span>}
    </div>
  )
}

export default ConnectionStatus
