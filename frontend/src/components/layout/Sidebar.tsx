import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  FileText,
  Briefcase,
  ClipboardList,
  TrendingUp,
  MessageSquare,
  Bell,
  Settings,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  LogOut,
} from 'lucide-react'
import { cn } from '@/utils/cn'
import { useUIStore } from '@/store/ui.store'
import { useAuthStore } from '@/store/auth.store'
import { useAuth } from '@/hooks/useAuth'
import { useNotifications } from '@/hooks/useNotifications'
import { Tooltip, TooltipProvider } from '@/components/common/Tooltip'

const navItems = [
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/resume', icon: FileText, label: 'Resume' },
  { to: '/jobs', icon: Briefcase, label: 'Jobs' },
  { to: '/applications', icon: ClipboardList, label: 'Applications' },
  { to: '/career', icon: TrendingUp, label: 'Career' },
  { to: '/interview', icon: MessageSquare, label: 'Interview' },
  { to: '/notifications', icon: Bell, label: 'Notifications', badge: true },
  { to: '/settings', icon: Settings, label: 'Settings' },
]

export const Sidebar = () => {
  const { sidebarCollapsed, toggleSidebarCollapsed } = useUIStore()
  const { user } = useAuthStore()
  const { logout } = useAuth()
  const { unreadCount } = useNotifications()
  const location = useLocation()

  const isActive = (to: string) => location.pathname === to || location.pathname.startsWith(to + '/')

  return (
    <TooltipProvider>
      <motion.aside
        animate={{ width: sidebarCollapsed ? 72 : 240 }}
        transition={{ type: 'spring', stiffness: 300, damping: 30 }}
        className="relative flex flex-col h-full bg-dark-card border-r border-dark-border overflow-hidden flex-shrink-0"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-4 py-5 border-b border-dark-border">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-primary-500 to-secondary-600 flex items-center justify-center flex-shrink-0 glow-primary">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <p className="font-bold text-base text-white tracking-tight leading-none">
                  FUTURE VIP
                </p>
                <p className="text-xs text-slate-500 mt-0.5">AI Career Intelligence</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Navigation */}
        <nav className="flex-1 p-3 space-y-1 overflow-y-auto overflow-x-hidden">
          {navItems.map((item) => {
            const active = isActive(item.to)
            const Icon = item.icon

            const navContent = (
              <NavLink
                key={item.to}
                to={item.to}
                className={cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all duration-200 relative group',
                  active
                    ? 'bg-primary-600/20 text-white border border-primary-500/30'
                    : 'text-slate-400 hover:text-white hover:bg-white/5'
                )}
              >
                <div className="relative flex-shrink-0">
                  <Icon
                    className={cn('w-5 h-5', active ? 'text-primary-400' : '')}
                  />
                  {item.badge && unreadCount > 0 && (
                    <span className="absolute -top-1.5 -right-1.5 min-w-[16px] h-4 bg-danger-500 text-white text-xs font-bold rounded-full flex items-center justify-center px-1">
                      {unreadCount > 99 ? '99+' : unreadCount}
                    </span>
                  )}
                </div>
                <AnimatePresence>
                  {!sidebarCollapsed && (
                    <motion.span
                      initial={{ opacity: 0, x: -5 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -5 }}
                      transition={{ duration: 0.15 }}
                      className="text-sm font-medium whitespace-nowrap overflow-hidden"
                    >
                      {item.label}
                    </motion.span>
                  )}
                </AnimatePresence>
                {active && (
                  <motion.div
                    layoutId="active-indicator"
                    className="absolute right-0 top-1/2 -translate-y-1/2 w-0.5 h-6 bg-primary-400 rounded-full"
                  />
                )}
              </NavLink>
            )

            if (sidebarCollapsed) {
              return (
                <Tooltip key={item.to} content={item.label} side="right">
                  {navContent}
                </Tooltip>
              )
            }

            return navContent
          })}
        </nav>

        {/* User Section */}
        <div className="p-3 border-t border-dark-border">
          <div
            className={cn(
              'flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 transition-all duration-200',
              sidebarCollapsed ? 'justify-center' : ''
            )}
          >
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-secondary-600 flex items-center justify-center flex-shrink-0 text-white text-sm font-bold">
              {user?.full_name?.charAt(0) || 'U'}
            </div>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.div
                  initial={{ opacity: 0, x: -5 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -5 }}
                  className="flex-1 min-w-0"
                >
                  <p className="text-sm font-medium text-slate-200 truncate">
                    {user?.full_name || 'User'}
                  </p>
                  <p className="text-xs text-slate-500 truncate">{user?.email || ''}</p>
                </motion.div>
              )}
            </AnimatePresence>
            <AnimatePresence>
              {!sidebarCollapsed && (
                <motion.button
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  onClick={logout}
                  className="text-slate-500 hover:text-danger-400 transition-colors p-1 rounded-lg hover:bg-danger-500/10 flex-shrink-0"
                  title="Logout"
                >
                  <LogOut className="w-4 h-4" />
                </motion.button>
              )}
            </AnimatePresence>
          </div>
        </div>

        {/* Collapse Toggle */}
        <button
          onClick={toggleSidebarCollapsed}
          className={cn(
            'absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full',
            'bg-dark-card border border-dark-border text-slate-400 hover:text-white',
            'flex items-center justify-center transition-all duration-200 hover:bg-dark-hover',
            'shadow-md z-10'
          )}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="w-3.5 h-3.5" />
          ) : (
            <ChevronLeft className="w-3.5 h-3.5" />
          )}
        </button>
      </motion.aside>
    </TooltipProvider>
  )
}
