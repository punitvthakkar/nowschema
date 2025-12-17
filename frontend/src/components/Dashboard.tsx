'use client'

import { useEffect, useState } from 'react'
import {
  MagnifyingGlassIcon,
  ClockIcon,
  BoltIcon,
  ServerIcon,
} from '@heroicons/react/24/outline'
import { useConfigStore } from '@/lib/store'

interface StatCard {
  name: string
  value: string
  change: string
  changeType: 'increase' | 'decrease' | 'neutral'
  icon: typeof MagnifyingGlassIcon
}

const mockStats: StatCard[] = [
  {
    name: 'Total Queries',
    value: '12,847',
    change: '+12%',
    changeType: 'increase',
    icon: MagnifyingGlassIcon,
  },
  {
    name: 'Avg Latency',
    value: '142ms',
    change: '-8%',
    changeType: 'decrease',
    icon: ClockIcon,
  },
  {
    name: 'Cache Hit Rate',
    value: '67%',
    change: '+5%',
    changeType: 'increase',
    icon: BoltIcon,
  },
  {
    name: 'Active Keys',
    value: '8',
    change: '+2',
    changeType: 'neutral',
    icon: ServerIcon,
  },
]

export default function Dashboard() {
  const { isConfigured, credentials } = useConfigStore()
  const [apiHealth, setApiHealth] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Fetch API health
    const fetchHealth = async () => {
      try {
        const res = await fetch(`${credentials.apiBaseUrl}-health.modal.run`)
        const data = await res.json()
        setApiHealth(data)
      } catch (e) {
        console.error('Failed to fetch health:', e)
      } finally {
        setLoading(false)
      }
    }

    if (credentials.apiBaseUrl) {
      fetchHealth()
    } else {
      setLoading(false)
    }
  }, [credentials.apiBaseUrl])

  return (
    <div className="space-y-6">
      {/* Config Warning */}
      {!isConfigured && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <span className="text-2xl">⚠️</span>
            <div>
              <h3 className="font-medium text-yellow-800">Configuration Required</h3>
              <p className="text-sm text-yellow-700 mt-1">
                Please configure your service credentials to enable all enterprise features.
                Click the "Configure Services" button in the header to get started.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {mockStats.map((stat) => (
          <div
            key={stat.name}
            className="bg-white rounded-xl shadow-sm border border-gray-200 p-6"
          >
            <div className="flex items-center justify-between">
              <div className="p-2 bg-primary-50 rounded-lg">
                <stat.icon className="h-6 w-6 text-primary-600" />
              </div>
              <span
                className={`text-sm font-medium ${
                  stat.changeType === 'increase'
                    ? 'text-green-600'
                    : stat.changeType === 'decrease'
                    ? 'text-green-600'
                    : 'text-gray-600'
                }`}
              >
                {stat.change}
              </span>
            </div>
            <div className="mt-4">
              <h3 className="text-2xl font-bold text-gray-900">{stat.value}</h3>
              <p className="text-sm text-gray-500">{stat.name}</p>
            </div>
          </div>
        ))}
      </div>

      {/* API Health */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">API Health</h3>
          {loading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          ) : apiHealth ? (
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Status</span>
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-400 rounded-full"></span>
                  <span className="text-green-600 font-medium">{apiHealth.status}</span>
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Items Indexed</span>
                <span className="font-medium">{apiHealth.items_indexed?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Embedding Dimension</span>
                <span className="font-medium">{apiHealth.embedding_dim}</span>
              </div>
              {apiHealth.services && (
                <div className="mt-4 pt-4 border-t border-gray-200">
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Services</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(apiHealth.services).map(([service, status]) => (
                      <div key={service} className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${status ? 'bg-green-400' : 'bg-gray-300'}`}></span>
                        <span className="text-sm text-gray-600 capitalize">{service.replace('_', ' ')}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-gray-500 text-sm">
              Unable to fetch API health. Make sure the API is deployed.
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <a
              href={`${credentials.apiBaseUrl}-search-get.modal.run?q=door+handle&top_k=5`}
              target="_blank"
              rel="noopener noreferrer"
              className="block w-full p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <div className="font-medium text-gray-900">🔍 Test Search</div>
              <div className="text-sm text-gray-500">Try a sample search query</div>
            </a>
            <button
              className="block w-full p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left"
            >
              <div className="font-medium text-gray-900">📖 API Documentation</div>
              <div className="text-sm text-gray-500">View endpoint documentation</div>
            </button>
            <button
              className="block w-full p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left"
            >
              <div className="font-medium text-gray-900">🔧 Deploy Update</div>
              <div className="text-sm text-gray-500">Redeploy the API with new config</div>
            </button>
          </div>
        </div>
      </div>

      {/* Recent Activity */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Recent Activity</h3>
        <div className="space-y-4">
          {[
            { action: 'API key created', time: '2 minutes ago', user: 'admin@company.com' },
            { action: 'Batch search: 50 queries', time: '15 minutes ago', user: 'api-key-prod' },
            { action: 'Rate limit triggered', time: '1 hour ago', user: 'api-key-test' },
            { action: 'New tenant registered', time: '3 hours ago', user: 'john@example.com' },
          ].map((activity, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0">
              <div>
                <div className="font-medium text-gray-900">{activity.action}</div>
                <div className="text-sm text-gray-500">{activity.user}</div>
              </div>
              <div className="text-sm text-gray-400">{activity.time}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
