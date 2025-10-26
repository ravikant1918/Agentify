import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { 
  Menu,
  Sun,
  Moon,
  Plus,
  Settings,
  User,
  LogOut,
  ChevronDown
} from 'lucide-react'
import { useUIStore } from '../store/ui'
import { useMCPStore } from '../store/mcp'
import { useChatStore } from '../store/chat'
import { useAuth } from '../contexts/AuthContext'
import { cn } from '../utils'

export const Navbar: React.FC = () => {
  const location = useLocation()
  const { darkMode, sidebarOpen, toggleDarkMode, toggleSidebar } = useUIStore()
  const { connectionStatus, checkStatus } = useMCPStore()
  const { clearCurrentThread } = useChatStore()
  const { user, logout } = useAuth()
  const [userMenuOpen, setUserMenuOpen] = React.useState(false)

  React.useEffect(() => {
    checkStatus()
    const interval = setInterval(checkStatus, 30000)
    return () => clearInterval(interval)
  }, [checkStatus])

  const handleNewChat = () => {
    clearCurrentThread()
    if (location.pathname !== '/') {
      // Will be handled by router
    }
  }

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'connected': return 'bg-green-500'
      case 'disconnected': return 'bg-red-500'
      case 'error': return 'bg-yellow-500'
      default: return 'bg-gray-500'
    }
  }

  const getStatusTooltip = () => {
    switch (connectionStatus) {
      case 'connected': return 'Connected to MCP server'
      case 'disconnected': return 'Disconnected from MCP server'
      case 'error': return 'MCP server error'
      default: return 'Unknown status'
    }
  }

  return (
    <nav className="fixed top-0 left-0 right-0 z-40 glass border-b border-gray-200 dark:border-gray-700">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Left side */}
          <div className="flex items-center">
            <button
              onClick={toggleSidebar}
              className="p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Menu className="h-6 w-6" />
            </button>
            <Link to="/" className="ml-4 flex items-center space-x-2">
              <span className="text-2xl font-bold bg-gradient-to-r from-primary-600 to-blue-600 bg-clip-text text-transparent">
                Agentify
              </span>
            </Link>
          </div>

          {/* Right side */}
          <div className="flex items-center space-x-4">
            {/* New Chat Button */}
            <Link
              to="/"
              onClick={handleNewChat}
              className="hidden sm:flex items-center space-x-2 px-3 py-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Plus className="h-5 w-5" />
              <span className="text-sm font-medium">New Chat</span>
            </Link>

            {/* MCP Status */}
            <div 
              className="hidden sm:flex items-center"
              title={getStatusTooltip()}
            >
              <div className={cn('h-3 w-3 rounded-full', getStatusColor())} />
            </div>

            {/* Theme Toggle */}
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              {darkMode ? (
                <Sun className="h-6 w-6" />
              ) : (
                <Moon className="h-6 w-6" />
              )}
            </button>

            {/* Config Link */}
            <Link
              to="/config"
              className="p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            >
              <Settings className="h-6 w-6" />
            </Link>

            {/* User Menu */}
            <div className="relative">
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center space-x-2 p-2 rounded-md text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-full flex items-center justify-center">
                  <User className="w-5 h-5 text-white" />
                </div>
                <span className="hidden sm:block text-sm font-medium">
                  {user?.username || 'User'}
                </span>
                <ChevronDown className="w-4 h-4" />
              </button>

              {userMenuOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
                  <div className="py-1">
                    <div className="px-4 py-2 text-sm text-gray-700 dark:text-gray-300 border-b border-gray-200 dark:border-gray-600">
                      <div className="font-medium">{user?.full_name || user?.username}</div>
                      <div className="text-gray-500 dark:text-gray-400">{user?.email}</div>
                    </div>
                    <button
                      onClick={() => {
                        logout();
                        setUserMenuOpen(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center space-x-2"
                    >
                      <LogOut className="w-4 h-4" />
                      <span>Sign out</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Click outside to close user menu */}
      {userMenuOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setUserMenuOpen(false)}
        />
      )}
    </nav>
  )
}