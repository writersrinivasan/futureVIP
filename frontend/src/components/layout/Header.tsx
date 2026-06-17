import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell,
  Search,
  Settings,
  User,
  LogOut,
  ChevronDown,
  Menu,
} from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { useUIStore } from '@/store/ui.store'
import { useAuthStore } from '@/store/auth.store'
import { useAuth } from '@/hooks/useAuth'
import { cn } from '@/utils/cn'

export const Header = () => {
  const navigate = useNavigate()
  const { currentPageTitle, unreadNotificationsCount, toggleSidebar, sidebarOpen } = useUIStore()
  const { user } = useAuthStore()
  const { logout } = useAuth()
  const [searchQuery, setSearchQuery] = useState('')
  const [searchFocused, setSearchFocused] = useState(false)

  return (
    <header className="h-16 bg-dark-card/80 backdrop-blur-md border-b border-dark-border flex items-center px-4 md:px-6 gap-4 sticky top-0 z-30">
      {/* Mobile menu toggle */}
      <button
        onClick={toggleSidebar}
        className="md:hidden text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-white/5 transition-colors"
      >
        <Menu className="w-5 h-5" />
      </button>

      {/* Page Title */}
      <div className="hidden md:block">
        <h1 className="text-lg font-bold text-slate-100">{currentPageTitle}</h1>
      </div>

      {/* Search */}
      <div className="flex-1 max-w-md mx-auto md:mx-4">
        <div
          className={cn(
            'relative flex items-center rounded-xl border transition-all duration-300',
            searchFocused
              ? 'border-primary-500/50 bg-white/5'
              : 'border-white/10 bg-white/3'
          )}
        >
          <Search className="w-4 h-4 text-slate-400 ml-3 flex-shrink-0" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onFocus={() => setSearchFocused(true)}
            onBlur={() => setSearchFocused(false)}
            placeholder="Search jobs, skills, companies..."
            className="flex-1 bg-transparent text-sm text-slate-200 placeholder-slate-500 px-3 py-2 focus:outline-none"
          />
          <AnimatePresence>
            {searchFocused && (
              <motion.span
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="hidden md:block text-xs text-slate-500 mr-3 px-1.5 py-0.5 bg-white/5 rounded border border-white/10"
              >
                ⌘K
              </motion.span>
            )}
          </AnimatePresence>
        </div>
      </div>

      <div className="flex items-center gap-2 ml-auto">
        {/* Notifications Bell */}
        <button
          onClick={() => navigate('/notifications')}
          className="relative p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/5 transition-all duration-200"
        >
          <Bell className="w-5 h-5" />
          {unreadNotificationsCount > 0 && (
            <motion.span
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] bg-danger-500 text-white text-xs font-bold rounded-full flex items-center justify-center px-1"
            >
              {unreadNotificationsCount > 99 ? '99+' : unreadNotificationsCount}
            </motion.span>
          )}
        </button>

        {/* User Menu */}
        <DropdownMenu.Root>
          <DropdownMenu.Trigger asChild>
            <button className="flex items-center gap-2 p-1.5 pr-3 rounded-xl hover:bg-white/5 transition-all duration-200 border border-transparent hover:border-white/10">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-secondary-600 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                {user?.full_name?.charAt(0) || 'U'}
              </div>
              <span className="hidden md:block text-sm font-medium text-slate-200 max-w-[120px] truncate">
                {user?.full_name?.split(' ')[0] || 'User'}
              </span>
              <ChevronDown className="w-4 h-4 text-slate-400 hidden md:block" />
            </button>
          </DropdownMenu.Trigger>

          <DropdownMenu.Portal>
            <DropdownMenu.Content
              align="end"
              sideOffset={8}
              className="w-56 bg-dark-card border border-white/10 rounded-xl shadow-xl p-1.5 z-50 animate-slide-down"
            >
              <div className="px-3 py-2 border-b border-white/10 mb-1">
                <p className="text-sm font-semibold text-slate-200">{user?.full_name}</p>
                <p className="text-xs text-slate-500 truncate">{user?.email}</p>
              </div>

              <DropdownMenu.Item
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/5 rounded-lg cursor-pointer focus:outline-none"
                onSelect={() => navigate('/settings')}
              >
                <User className="w-4 h-4" />
                Profile
              </DropdownMenu.Item>

              <DropdownMenu.Item
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-slate-300 hover:text-white hover:bg-white/5 rounded-lg cursor-pointer focus:outline-none"
                onSelect={() => navigate('/settings')}
              >
                <Settings className="w-4 h-4" />
                Settings
              </DropdownMenu.Item>

              <DropdownMenu.Separator className="my-1 h-px bg-white/10" />

              <DropdownMenu.Item
                className="flex items-center gap-2.5 px-3 py-2 text-sm text-danger-400 hover:text-danger-300 hover:bg-danger-500/10 rounded-lg cursor-pointer focus:outline-none"
                onSelect={logout}
              >
                <LogOut className="w-4 h-4" />
                Sign Out
              </DropdownMenu.Item>
            </DropdownMenu.Content>
          </DropdownMenu.Portal>
        </DropdownMenu.Root>
      </div>
    </header>
  )
}
