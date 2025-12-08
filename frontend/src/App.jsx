import { useState, useEffect, useCallback, useRef } from 'react'
import axios from 'axios'
import ChatInterface from './components/ChatInterface'
import StatusBar from './components/StatusBar'
import { useAuth } from './hooks/useAuth'
import { useAnalytics } from './hooks/useAnalytics'
import { API_V1, API_ENDPOINTS } from '@/config/api'
import { useSpreadsheet } from './contexts/SpreadsheetContext'
import { SpreadsheetPanel } from './components/SpreadsheetPanel'
import { TopBar } from './components/TopBar'
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
import { LogOut } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

const API_BASE_URL = API_V1

function App() {
  const navigate = useNavigate()
  const { user, isAuthenticated } = useAuth()
  const { sessionId, trackEvent } = useAnalytics()
  const [uploadedFile, setUploadedFile] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploadKey, setUploadKey] = useState(0)

  // Resizable Sidebar State
  const [sidebarWidth, setSidebarWidth] = useState(450)
  const [isResizing, setIsResizing] = useState(false)
  const [mode, setMode] = useState('sheet') // 'chat' or 'sheet'

  const startResizing = useCallback((mouseDownEvent) => {
    mouseDownEvent.preventDefault();
    setIsResizing(true);
  }, []);

  const stopResizing = useCallback(() => {
    setIsResizing(false);
  }, []);

  const resize = useCallback(
    (mouseMoveEvent) => {
      if (isResizing) {
        const newWidth = mouseMoveEvent.clientX;
        if (newWidth > 300 && newWidth < window.innerWidth - 100) {
          setSidebarWidth(newWidth);
        }
      }
    },
    [isResizing]
  );

  const handleModeChange = (newMode) => {
    setMode(newMode)
  }

  useEffect(() => {
    window.addEventListener("mousemove", resize);
    window.addEventListener("mouseup", stopResizing);
    return () => {
      window.removeEventListener("mousemove", resize);
      window.removeEventListener("mouseup", stopResizing);
    };
  }, [resize, stopResizing]);

  // accessing the context
  const { loadSheets, clearSpreadsheet, handleSheetUpdate } = useSpreadsheet()

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
      // Load spreadsheet data
      loadSheets(response.data.filename)

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
    <div className="h-screen flex flex-col w-full bg-gray-50 overflow-hidden">
      {/* Top Bar */}
      <TopBar mode={mode} onModeChange={handleModeChange} />

      {/* Main Content - Split Layout */}
      <main className="flex-1 flex overflow-hidden p-4 gap-4">
        {/* Left Panel - Chat */}
        <div
          style={{ width: mode === 'sheet' ? sidebarWidth : '100%' }}
          className="flex flex-col h-full shrink-0 bg-white rounded-2xl shadow-lg border border-gray-100 z-[100] relative group transition-[width] duration-0 ease-linear overflow-hidden"
        >
          <div className="flex-1 overflow-hidden h-full">
            <ChatInterface
              uploadedFile={uploadedFile}
              apiBaseUrl={API_BASE_URL}
              onClearChat={handleClearChat}
              onFileUpload={handleFileUpload}
              onSheetUpdated={handleSheetUpdate}
            />
          </div>

          {/* Resize Handle */}
          {mode === 'sheet' && (
            <div
              className={`absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-400 transition-colors z-50 flex items-center justify-center ${isResizing ? 'bg-blue-600' : 'bg-transparent hover:bg-gray-300'}`}
              onMouseDown={startResizing}
            />
          )}
        </div>

        {/* Right Panel - Spreadsheet */}
        {mode === 'sheet' && (
          <div className="flex-1 h-full overflow-hidden bg-white rounded-2xl shadow-lg border border-gray-100">
            <SpreadsheetPanel />
          </div>
        )}
      </main>
    </div>
  )
}

export default App
