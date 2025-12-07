import { useState, useEffect } from 'react'
import axios from 'axios'
import ChatInterface from './components/ChatInterface'
import StatusBar from './components/StatusBar'
import { SpreadsheetPanel } from './components/SpreadsheetPanel'
import { useAuth } from './hooks/useAuth'
import { useAnalytics } from './hooks/useAnalytics'
import { SpreadsheetProvider, useSpreadsheet } from './contexts/SpreadsheetContext'
import { API_V1, API_ENDPOINTS } from '@/config/api'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarProvider,
} from '@/components/ui/sidebar'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { LogOut, PanelLeftClose, PanelLeft } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const API_BASE_URL = API_V1

function AppContent() {
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuth()
  const { sessionId, trackEvent } = useAnalytics()
  const { loadSheets, handleSheetUpdate, clearSpreadsheet } = useSpreadsheet()
  const [uploadedFile, setUploadedFile] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploadKey, setUploadKey] = useState(0)
  const [showSpreadsheet, setShowSpreadsheet] = useState(true)

  useEffect(() => {
    checkSystemStatus()
  }, [])

  const checkSystemStatus = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/status`, {
        withCredentials: true,
        headers: {
          'X-Session-ID': sessionId  // Include session ID for tracking
        }
      })
      setSystemStatus(response.data)
    } catch (error) {
      console.error('Error checking system status:', error)
      setSystemStatus({ error: 'Unable to connect to backend' })
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (file) => {
    const startTime = Date.now()

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post(`${API_BASE_URL}/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          'X-Session-ID': sessionId  // Include session ID for backend tracking
        }
      })

      setUploadedFile(response.data)

      // Load sheets for the spreadsheet viewer
      if (response.data.filename) {
        loadSheets(response.data.filename)
      }

      // Track successful file upload
      const processingTime = Date.now() - startTime
      await trackEvent('upload', {
        filename: file.name,
        file_size: file.size,
        file_type: file.type
      }, {
        processing_time_ms: processingTime
      })

      return response.data
    } catch (error) {
      console.error('Error uploading file:', error)

      // Track failed upload
      const processingTime = Date.now() - startTime
      await trackEvent('upload_error', {
        filename: file.name,
        file_size: file.size,
        error: error.message
      }, {
        processing_time_ms: processingTime
      })

      throw error
    }
  }

  const handleClearChat = () => {
    setUploadedFile(null)
    setUploadKey(prev => prev + 1)
    clearSpreadsheet()
  }

  const handleSheetUpdated = (updateInfo) => {
    handleSheetUpdate(updateInfo)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    )
  }

  const getUserInitials = () => {
    if (user?.full_name) {
      return user.full_name
        .split(' ')
        .map(n => n[0])
        .join('')
        .toUpperCase()
        .slice(0, 2)
    }
    if (user?.email) {
      return user.email[0].toUpperCase()
    }
    return 'U'
  }

  const handleLogout = async () => {
    try {
      // Call backend to revoke Stytch session
      await fetch(API_ENDPOINTS.LOGOUT, {
        method: 'POST',
        credentials: 'include', // Send session cookie
      })
    } catch (error) {
      console.error('Logout error:', error)
      // Continue with logout even if API call fails
    }

    // Clear any localStorage remnants (fallback cleanup)
    localStorage.removeItem('auth_token')

    // Redirect to login
    navigate('/login')
  }

  return (
    <SidebarProvider>
      <div className="min-h-screen flex w-full bg-white">
          {/* Sidebar */}
          <Sidebar>
            {/* Sidebar Header */}
            <SidebarHeader className="border-b border-gray-100 px-4 py-4">
              <div className="flex items-center gap-2">
                <img src="/alkanalyst.svg" alt="ALK analyst" className="h-6" />
                <span className="text-[10px] font-sans font-medium text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded whitespace-nowrap">
                  Early Preview
                </span>
              </div>
            </SidebarHeader>

            {/* Sidebar Content */}
            <SidebarContent>
              <SidebarGroup>
                <div className="flex items-center justify-between px-2 mb-3">
                  <SidebarGroupLabel className="mb-0 justify-start">System Status</SidebarGroupLabel>
                  <button
                    onClick={checkSystemStatus}
                    className="text-gray-400 hover:text-gray-600 transition-colors"
                  >
                    <svg
                      className="h-4 w-4"
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
                <SidebarGroupContent>
                  <StatusBar status={systemStatus} onRefresh={checkSystemStatus} />
                </SidebarGroupContent>
              </SidebarGroup>
            </SidebarContent>

            {/* Sidebar Footer */}
            <SidebarFooter className="border-t border-gray-100 p-4">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-3 w-full hover:bg-gray-50 rounded-lg p-2 transition-colors">
                    <Avatar className="h-8 w-8">
                      <AvatarFallback className="bg-gray-200 text-gray-700 text-sm">
                        {getUserInitials()}
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col items-start text-sm">
                      <span className="font-medium text-gray-900">
                        {user?.full_name || user?.email?.split('@')[0] || 'User'}
                      </span>
                      <span className="text-xs text-gray-500">
                        {user?.email || 'Loading...'}
                      </span>
                    </div>
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="w-48">
                  <DropdownMenuItem onClick={handleLogout} className="cursor-pointer">
                    <LogOut className="mr-2 h-4 w-4" />
                    <span>Logout</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </SidebarFooter>
          </Sidebar>

          {/* Main Content - Split View */}
          <main className="flex-1 flex overflow-hidden">
            {/* Chat Panel */}
            <div className={`flex flex-col transition-all duration-300 ${showSpreadsheet && uploadedFile ? 'w-1/2' : 'flex-1'}`}>
              {/* Toggle button header */}
              {uploadedFile && (
                <div className="flex items-center justify-end px-4 py-2 border-b border-gray-100">
                  <button
                    onClick={() => setShowSpreadsheet(!showSpreadsheet)}
                    className="flex items-center gap-2 px-3 py-1.5 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors"
                    title={showSpreadsheet ? 'Hide spreadsheet' : 'Show spreadsheet'}
                  >
                    {showSpreadsheet ? (
                      <>
                        <PanelLeftClose className="h-4 w-4" />
                        <span>Hide Spreadsheet</span>
                      </>
                    ) : (
                      <>
                        <PanelLeft className="h-4 w-4" />
                        <span>Show Spreadsheet</span>
                      </>
                    )}
                  </button>
                </div>
              )}
              <div className="flex-1 p-6 overflow-hidden">
                <ChatInterface
                  uploadedFile={uploadedFile}
                  apiBaseUrl={API_BASE_URL}
                  onClearChat={handleClearChat}
                  onFileUpload={handleFileUpload}
                  onSheetUpdated={handleSheetUpdated}
                />
              </div>
            </div>

            {/* Spreadsheet Panel */}
            {showSpreadsheet && uploadedFile && (
              <div className="w-1/2 border-l border-gray-200 p-4 overflow-hidden">
                <SpreadsheetPanel filename={uploadedFile?.filename} />
              </div>
            )}
          </main>
      </div>
    </SidebarProvider>
  )
}

function App() {
  return (
    <SpreadsheetProvider>
      <AppContent />
    </SpreadsheetProvider>
  )
}

export default App
