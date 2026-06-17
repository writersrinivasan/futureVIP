import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UIState {
  sidebarOpen: boolean
  sidebarCollapsed: boolean
  theme: 'dark' | 'light'
  unreadNotificationsCount: number
  currentPageTitle: string
  setSidebarOpen: (open: boolean) => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void
  toggleSidebarCollapsed: () => void
  setTheme: (theme: 'dark' | 'light') => void
  setUnreadNotificationsCount: (count: number) => void
  decrementNotificationsCount: () => void
  setCurrentPageTitle: (title: string) => void
}

export const useUIStore = create<UIState>()(
  persist(
    (set, get) => ({
      sidebarOpen: true,
      sidebarCollapsed: false,
      theme: 'dark',
      unreadNotificationsCount: 0,
      currentPageTitle: 'Dashboard',

      setSidebarOpen: (open: boolean) => {
        set({ sidebarOpen: open })
      },

      setSidebarCollapsed: (collapsed: boolean) => {
        set({ sidebarCollapsed: collapsed })
      },

      toggleSidebar: () => {
        set({ sidebarOpen: !get().sidebarOpen })
      },

      toggleSidebarCollapsed: () => {
        set({ sidebarCollapsed: !get().sidebarCollapsed })
      },

      setTheme: (theme: 'dark' | 'light') => {
        set({ theme })
        if (theme === 'dark') {
          document.documentElement.classList.add('dark')
        } else {
          document.documentElement.classList.remove('dark')
        }
      },

      setUnreadNotificationsCount: (count: number) => {
        set({ unreadNotificationsCount: count })
      },

      decrementNotificationsCount: () => {
        const current = get().unreadNotificationsCount
        set({ unreadNotificationsCount: Math.max(0, current - 1) })
      },

      setCurrentPageTitle: (title: string) => {
        set({ currentPageTitle: title })
      },
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        sidebarCollapsed: state.sidebarCollapsed,
        theme: state.theme,
      }),
    }
  )
)
