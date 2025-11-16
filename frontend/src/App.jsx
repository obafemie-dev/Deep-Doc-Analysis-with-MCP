import { useState, useEffect } from 'react'
import axios from 'axios'
import ChatInterface from './components/ChatInterface'
import StatusBar from './components/StatusBar'
import { SessionProvider } from './contexts/SessionContext'
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

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

function App() {
  const navigate = useNavigate()
  const [uploadedFile, setUploadedFile] = useState(null)
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(true)
  const [uploadKey, setUploadKey] = useState(0)

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

  const handleClearChat = () => {
    setUploadedFile(null)
    setUploadKey(prev => prev + 1)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-xl text-gray-600">Loading...</div>
      </div>
    )
  }

  const handleLogout = () => {
    // Clear auth token
    localStorage.removeItem('auth_token')
    // Redirect to login
    navigate('/login')
  }

  return (
    <SessionProvider>
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
                        TA
                      </AvatarFallback>
                    </Avatar>
                    <div className="flex flex-col items-start text-sm">
                      <span className="font-medium text-gray-900">User</span>
                      <span className="text-xs text-gray-500">user@example.com</span>
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

          {/* Main Content */}
          <main className="flex-1 overflow-hidden">
            <div className="h-full p-6">
              <ChatInterface
                uploadedFile={uploadedFile}
                apiBaseUrl={API_BASE_URL}
                onClearChat={handleClearChat}
                onFileUpload={handleFileUpload}
              />
            </div>
          </main>
        </div>
      </SidebarProvider>
    </SessionProvider>
  )
}

export default App
