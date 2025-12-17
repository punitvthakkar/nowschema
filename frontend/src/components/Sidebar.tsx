'use client'

import {
  HomeIcon,
  KeyIcon,
  ChartBarIcon,
  CreditCardIcon,
  Cog6ToothIcon,
} from '@heroicons/react/24/outline'
import clsx from 'clsx'

type Tab = 'dashboard' | 'api-keys' | 'usage' | 'billing' | 'settings'

interface Props {
  activeTab: Tab
  onTabChange: (tab: Tab) => void
}

const navigation = [
  { id: 'dashboard' as Tab, name: 'Dashboard', icon: HomeIcon },
  { id: 'api-keys' as Tab, name: 'API Keys', icon: KeyIcon },
  { id: 'usage' as Tab, name: 'Usage', icon: ChartBarIcon },
  { id: 'billing' as Tab, name: 'Billing', icon: CreditCardIcon },
  { id: 'settings' as Tab, name: 'Settings', icon: Cog6ToothIcon },
]

export default function Sidebar({ activeTab, onTabChange }: Props) {
  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-gray-800">
        <h1 className="text-xl font-bold flex items-center gap-2">
          <span className="text-2xl">🏗️</span>
          <span>Uniclass</span>
        </h1>
        <p className="text-xs text-gray-400 mt-1">Enterprise Admin</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navigation.map((item) => {
          const isActive = activeTab === item.id
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={clsx(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary-600 text-white'
                  : 'text-gray-300 hover:bg-gray-800 hover:text-white'
              )}
            >
              <item.icon className="h-5 w-5" />
              {item.name}
            </button>
          )
        })}
      </nav>

      {/* Status */}
      <div className="px-4 py-4 border-t border-gray-800">
        <div className="flex items-center gap-2 text-sm">
          <span className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
          <span className="text-gray-400">API Status:</span>
          <span className="text-green-400">Healthy</span>
        </div>
        <div className="mt-2 text-xs text-gray-500">
          v1.0.0 • Enterprise Edition
        </div>
      </div>
    </aside>
  )
}
