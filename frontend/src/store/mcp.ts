import { create } from 'zustand'
import { mcpAPI, MCPServer } from '../utils/api'
import toast from 'react-hot-toast'

interface MCPState {
  servers: MCPServer[]
  isLoading: boolean
  connectionStatus: 'connected' | 'disconnected' | 'error'
  
  // Actions
  loadServers: () => Promise<void>
  addServer: (server: Omit<MCPServer, 'connected'>) => Promise<void>
  deleteServer: (serverId: string) => Promise<void>
  connectServer: (serverId: string) => Promise<void>
  disconnectServer: (serverId: string) => Promise<void>
  checkStatus: () => Promise<void>
}

export const useMCPStore = create<MCPState>((set, get) => ({
  servers: [],
  isLoading: false,
  connectionStatus: 'disconnected',

  loadServers: async () => {
    try {
      set({ isLoading: true })
      const data = await mcpAPI.getServers()
      set({ servers: data.servers, isLoading: false })
    } catch (error) {
      console.error('Failed to load MCP servers:', error)
      toast.error('Failed to load MCP servers')
      set({ isLoading: false })
    }
  },

  addServer: async (server) => {
    try {
      await mcpAPI.addServer(server)
      await get().loadServers()
      toast.success('MCP server added successfully')
    } catch (error) {
      console.error('Failed to add MCP server:', error)
      toast.error('Failed to add MCP server')
    }
  },

  deleteServer: async (serverId) => {
    try {
      await mcpAPI.deleteServer(serverId)
      await get().loadServers()
      toast.success('MCP server deleted successfully')
    } catch (error) {
      console.error('Failed to delete MCP server:', error)
      toast.error('Failed to delete MCP server')
    }
  },

  connectServer: async (serverId) => {
    try {
      await mcpAPI.connectServer(serverId)
      await get().loadServers()
      await get().checkStatus()
      toast.success('Connected to MCP server')
    } catch (error) {
      console.error('Failed to connect to MCP server:', error)
      toast.error('Failed to connect to MCP server')
    }
  },

  disconnectServer: async (serverId) => {
    try {
      await mcpAPI.disconnectServer(serverId)
      await get().loadServers()
      await get().checkStatus()
      toast.success('Disconnected from MCP server')
    } catch (error) {
      console.error('Failed to disconnect from MCP server:', error)
      toast.error('Failed to disconnect from MCP server')
    }
  },

  checkStatus: async () => {
    try {
      const statusData = await mcpAPI.getStatus()
      
      if (statusData.status === 'connected') {
        set({ connectionStatus: 'connected' })
      } else if (statusData.status === 'disconnected') {
        set({ connectionStatus: 'disconnected' })
      } else {
        set({ connectionStatus: 'error' })
      }
    } catch (error) {
      console.error('Failed to check MCP status:', error)
      set({ connectionStatus: 'error' })
    }
  },
}))