import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle auth errors and token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      
      // Try to refresh the token
      const refreshToken = localStorage.getItem('refreshToken')
      if (refreshToken) {
        try {
          const response = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${refreshToken}`,
              'Content-Type': 'application/json',
            },
          })
          
          if (response.ok) {
            const data = await response.json()
            localStorage.setItem('token', data.access_token)
            localStorage.setItem('refreshToken', data.refresh_token)
            localStorage.setItem('user', JSON.stringify(data.user))
            
            // Retry the original request with new token
            originalRequest.headers.Authorization = `Bearer ${data.access_token}`
            return api(originalRequest)
          }
        } catch (refreshError) {
          console.error('Token refresh failed:', refreshError)
        }
      }
      
      // If refresh fails, redirect to login
      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('user')
      window.location.href = '/auth'
    }
    
    return Promise.reject(error)
  }
)

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
}

export interface Thread {
  id: string
  title: string
  message_count: number
  last_message: string
  updated_at: string
}

export interface MCPServer {
  id: string
  name: string
  type: 'direct' | 'remote'
  url?: string
  command?: string
  args?: string[]
  authType: 'none' | 'api_key' | 'bearer' | 'custom'
  headers?: Record<string, string>
  description: string
  connected: boolean
}

export interface ChatResponse {
  thread_id: string
  response: string
}

// Chat API
export const chatAPI = {
  sendMessage: async (message: string, threadId?: string): Promise<ChatResponse> => {
    const requestBody = {
      message: message,
      ...(threadId && { thread_id: threadId })
    }
    
    const response = await api.post<ChatResponse>('/chat', requestBody)
    return response.data
  },

  getThreads: async (): Promise<Thread[]> => {
    const response = await api.get<Thread[]>('/threads')
    return response.data
  },

  getMessages: async (threadId: string): Promise<Message[]> => {
    const response = await api.get<Message[]>(`/threads/${threadId}/messages`)
    return response.data
  },

  createThread: async (title: string): Promise<{ thread_id: string; title: string }> => {
    const requestBody = {
      title: title
    }
    
    const response = await api.post('/threads', requestBody)
    return response.data
  },

  deleteThread: async (threadId: string): Promise<void> => {
    await api.delete(`/threads/${threadId}`)
  },
}

// MCP API
export const mcpAPI = {
  getStatus: async (): Promise<{status: string; tools_count: number; tools: string[]}> => {
    const response = await api.get<{status: string; tools_count: number; tools: string[]}>('/mcp/status')
    return response.data
  },

  getServers: async (): Promise<{ servers: MCPServer[] }> => {
    const response = await api.get<any[]>('/mcp/servers')
    
    // Transform backend MCPServerResponse to frontend MCPServer format
    const servers: MCPServer[] = response.data.map((backendServer: any) => ({
      id: backendServer.id,
      name: backendServer.name,
      description: backendServer.description || '',
      type: backendServer.server_type === 'sse' ? 'direct' : 'remote',
      url: backendServer.configuration?.url,
      command: backendServer.configuration?.command,
      args: backendServer.configuration?.args,
      authType: backendServer.configuration?.authType || 'none',
      headers: backendServer.configuration?.headers,
      connected: backendServer.is_active || false
    }));
    
    return { servers }
  },

  addServer: async (server: Omit<MCPServer, 'connected'>): Promise<{ message: string }> => {
    // Transform frontend MCPServer to backend MCPServerCreate schema
    const backendServer = {
      name: server.name,
      description: server.description,
      server_type: server.type === 'direct' ? 'sse' : 'stdio',
      configuration: {
        ...(server.type === 'direct' ? { url: server.url } : { command: server.command, args: server.args }),
        authType: server.authType,
        ...(server.headers && { headers: server.headers })
      }
    };
    
    const response = await api.post<{ message: string }>('/mcp/servers', backendServer)
    return response.data
  },

  deleteServer: async (serverId: string): Promise<{ message: string }> => {
    const response = await api.delete<{ message: string }>(`/mcp/servers/${serverId}`)
    return response.data
  },

  connectServer: async (serverId: string): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>(`/mcp/servers/${serverId}/connect`)
    return response.data
  },

  disconnectServer: async (serverId: string): Promise<{ message: string }> => {
    const response = await api.post<{ message: string }>(`/mcp/servers/${serverId}/disconnect`)
    return response.data
  },
}

export default api