import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UIState {
  darkMode: boolean
  sidebarOpen: boolean
  toggleDarkMode: () => void
  toggleSidebar: () => void
  setSidebarOpen: (open: boolean) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      darkMode: false,
      sidebarOpen: false,
      toggleDarkMode: () => set((state) => ({ darkMode: !state.darkMode })),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
    }),
    {
      name: 'ui-store',
      partialize: (state) => ({ darkMode: state.darkMode }),
    }
  )
)