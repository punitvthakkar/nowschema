'use client'

import { useState } from 'react'
import Sidebar from '@/components/Sidebar'
import Dashboard from '@/components/Dashboard'
import APIKeys from '@/components/APIKeys'
import UsageAnalytics from '@/components/UsageAnalytics'
import Billing from '@/components/Billing'
import Settings from '@/components/Settings'
import CredentialsDialog from '@/components/CredentialsDialog'
import { useConfigStore } from '@/lib/store'

type Tab = 'dashboard' | 'api-keys' | 'usage' | 'billing' | 'settings'

export default function Home() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [credentialsOpen, setCredentialsOpen] = useState(false)
  const { isConfigured } = useConfigStore()

  // Show credentials dialog on first visit if not configured
  useState(() => {
    if (!isConfigured) {
      setCredentialsOpen(true)
    }
  })

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard':
        return <Dashboard />
      case 'api-keys':
        return <APIKeys />
      case 'usage':
        return <UsageAnalytics />
      case 'billing':
        return <Billing />
      case 'settings':
        return <Settings onOpenCredentials={() => setCredentialsOpen(true)} />
      default:
        return <Dashboard />
    }
  }

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar activeTab={activeTab} onTabChange={setActiveTab} />

      <main className="flex-1 overflow-auto">
        <header className="bg-white border-b border-gray-200 px-8 py-4">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-semibold text-gray-900">
              {activeTab === 'dashboard' && 'Dashboard'}
              {activeTab === 'api-keys' && 'API Keys'}
              {activeTab === 'usage' && 'Usage Analytics'}
              {activeTab === 'billing' && 'Billing'}
              {activeTab === 'settings' && 'Settings'}
            </h1>

            {!isConfigured && (
              <button
                onClick={() => setCredentialsOpen(true)}
                className="px-4 py-2 bg-yellow-100 text-yellow-800 rounded-lg text-sm font-medium hover:bg-yellow-200 transition-colors"
              >
                ⚠️ Configure Services
              </button>
            )}
          </div>
        </header>

        <div className="p-8">
          {renderContent()}
        </div>
      </main>

      <CredentialsDialog
        open={credentialsOpen}
        onClose={() => setCredentialsOpen(false)}
      />
    </div>
  )
}
