import { create } from 'zustand'
import { chatAPI, Message, Thread } from '../utils/api'
import toast from 'react-hot-toast'

interface ChatState {
  threads: Thread[]
  currentThread: Thread | null
  messages: Message[]
  isLoading: boolean
  isTyping: boolean
  
  // Actions
  loadThreads: () => Promise<void>
  createThread: (title: string) => Promise<string>
  selectThread: (threadId: string) => Promise<void>
  sendMessage: (message: string) => Promise<void>
  deleteThread: (threadId: string) => Promise<void>
  clearCurrentThread: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  threads: [],
  currentThread: null,
  messages: [],
  isLoading: false,
  isTyping: false,

  loadThreads: async () => {
    try {
      set({ isLoading: true })
      const threads = await chatAPI.getThreads()
      console.log('Chat store: Loaded threads', threads);
      set({ threads: Array.isArray(threads) ? threads : [], isLoading: false })
    } catch (error) {
      console.error('Failed to load threads:', error)
      toast.error('Failed to load threads')
      set({ threads: [], isLoading: false })
    }
  },

  createThread: async (title: string) => {
    try {
      const result = await chatAPI.createThread(title)
      await get().loadThreads()
      return result.thread_id
    } catch (error) {
      console.error('Failed to create thread:', error)
      toast.error('Failed to create thread')
      throw error
    }
  },

  selectThread: async (threadId: string) => {
    try {
      set({ isLoading: true })
      const [messages, threads] = await Promise.all([
        chatAPI.getMessages(threadId),
        chatAPI.getThreads()
      ])
      
      const thread = threads.find(t => t.id === threadId)
      set({ 
        currentThread: thread || null,
        messages,
        threads,
        isLoading: false 
      })
    } catch (error) {
      console.error('Failed to load thread:', error)
      toast.error('Failed to load thread')
      set({ isLoading: false })
    }
  },

  sendMessage: async (messageContent: string) => {
    const { currentThread } = get()
    
    try {
      set({ isTyping: true })
      
      // Add user message immediately for better UX
      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: messageContent,
        timestamp: new Date().toISOString()
      }
      
      set(state => ({ 
        messages: [...state.messages, userMessage] 
      }))

      const response = await chatAPI.sendMessage(messageContent, currentThread?.id)
      
      // Add assistant response
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.response,
        timestamp: new Date().toISOString()
      }
      
      set(state => ({ 
        messages: [...state.messages, assistantMessage],
        isTyping: false
      }))

      // If no current thread, select the new one
      if (!currentThread && response.thread_id) {
        await get().selectThread(response.thread_id)
      } else {
        // Refresh threads to update message count
        await get().loadThreads()
      }
      
    } catch (error) {
      console.error('Failed to send message:', error)
      toast.error('Failed to send message')
      set({ isTyping: false })
    }
  },

  deleteThread: async (threadId: string) => {
    try {
      await chatAPI.deleteThread(threadId)
      await get().loadThreads()
      
      // If we deleted the current thread, clear it
      if (get().currentThread?.id === threadId) {
        set({ currentThread: null, messages: [] })
      }
      
      toast.success('Thread deleted')
    } catch (error) {
      console.error('Failed to delete thread:', error)
      toast.error('Failed to delete thread')
    }
  },

  clearCurrentThread: () => {
    set({ currentThread: null, messages: [] })
  },
}))