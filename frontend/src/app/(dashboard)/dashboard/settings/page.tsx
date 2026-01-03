'use client'

import { useEffect, useState } from 'react'
import {
  User,
  Shield,
  Link2,
  Bell,
  Mail,
  Phone,
  Eye,
  EyeOff,
  Check,
  X,
  Trash2,
  ExternalLink,
} from 'lucide-react'
import { userApi, notificationsApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import { useAuthStore } from '@/stores/authStore'

type TabType = 'profile' | 'security' | 'brokers' | 'notifications'

interface BrokerConnection {
  id: string
  broker: string
  api_key: string
  is_active: boolean
  token_expiry: string | null
}

interface NotificationPreferences {
  email_enabled: boolean
  sms_enabled: boolean
  in_app_enabled: boolean
  trade_alerts: boolean
  daily_summary: boolean
  risk_alerts: boolean
}

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<TabType>('profile')
  const { user, setUser } = useAuthStore()

  const tabs = [
    { id: 'profile' as TabType, label: 'Profile', icon: User },
    { id: 'security' as TabType, label: 'Security', icon: Shield },
    { id: 'brokers' as TabType, label: 'Broker Connections', icon: Link2 },
    { id: 'notifications' as TabType, label: 'Notifications', icon: Bell },
  ]

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">Settings</h1>
        <p className="text-gray-500 dark:text-gray-400">
          Manage your account settings and preferences
        </p>
      </div>

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Sidebar navigation */}
        <div className="lg:w-64 flex-shrink-0">
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-2">
            <nav className="space-y-1">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={cn(
                    'w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors',
                    activeTab === tab.id
                      ? 'bg-primary text-white'
                      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                  )}
                >
                  <tab.icon className="h-5 w-5" />
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1">
          <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800">
            {activeTab === 'profile' && <ProfileTab user={user} setUser={setUser} />}
            {activeTab === 'security' && <SecurityTab />}
            {activeTab === 'brokers' && <BrokersTab />}
            {activeTab === 'notifications' && <NotificationsTab />}
          </div>
        </div>
      </div>
    </div>
  )
}

function ProfileTab({ user, setUser }: { user: any; setUser: (user: any) => void }) {
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [phone, setPhone] = useState(user?.phone || '')
  const [isLoading, setIsLoading] = useState(false)

  useEffect(() => {
    setFullName(user?.full_name || '')
    setPhone(user?.phone || '')
  }, [user])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    try {
      const updatedUser = await userApi.updateProfile({ full_name: fullName, phone: phone || undefined })
      setUser(updatedUser)
      toast.success('Profile updated successfully')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to update profile')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="p-6">
      <h2 className="text-lg font-semibold mb-6">Profile Information</h2>
      <form onSubmit={handleSubmit} className="space-y-6 max-w-md">
        <div>
          <label className="block text-sm font-medium mb-2">Email</label>
          <div className="flex items-center gap-3 px-4 py-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <Mail className="h-5 w-5 text-gray-400" />
            <span className="text-gray-600 dark:text-gray-300">{user?.email}</span>
            {user?.email_verified && (
              <span className="ml-auto flex items-center gap-1 text-xs text-green-600">
                <Check className="h-3 w-3" /> Verified
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Email cannot be changed
          </p>
        </div>

        <div>
          <label htmlFor="fullName" className="block text-sm font-medium mb-2">
            Full Name
          </label>
          <input
            id="fullName"
            type="text"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="Enter your full name"
          />
        </div>

        <div>
          <label htmlFor="phone" className="block text-sm font-medium mb-2">
            Phone Number
          </label>
          <div className="relative">
            <Phone className="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              id="phone"
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              className="w-full pl-12 pr-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="+91 9876543210"
            />
          </div>
        </div>

        <button
          type="submit"
          disabled={isLoading}
          className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Saving...
            </>
          ) : (
            'Save Changes'
          )}
        </button>
      </form>
    </div>
  )
}

