import React from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useUIStore } from './store/ui'
import { AuthProvider } from './contexts/AuthContext'
import { ProtectedRoute } from './components/ProtectedRoute'
import ChatPage from './pages/ChatPage'
import ConfigPage from './pages/ConfigPage'
import AuthPage from './pages/AuthPage'
import { cn } from './utils'

function App() {
  const { darkMode } = useUIStore()

  React.useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  return (
    <div className={cn('h-full', darkMode && 'dark')}>
      <AuthProvider>
        <Router>
          <Routes>
            <Route path="/auth" element={<AuthPage />} />
            <Route 
              path="/" 
              element={
                <ProtectedRoute>
                  <ChatPage />
                </ProtectedRoute>
              } 
            />
            <Route 
              path="/config" 
              element={
                <ProtectedRoute>
                  <ConfigPage />
                </ProtectedRoute>
              } 
            />
          </Routes>
        </Router>
        
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 5000,
            style: {
              background: darkMode ? '#1f2937' : '#ffffff',
              color: darkMode ? '#f9fafb' : '#111827',
              border: `1px solid ${darkMode ? '#374151' : '#e5e7eb'}`,
              fontSize: '16px',
              padding: '16px 20px',
              minWidth: '320px',
              maxWidth: '500px',
              borderRadius: '12px',
              boxShadow: darkMode 
                ? '0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.1)' 
                : '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
            },
            success: {
              iconTheme: {
                primary: '#10b981',
                secondary: '#ffffff',
              },
            },
            error: {
              iconTheme: {
                primary: '#ef4444',
                secondary: '#ffffff',
              },
            },
          }}
        />
      </AuthProvider>
    </div>
  )
}

export default App