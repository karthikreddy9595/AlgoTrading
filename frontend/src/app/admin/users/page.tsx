'use client'

import { useEffect, useState } from 'react'
import {
  Users,
  UserCheck,
  Activity,
  Link2,
  Search,
  Shield,
  ShieldOff,
  UserX,
  UserPlus,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'

interface UserStats {
  total_users: number
  active_users: number
  trading_users: number
  connected_users: number
}

interface User {
  id: string
  email: string
  full_name: string
  phone: string | null
  is_active: boolean
  is_admin: boolean
  email_verified: boolean
  created_at: string
}

export default function AdminUsersPage() {
  const [stats, setStats] = useState<UserStats | null>(null)
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'active' | 'inactive'>('all')
  const [page, setPage] = useState(1)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const pageSize = 10

  useEffect(() => {
    fetchStats()
  }, [])

  useEffect(() => {
    fetchUsers()
  }, [search, filter, page])

  const fetchStats = async () => {
    try {
      const data = await adminApi.getUserStats()
      setStats(data)
    } catch (error) {
      console.error('Failed to fetch user stats:', error)
    }
  }

  const fetchUsers = async () => {
    setIsLoading(true)
    try {
      const params: any = {
        skip: (page - 1) * pageSize,
        limit: pageSize,
      }
      if (search) params.search = search
      if (filter !== 'all') params.is_active = filter === 'active'

      const data = await adminApi.getUsers(params)
      setUsers(data || [])
    } catch (error) {
      console.error('Failed to fetch users:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAction = async (userId: string, action: 'activate' | 'deactivate' | 'make-admin' | 'remove-admin') => {
    setActionLoading(userId)
    try {
      switch (action) {
        case 'activate':
          await adminApi.activateUser(userId)
          toast.success('User activated')
          break
        case 'deactivate':
          await adminApi.deactivateUser(userId)
          toast.success('User deactivated')
          break
        case 'make-admin':
          await adminApi.makeAdmin(userId)
          toast.success('Admin privileges granted')
          break
        case 'remove-admin':
          await adminApi.removeAdmin(userId)
          toast.success('Admin privileges removed')
          break
      }
      await fetchUsers()
      await fetchStats()
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Action failed')
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">User Management</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Manage platform users and permissions
        </p>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Total Users"
          value={String(stats?.total_users || 0)}
          icon={<Users className="h-5 w-5" />}
          color="blue"
        />
        <StatCard
          title="Active Users"
          value={String(stats?.active_users || 0)}
          icon={<UserCheck className="h-5 w-5" />}
          color="green"
        />
        <StatCard
          title="Trading Users"
          value={String(stats?.trading_users || 0)}
          icon={<Activity className="h-5 w-5" />}
          color="purple"
        />
        <StatCard
          title="Connected to Broker"
          value={String(stats?.connected_users || 0)}
          icon={<Link2 className="h-5 w-5" />}
          color="indigo"
        />
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-4">
        <div className="flex flex-wrap items-center gap-4">
          <div className="relative flex-1 min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => {
                setSearch(e.target.value)
                setPage(1)
              }}
              placeholder="Search by email or name..."
              className="w-full pl-10 pr-4 py-2 text-sm rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>
          <div className="flex gap-2">
            {(['all', 'active', 'inactive'] as const).map((f) => (
              <button
                key={f}
                onClick={() => {
                  setFilter(f)
                  setPage(1)
                }}
                className={cn(
                  'px-4 py-2 text-sm rounded-lg capitalize',
                  filter === f
                    ? 'bg-primary text-white'
                    : 'border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'
                )}
              >
                {f}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Users table */}
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
        <div className="overflow-x-auto">
          {isLoading ? (
            <div className="p-8 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
          ) : users.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-gray-400">
              No users found
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr className="text-left text-sm text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-800">
                  <th className="px-6 py-4 font-medium">User</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Role</th>
                  <th className="px-6 py-4 font-medium">Verified</th>
                  <th className="px-6 py-4 font-medium">Joined</th>
                  <th className="px-6 py-4 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
                {users.map((user) => (
                  <tr key={user.id} className="text-sm">
                    <td className="px-6 py-4">
                      <div className="font-medium">{user.full_name}</div>
                      <div className="text-xs text-gray-500">{user.email}</div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={cn(
                        'px-2 py-1 text-xs rounded',
                        user.is_active
                          ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                          : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                      )}>
                        {user.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {user.is_admin ? (
                        <span className="flex items-center gap-1 text-red-600 dark:text-red-400">
                          <Shield className="h-4 w-4" />
                          Admin
                        </span>
                      ) : (
                        <span className="text-gray-500">User</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {user.email_verified ? (
                        <span className="text-green-600">Yes</span>
                      ) : (
                        <span className="text-gray-400">No</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-gray-500">
                      {new Date(user.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {user.is_active ? (
                          <button
                            onClick={() => handleAction(user.id, 'deactivate')}
                            disabled={actionLoading === user.id}
                            title="Deactivate user"
                            className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg disabled:opacity-50"
                          >
                            {actionLoading === user.id ? (
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-red-500"></div>
                            ) : (
                              <UserX className="h-4 w-4" />
                            )}
                          </button>
                        ) : (
                          <button
                            onClick={() => handleAction(user.id, 'activate')}
                            disabled={actionLoading === user.id}
                            title="Activate user"
                            className="p-2 text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg disabled:opacity-50"
                          >
                            {actionLoading === user.id ? (
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-green-500"></div>
                            ) : (
                              <UserPlus className="h-4 w-4" />
                            )}
                          </button>
                        )}
                        {user.is_admin ? (
                          <button
                            onClick={() => handleAction(user.id, 'remove-admin')}
                            disabled={actionLoading === user.id}
                            title="Remove admin privileges"
                            className="p-2 text-orange-500 hover:bg-orange-50 dark:hover:bg-orange-900/20 rounded-lg disabled:opacity-50"
                          >
                            <ShieldOff className="h-4 w-4" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleAction(user.id, 'make-admin')}
                            disabled={actionLoading === user.id}
                            title="Grant admin privileges"
                            className="p-2 text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg disabled:opacity-50"
                          >
                            <Shield className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {users.length > 0 && (
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-800">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              Page {page}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(page - 1)}
                disabled={page === 1}
                className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <ChevronLeft className="h-4 w-4" />
              </button>
              <button
                onClick={() => setPage(page + 1)}
                disabled={users.length < pageSize}
                className="p-2 rounded-lg border border-gray-200 dark:border-gray-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <ChevronRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function StatCard({
  title,
  value,
  icon,
  color,
}: {
  title: string
  value: string
  icon: React.ReactNode
  color: 'blue' | 'green' | 'purple' | 'indigo'
}) {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400',
    green: 'bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400',
    purple: 'bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400',
    indigo: 'bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-400',
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6">
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm text-gray-500 dark:text-gray-400">{title}</span>
        <div className={cn('p-2 rounded-lg', colorClasses[color])}>{icon}</div>
      </div>
      <div className="text-2xl font-bold">{value}</div>
    </div>
  )
}
