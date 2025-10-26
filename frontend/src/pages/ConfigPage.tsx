import React from 'react'
import { 
  Server, 
  Plus, 
  Edit, 
  Trash2, 
  Link,
  Power,
  Check
} from 'lucide-react'
import { Navbar } from '../components/Navbar'
import { Button } from '../components/Button'
import { Input } from '../components/Input'
import { Modal } from '../components/Modal'
import { useMCPStore } from '../store/mcp'
import { useUIStore } from '../store/ui'
import { MCPServer } from '../utils/api'
import { cn } from '../utils'

const ConfigPage: React.FC = () => {
  const { sidebarOpen } = useUIStore()
  const { servers, isLoading, loadServers, addServer, deleteServer, connectServer, disconnectServer } = useMCPStore()
  const [isAddModalOpen, setIsAddModalOpen] = React.useState(false)

  React.useEffect(() => {
    loadServers()
  }, [loadServers])

  return (
    <div className="h-full">
      <Navbar />
      
      {/* Main Content */}
      <main className={cn(
        'pt-16 min-h-screen transition-all duration-200',
        sidebarOpen ? 'lg:ml-64' : ''
      )}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">
              Configuration
            </h1>
            <p className="text-gray-600 dark:text-gray-400">
              Manage your MCP servers and LLM settings
            </p>
          </div>

          {/* MCP Servers Section */}
          <div className="card p-6 mb-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-xl font-bold flex items-center text-gray-900 dark:text-gray-100">
                <Server className="h-6 w-6 mr-2 text-primary-600" />
                MCP Servers
              </h2>
              <Button onClick={() => setIsAddModalOpen(true)}>
                <Plus className="h-5 w-5 mr-2" />
                Add Server
              </Button>
            </div>

            {isLoading ? (
              <div className="animate-pulse space-y-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg" />
                ))}
              </div>
            ) : !servers || servers.length === 0 ? (
              <div className="text-center py-12">
                <Server className="mx-auto h-12 w-12 text-gray-400 mb-4" />
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                  No MCP servers configured
                </h3>
                <p className="text-gray-500 dark:text-gray-400 mb-6">
                  Add your first MCP server to get started
                </p>
                <Button onClick={() => setIsAddModalOpen(true)}>
                  <Plus className="h-5 w-5 mr-2" />
                  Add MCP Server
                </Button>
              </div>
            ) : (
              <div className="space-y-4">
                {servers?.map((server) => (
                  <ServerCard
                    key={server.id}
                    server={server}
                    onConnect={() => connectServer(server.id)}
                    onDisconnect={() => disconnectServer(server.id)}
                    onDelete={() => deleteServer(server.id)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* LLM Configuration Section */}
          <LLMConfigSection />
        </div>
      </main>

      {/* Add Server Modal */}
      <AddServerModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdd={addServer}
      />
    </div>
  )
}

interface ServerCardProps {
  server: MCPServer
  onConnect: () => void
  onDisconnect: () => void
  onDelete: () => void
}

const ServerCard: React.FC<ServerCardProps> = ({ server, onConnect, onDisconnect, onDelete }) => {
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center space-x-3">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">
              {server.name}
            </h3>
            <span className={cn(
              'px-2 py-1 text-xs font-medium rounded-full',
              server.type === 'direct' 
                ? 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200'
                : 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200'
            )}>
              {server.type}
            </span>
            <span className={cn(
              'px-2 py-1 text-xs font-medium rounded-full',
              server.connected
                ? 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200'
                : 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200'
            )}>
              {server.connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            {server.description}
          </p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">
            {server.type === 'direct' ? server.url : `${server.command} ${server.args?.join(' ')}`}
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {/* Edit functionality */}}
          >
            <Edit className="h-4 w-4" />
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={server.connected ? onDisconnect : onConnect}
          >
            {server.connected ? (
              <Power className="h-4 w-4" />
            ) : (
              <Link className="h-4 w-4" />
            )}
          </Button>
          
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (confirm('Are you sure you want to delete this server?')) {
                onDelete()
              }
            }}
            className="text-red-600 hover:text-red-700"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

interface AddServerModalProps {
  isOpen: boolean
  onClose: () => void
  onAdd: (server: Omit<MCPServer, 'connected'>) => Promise<void>
}

const AddServerModal: React.FC<AddServerModalProps> = ({ isOpen, onClose, onAdd }) => {
  const [formData, setFormData] = React.useState({
    name: '',
    type: 'direct' as 'direct' | 'remote',
    url: '',
    command: '',
    args: '',
    authType: 'none' as 'none' | 'api_key' | 'bearer' | 'custom',
    headers: '',
    description: '',
  })

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      const server: Omit<MCPServer, 'connected'> = {
        id: '', // Backend will generate the ID
        name: formData.name,
        type: formData.type,
        authType: formData.authType,
        description: formData.description,
      }

      if (formData.type === 'direct') {
        server.url = formData.url
      } else {
        server.command = formData.command
        server.args = formData.args.split(',').map(arg => arg.trim())
      }

      if (formData.authType !== 'none' && formData.headers) {
        server.headers = JSON.parse(formData.headers)
      }

      await onAdd(server)
      onClose()
      setFormData({
        name: '',
        type: 'direct',
        url: '',
        command: '',
        args: '',
        authType: 'none',
        headers: '',
        description: '',
      })
    } catch (error) {
      // Handle error appropriately
    }
  }

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Add MCP Server" size="lg">
      <form onSubmit={handleSubmit} className="space-y-4">
        <Input
          label="Name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          placeholder="e.g., Kite Trading, Claude AI"
          required
        />

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Type
          </label>
          <select
            value={formData.type}
            onChange={(e) => setFormData({ ...formData, type: e.target.value as 'direct' | 'remote' })}
            className="input"
          >
            <option value="direct">Direct (SSE)</option>
            <option value="remote">Remote (stdio)</option>
          </select>
        </div>

        {formData.type === 'direct' ? (
          <Input
            label="URL"
            value={formData.url}
            onChange={(e) => setFormData({ ...formData, url: e.target.value })}
            placeholder="https://mcp.service.com/mcp"
            required
          />
        ) : (
          <div className="space-y-4">
            <Input
              label="Command"
              value={formData.command}
              onChange={(e) => setFormData({ ...formData, command: e.target.value })}
              placeholder="npx"
              required
            />
            <Input
              label="Arguments (comma-separated)"
              value={formData.args}
              onChange={(e) => setFormData({ ...formData, args: e.target.value })}
              placeholder="mcp-remote,https://mcp.service.com/mcp"
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Authentication Type
          </label>
          <select
            value={formData.authType}
            onChange={(e) => setFormData({ ...formData, authType: e.target.value as any })}
            className="input"
          >
            <option value="none">None</option>
            <option value="api_key">API Key</option>
            <option value="bearer">Bearer Token</option>
            <option value="custom">Custom Headers</option>
          </select>
        </div>

        {formData.authType !== 'none' && (
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Headers (JSON)
            </label>
            <textarea
              value={formData.headers}
              onChange={(e) => setFormData({ ...formData, headers: e.target.value })}
              className="input min-h-[80px]"
              placeholder='{"Authorization": "Bearer token"}'
            />
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Description
          </label>
          <textarea
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="input min-h-[60px]"
            placeholder="Brief description of this MCP server"
          />
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <Button type="button" variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit">
            <Check className="h-5 w-5 mr-2" />
            Add Server
          </Button>
        </div>
      </form>
    </Modal>
  )
}

const LLMConfigSection: React.FC = () => {
  const [config, setConfig] = React.useState({
    provider: 'openai',
    apiKey: '',
    model: 'gpt-4-turbo',
    azureEndpoint: '',
    apiVersion: '2024-12-01-preview',
    baseUrl: '',
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    // Handle LLM config save
  }

  return (
    <div className="card p-6">
      <h2 className="text-xl font-bold mb-6 flex items-center text-gray-900 dark:text-gray-100">
        <svg className="h-6 w-6 mr-2 text-primary-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2"
                d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
        </svg>
        LLM Configuration
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              Provider
            </label>
            <select
              value={config.provider}
              onChange={(e) => setConfig({ ...config, provider: e.target.value })}
              className="input"
            >
              <option value="openai">OpenAI</option>
              <option value="azure">Azure OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="groq">Groq</option>
              <option value="custom">Custom</option>
            </select>
          </div>

          <Input
            label="Model"
            value={config.model}
            onChange={(e) => setConfig({ ...config, model: e.target.value })}
            placeholder="gpt-4-turbo"
          />
        </div>

        <Input
          label="API Key"
          type="password"
          value={config.apiKey}
          onChange={(e) => setConfig({ ...config, apiKey: e.target.value })}
          placeholder="Enter your API key"
        />

        {config.provider === 'azure' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Input
              label="Azure Endpoint"
              value={config.azureEndpoint}
              onChange={(e) => setConfig({ ...config, azureEndpoint: e.target.value })}
              placeholder="https://your-endpoint.openai.azure.com"
            />
            <Input
              label="API Version"
              value={config.apiVersion}
              onChange={(e) => setConfig({ ...config, apiVersion: e.target.value })}
            />
          </div>
        )}

        {config.provider === 'custom' && (
          <Input
            label="Base URL"
            value={config.baseUrl}
            onChange={(e) => setConfig({ ...config, baseUrl: e.target.value })}
            placeholder="https://api.custom-llm.com/v1"
          />
        )}

        <div className="flex justify-end">
          <Button type="submit">
            <Check className="h-5 w-5 mr-2" />
            Save Changes
          </Button>
        </div>
      </form>
    </div>
  )
}

export default ConfigPage