function SecurityTab() {
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showCurrentPassword, setShowCurrentPassword] = useState(false)
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()

    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match')
      return
    }

    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }

    setIsLoading(true)
    try {
      await userApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      })
      toast.success('Password changed successfully')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to change password')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="p-6">
      <h2 className="text-lg font-semibold mb-6">Change Password</h2>
      <form onSubmit={handleSubmit} className="space-y-6 max-w-md">
        <div>
          <label htmlFor="currentPassword" className="block text-sm font-medium mb-2">
            Current Password
          </label>
          <div className="relative">
            <input
              id="currentPassword"
              type={showCurrentPassword ? 'text' : 'password'}
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-4 py-3 pr-12 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Enter current password"
              required
            />
            <button
              type="button"
              onClick={() => setShowCurrentPassword(!showCurrentPassword)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showCurrentPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
        </div>

        <div>
          <label htmlFor="newPassword" className="block text-sm font-medium mb-2">
            New Password
          </label>
          <div className="relative">
            <input
              id="newPassword"
              type={showNewPassword ? 'text' : 'password'}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-3 pr-12 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
              placeholder="Enter new password"
              required
              minLength={8}
            />
            <button
              type="button"
              onClick={() => setShowNewPassword(!showNewPassword)}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showNewPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Minimum 8 characters
          </p>
        </div>

        <div>
          <label htmlFor="confirmPassword" className="block text-sm font-medium mb-2">
            Confirm New Password
          </label>
          <input
            id="confirmPassword"
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary"
            placeholder="Confirm new password"
            required
          />
          {confirmPassword && newPassword !== confirmPassword && (
            <p className="mt-1 text-xs text-red-500">Passwords do not match</p>
          )}
        </div>

        <button
          type="submit"
          disabled={isLoading || !currentPassword || !newPassword || newPassword !== confirmPassword}
          className="px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isLoading ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Changing...
            </>
          ) : (
            'Change Password'
          )}
        </button>
      </form>
    </div>
  )
}

