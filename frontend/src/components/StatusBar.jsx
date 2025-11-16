import { useState } from 'react'

function StatusBar({ status, onRefresh }) {
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = async () => {
    setRefreshing(true)
    await onRefresh()
    setRefreshing(false)
  }

  if (!status) {
    return null
  }

  const llmStatus = status.llm_status || {}
  const isHealthy = status.api_status === 'running' &&
                    (llmStatus.status === 'running' || llmStatus.status === 'configured')

  return (
    <div className="px-2">
      <div className="space-y-4">
        {/* API Status */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">API Server</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-900">
              {status.api_status === 'running' ? 'running' : 'offline'}
            </span>
            <span
              className={`h-2 w-2 rounded-full ${
                status.api_status === 'running' ? 'bg-green-500 animate-pulse' : 'bg-red-500'
              }`}
            />
          </div>
        </div>

        {/* LLM Service Status */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">LLM Service</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-900">
              {llmStatus.status || 'unknown'}
            </span>
            <span
              className={`h-2 w-2 rounded-full ${
                llmStatus.status === 'running' || llmStatus.status === 'configured'
                  ? 'bg-green-500 animate-pulse'
                  : 'bg-red-500'
              }`}
            />
          </div>
        </div>

        {/* Model Status */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Model</span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-900">
              {llmStatus.model || llmStatus.model_available ? 'active' : 'inactive'}
            </span>
            <span
              className={`h-2 w-2 rounded-full ${
                llmStatus.model || llmStatus.model_available ? 'bg-green-500 animate-pulse' : 'bg-yellow-500'
              }`}
            />
          </div>
        </div>

        {/* Capabilities */}
        <div className="flex items-center justify-between">
          <span className="text-sm text-gray-600">Capabilities</span>
          <span className="text-sm text-gray-900">
            {status.available_tools || 0} available
          </span>
        </div>
      </div>

      {/* Overall Health Indicator */}
      {!isHealthy && (
        <div className="mt-6 p-3 bg-red-50 rounded-md">
          <p className="text-sm text-red-800">
            System issues detected
          </p>
        </div>
      )}

      {/* Error Display */}
      {status.error && (
        <div className="mt-3 p-3 bg-red-50 rounded-md">
          <p className="text-sm text-red-800">{status.error}</p>
        </div>
      )}
    </div>
  )
}

export default StatusBar
