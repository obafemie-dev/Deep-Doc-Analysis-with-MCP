import { useState, useEffect } from 'react'
import axios from 'axios'
import FileUpload from './components/FileUpload'
import ChatInterface from './components/ChatInterface'
import StatusBar from './components/StatusBar'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

function App() {
  const [uploadedFile, setUploadedFile] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    checkSystemStatus()
  }, [])

  const checkSystemStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/status`)
      setSystemStatus(response.data)
    } catch (error) {
      console.error('Error checking system status:', error)
      setSystemStatus({ error: 'Unable to connect to backend' })
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (file) => {
    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      })

      setUploadedFile(response.data)
      return response.data
    } catch (error) {
      console.error('Error uploading file:', error)
      throw error
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Deep Doc Analysis with MCP
          </h1>
          <p className="text-sm text-gray-600">
            Analyze Excel files using AI-powered tools
          </p>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Sidebar */}
          <div className="lg:col-span-1 space-y-6">
            <FileUpload onFileUpload={handleFileUpload} />
            <StatusBar status={systemStatus} onRefresh={checkSystemStatus} />
          </div>

          {/* Main Chat Area */}
          <div className="lg:col-span-2">
            <ChatInterface
              uploadedFile={uploadedFile}
              apiBaseUrl={API_BASE_URL}
            />
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
