'use client'

import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import {
  TrendingUp,
  LayoutDashboard,
  BarChart3,
  Wallet,
  FileText,
  Settings,
  LogOut,
  Menu,
  X,
  Bell,
  User,
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { authApi, userApi } from '@/lib/api'
import { cn } from '@/lib/utils'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Strategies', href: '/dashboard/strategies', icon: BarChart3 },
  { name: 'Portfolio', href: '/dashboard/portfolio', icon: Wallet },
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
  const [isInitialized, setIsInitialized] = useState(false)

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
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
      {/* Mobile sidebar backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transform transition-transform duration-200 ease-in-out lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-800">
            <Link href="/dashboard" className="flex items-center gap-2">
              <TrendingUp className="h-8 w-8 text-primary" />
              <span className="text-xl font-bold">AlgoTrading</span>
            </Link>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
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
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary'
                      : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                  )}
                >
                  <item.icon className="h-5 w-5" />
                  {item.name}
                </Link>
              )
            })}
          </nav>

          {/* User section */}
          <div className="p-4 border-t border-gray-200 dark:border-gray-800">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                <User className="h-5 w-5 text-primary" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.full_name}</p>
                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
              </div>
            </div>
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
            >
              <LogOut className="h-5 w-5" />
              Logout
            </button>
          </div>
        </div>
      </aside>

      {/* Main content */}
      <div className="lg:pl-64">
        {/* Top header */}
        <header className="sticky top-0 z-30 h-16 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
          <div className="flex items-center justify-between h-full px-4">
            <button
              onClick={() => setSidebarOpen(true)}
              className="lg:hidden p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <Menu className="h-5 w-5" />
            </button>

            <div className="flex items-center gap-4 ml-auto">
              <button className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 relative">
                <Bell className="h-5 w-5" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>
              <div className="h-8 w-px bg-gray-200 dark:bg-gray-700"></div>
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <User className="h-4 w-4 text-primary" />
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
