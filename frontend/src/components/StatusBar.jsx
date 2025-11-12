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
    <div className="bg-white rounded-lg shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">System Status</h2>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="text-gray-400 hover:text-gray-600 transition-colors"
        >
          <svg
            className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
            />
          </svg>
        </button>
      </div>

      <div className="space-y-3">
        {/* API Status */}
        <div className="flex items-center justify-between py-2 border-b border-gray-100">
          <span className="text-sm text-gray-600">API Server</span>
          <div className="flex items-center space-x-2">
            <span
              className={`h-2 w-2 rounded-full ${
                status.api_status === 'running' ? 'bg-green-500' : 'bg-red-500'
              }`}
            />
            <span className="text-sm font-medium text-gray-900">
              {status.api_status}
            </span>
          </div>
        </div>

        {/* LLM Service Status */}
        <div className="flex items-center justify-between py-2 border-b border-gray-100">
          <span className="text-sm text-gray-600">
            LLM Service {status.llm_provider && `(${status.llm_provider})`}
          </span>
          <div className="flex items-center space-x-2">
            <span
              className={`h-2 w-2 rounded-full ${
                llmStatus.status === 'running' || llmStatus.status === 'configured'
                  ? 'bg-green-500'
                  : 'bg-red-500'
              }`}
            />
            <span className="text-sm font-medium text-gray-900">
              {llmStatus.status || 'unknown'}
            </span>
          </div>
        </div>

        {/* Model Status */}
        <div className="flex items-center justify-between py-2 border-b border-gray-100">
          <span className="text-sm text-gray-600">Model</span>
          <div className="flex items-center space-x-2">
            <span
              className={`h-2 w-2 rounded-full ${
                llmStatus.model || llmStatus.model_available ? 'bg-green-500' : 'bg-yellow-500'
              }`}
            />
            <span className="text-xs font-medium text-gray-900 truncate max-w-[150px]">
              {llmStatus.model || 'N/A'}
            </span>
          </div>
        </div>

        {/* MCP Tools */}
        <div className="flex items-center justify-between py-2">
          <span className="text-sm text-gray-600">MCP Tools</span>
          <span className="text-sm font-medium text-gray-900">
            {status.available_tools || 0} available
          </span>
        </div>
      </div>

      {/* Overall Health Indicator */}
      <div className={`mt-4 p-3 rounded-lg ${isHealthy ? 'bg-green-50' : 'bg-red-50'}`}>
        <p className={`text-sm font-medium ${isHealthy ? 'text-green-800' : 'text-red-800'}`}>
          {isHealthy ? 'All systems operational' : 'System issues detected'}
        </p>
      </div>

      {/* Error Display */}
      {status.error && (
        <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-xs text-red-600">{status.error}</p>
        </div>
      )}
    </div>
  )
}

export default StatusBar