function BrokersTab() {
  const [connections, setConnections] = useState<BrokerConnection[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [deletingId, setDeletingId] = useState<string | null>(null)

  useEffect(() => {
    fetchConnections()
  }, [])

  const fetchConnections = async () => {
    try {
      const data = await userApi.getBrokerConnections()
      setConnections(data || [])
    } catch (error) {
      console.error('Failed to fetch broker connections:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDisconnect = async (connectionId: string) => {
    setDeletingId(connectionId)
    try {
      await userApi.deleteBrokerConnection(connectionId)
      setConnections(connections.filter((c) => c.id !== connectionId))
      toast.success('Broker disconnected successfully')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to disconnect broker')
    } finally {
      setDeletingId(null)
    }
  }

  const brokerInfo: Record<string, { name: string; color: string }> = {
    fyers: { name: 'Fyers', color: 'bg-blue-500' },
    zerodha: { name: 'Zerodha', color: 'bg-red-500' },
    angel: { name: 'Angel One', color: 'bg-orange-500' },
  }

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-lg font-semibold">Broker Connections</h2>
        <a
          href="/dashboard/broker"
          className="flex items-center gap-2 px-4 py-2 text-sm bg-primary text-white rounded-lg hover:bg-primary/90"
        >
          Connect Broker <ExternalLink className="h-4 w-4" />
        </a>
      </div>

      {connections.length === 0 ? (
        <div className="text-center py-12">
          <Link2 className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium mb-2">No brokers connected</h3>
          <p className="text-gray-500 dark:text-gray-400 mb-4">
            Connect a broker to start trading
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {connections.map((connection) => {
            const broker = brokerInfo[connection.broker] || { name: connection.broker, color: 'bg-gray-500' }
            return (
              <div
                key={connection.id}
                className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700"
              >
                <div className="flex items-center gap-4">
                  <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center text-white font-bold', broker.color)}>
                    {broker.name.charAt(0)}
                  </div>
                  <div>
                    <div className="font-medium">{broker.name}</div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      API Key: {connection.api_key?.slice(0, 8)}...
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-4">
                  <span
                    className={cn(
                      'px-2 py-1 text-xs rounded',
                      connection.is_active
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
                    )}
                  >
                    {connection.is_active ? 'Active' : 'Inactive'}
                  </span>
                  <button
                    onClick={() => handleDisconnect(connection.id)}
                    disabled={deletingId === connection.id}
                    className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg disabled:opacity-50"
                  >
                    {deletingId === connection.id ? (
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-red-500"></div>
                    ) : (
                      <Trash2 className="h-5 w-5" />
                    )}
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function NotificationsTab() {
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    email_enabled: true,
    sms_enabled: false,
    in_app_enabled: true,
    trade_alerts: true,
    daily_summary: true,
    risk_alerts: true,
  })
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    fetchPreferences()
  }, [])

  const fetchPreferences = async () => {
    try {
      const data = await notificationsApi.getPreferences()
      if (data) {
        setPreferences(data)
      }
    } catch (error) {
      console.error('Failed to fetch notification preferences:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleToggle = (key: keyof NotificationPreferences) => {
    setPreferences((prev) => ({ ...prev, [key]: !prev[key] }))
  }

  const handleSave = async () => {
    setIsSaving(true)
    try {
      await notificationsApi.updatePreferences(preferences)
      toast.success('Notification preferences saved')
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to save preferences')
    } finally {
      setIsSaving(false)
    }
  }

  if (isLoading) {
    return (
      <div className="p-6 flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
      </div>
    )
  }

  const notificationOptions = [
    {
      key: 'email_enabled' as keyof NotificationPreferences,
      title: 'Email Notifications',
      description: 'Receive notifications via email',
    },
    {
      key: 'sms_enabled' as keyof NotificationPreferences,
      title: 'SMS Notifications',
      description: 'Receive notifications via SMS',
    },
    {
      key: 'in_app_enabled' as keyof NotificationPreferences,
      title: 'In-App Notifications',
      description: 'Show notifications in the app',
    },
    {
      key: 'trade_alerts' as keyof NotificationPreferences,
      title: 'Trade Alerts',
      description: 'Get notified when trades are executed',
    },
    {
      key: 'daily_summary' as keyof NotificationPreferences,
      title: 'Daily Summary',
      description: 'Receive daily trading summary',
    },
    {
      key: 'risk_alerts' as keyof NotificationPreferences,
      title: 'Risk Alerts',
      description: 'Get notified about risk management events',
    },
  ]

  return (
    <div className="p-6">
      <h2 className="text-lg font-semibold mb-6">Notification Preferences</h2>
      <div className="space-y-4 max-w-lg">
        {notificationOptions.map((option) => (
          <div
            key={option.key}
            className="flex items-center justify-between p-4 rounded-lg border border-gray-200 dark:border-gray-700"
          >
            <div>
              <div className="font-medium">{option.title}</div>
              <div className="text-sm text-gray-500 dark:text-gray-400">
                {option.description}
              </div>
            </div>
            <button
              onClick={() => handleToggle(option.key)}
              className={cn(
                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                preferences[option.key] ? 'bg-primary' : 'bg-gray-300 dark:bg-gray-600'
              )}
            >
              <span
                className={cn(
                  'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                  preferences[option.key] ? 'translate-x-6' : 'translate-x-1'
                )}
              />
            </button>
          </div>
        ))}

        <button
          onClick={handleSave}
          disabled={isSaving}
          className="mt-6 px-6 py-3 bg-primary text-white rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
        >
          {isSaving ? (
            <>
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Saving...
            </>
          ) : (
            'Save Preferences'
          )}
        </button>
      </div>
    </div>
  )
}
