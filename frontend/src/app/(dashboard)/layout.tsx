'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
import {
  LayoutDashboard,
  BarChart3,
  FlaskConical,
  Wallet,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  Bell,
  User,
  Activity,
  ChevronLeft,
  ChevronRight,
  ListChecks,
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { authApi, userApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import { IndexTicker } from '@/components/IndexTicker'
import { ThemeToggle } from '@/components/ThemeToggle'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Live Strategies', href: '/dashboard/live-strategies', icon: Activity },
  { name: 'Strategies', href: '/dashboard/strategies', icon: BarChart3 },
  { name: 'Backtest', href: '/dashboard/backtest', icon: FlaskConical },
  { name: 'Portfolio', href: '/dashboard/portfolio', icon: Wallet },
  { name: 'Order Logs', href: '/dashboard/orders/test', icon: ListChecks },
  { name: 'Reports', href: '/dashboard/reports', icon: FileText },
  { name: 'Settings', href: '/dashboard/settings', icon: Settings },
]

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const router = useRouter()
  const pathname = usePathname()
  const { user, isAuthenticated, setAuth, logout, setLoading } = useAuthStore()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [isInitialized, setIsInitialized] = useState(false)

  // Load sidebar collapsed state from localStorage
  useEffect(() => {
    const collapsed = localStorage.getItem('sidebarCollapsed') === 'true'
    setSidebarCollapsed(collapsed)
  }, [])

  // Save sidebar collapsed state to localStorage
  const toggleSidebarCollapse = () => {
    const newState = !sidebarCollapsed
    setSidebarCollapsed(newState)
    localStorage.setItem('sidebarCollapsed', String(newState))
  }

  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('access_token')
      const refreshToken = localStorage.getItem('refresh_token')

      if (!token) {
        router.push('/login')
        return
      }

      try {
        const userData = await userApi.getProfile()
        setAuth(userData, token, refreshToken || '')
      } catch (error) {
        logout()
        router.push('/login')
      } finally {
        setIsInitialized(true)
        setLoading(false)
      }
    }

    initAuth()
  }, [])

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch (error) {
      // Ignore errors, just clear local state
    }
    logout()
    router.push('/login')
  }

  if (!isInitialized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-50 via-white to-yellow-50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-50/50 via-white to-yellow-50/50 dark:from-gray-950 dark:via-gray-900 dark:to-gray-950">
      {/* Background Effects */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-purple-200/30 dark:bg-purple-900/20 rounded-full blur-[128px]" />
        <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-yellow-200/30 dark:bg-yellow-900/10 rounded-full blur-[128px]" />
      </div>

      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 bg-white/80 dark:bg-gray-900/90 backdrop-blur-xl border-r border-purple-200/50 dark:border-purple-900/30 transform transition-all duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
          sidebarCollapsed ? 'w-20' : 'w-64'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-purple-200/50 dark:border-purple-900/30">
            <Link href="/dashboard" className="flex items-center gap-2 min-w-0">
              <Image src="/logo.png" alt="Logo" width={32} height={32} className="h-8 w-8 flex-shrink-0" />
              {!sidebarCollapsed && (
                <span className="text-xl font-bold bg-gradient-to-r from-purple-600 to-yellow-500 bg-clip-text text-transparent whitespace-nowrap">
                  ArthaQuant
                </span>
              )}
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
            {navigation.map((item) => {
              const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
              return (
                <Link
                  key={item.name}
                  href={item.href}
                  title={sidebarCollapsed ? item.name : undefined}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all',
                    isActive
                      ? 'bg-gradient-to-r from-purple-600 to-purple-700 text-white shadow-lg shadow-purple-500/25'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-purple-100 dark:hover:bg-purple-900/30 hover:text-purple-700 dark:hover:text-purple-300',
                    sidebarCollapsed && 'justify-center'
                  )}
                >
                  <item.icon className="h-5 w-5 flex-shrink-0" />
                  {!sidebarCollapsed && <span className="whitespace-nowrap">{item.name}</span>}
                </Link>
              )
            })}
          </nav>

          {/* Collapse Toggle & User section */}
          <div className="p-4 border-t border-purple-200/50 dark:border-purple-900/30 space-y-2">
            {/* Desktop collapse toggle */}
            <button
              onClick={toggleSidebarCollapse}
              className="hidden lg:flex items-center justify-center w-full px-3 py-2 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-purple-100 dark:hover:bg-purple-900/30 transition-colors"
              title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {sidebarCollapsed ? (
                <ChevronRight className="h-5 w-5" />
              ) : (
                <>
                  <ChevronLeft className="h-5 w-5" />
                  <span className="ml-2">Collapse</span>
                </>
              )}
            </button>

            {!sidebarCollapsed && (
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-yellow-500 flex items-center justify-center flex-shrink-0">
                  <User className="h-5 w-5 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{user?.full_name}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 truncate">{user?.email}</p>
                </div>
              </div>
            )}

            <button
              onClick={handleLogout}
              title={sidebarCollapsed ? 'Logout' : undefined}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors',
                sidebarCollapsed && 'justify-center'
              )}
            >
              <LogOut className="h-5 w-5 flex-shrink-0" />
              {!sidebarCollapsed && <span>Logout</span>}
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className={cn('relative z-10 transition-all duration-200', sidebarCollapsed ? 'lg:pl-20' : 'lg:pl-64')}>
        {/* Top header */}
        <header className="sticky top-0 z-30 h-16 bg-white/80 dark:bg-gray-900/80 backdrop-blur-xl border-b border-purple-200/50 dark:border-purple-900/30">
          <div className="flex items-center justify-between h-full px-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30"
            >
              <Menu className="h-5 w-5" />
            </button>

            {/* Market Index Ticker */}
            <div className="hidden sm:flex flex-1 justify-center mx-4">
              <IndexTicker />
            </div>

            <div className="flex items-center gap-3 sm:ml-0 ml-auto">
              {/* Dark Mode Toggle */}
              <ThemeToggle />

              <button className="p-2 rounded-lg hover:bg-purple-100 dark:hover:bg-purple-900/30 relative">
                <Bell className="h-5 w-5 text-gray-600 dark:text-gray-400" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>
              <div className="h-8 w-px bg-purple-200 dark:bg-purple-900/50"></div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-yellow-500 flex items-center justify-center">
                  <User className="h-4 w-4 text-white" />
                </div>
                <span className="hidden sm:block text-sm font-medium">
                  {user?.full_name?.split(' ')[0]}
                </span>
              </div>
            </div>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 lg:p-6">{children}</main>
      </div>
    </div>
  )
}
