'use client'

import { useState } from 'react'
import {
  KeyIcon,
  ShieldCheckIcon,
  BellIcon,
  GlobeAltIcon,
  TrashIcon,
} from '@heroicons/react/24/outline'
import { useConfigStore } from '@/lib/store'
import toast from 'react-hot-toast'

interface Props {
  onOpenCredentials: () => void
}

export default function Settings({ onOpenCredentials }: Props) {
  const { credentials, isConfigured, clearCredentials } = useConfigStore()
  const [notifications, setNotifications] = useState({
    quotaWarning: true,
    usageReport: true,
    securityAlerts: true,
  })

  const handleClearCredentials = () => {
    if (confirm('Are you sure you want to clear all credentials? This cannot be undone.')) {
      clearCredentials()
      toast.success('Credentials cleared')
    }
  }

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Service Credentials */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-primary-50 rounded-lg">
            <KeyIcon className="h-6 w-6 text-primary-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">Service Credentials</h3>
            <p className="text-sm text-gray-500 mt-1">
              Configure API keys and secrets for all integrated services.
            </p>

            <div className="mt-4 space-y-3">
              {/* Status indicators */}
              <div className="grid grid-cols-2 gap-3">
                {[
                  { name: 'Supabase', configured: !!credentials.supabaseUrl },
                  { name: 'Upstash Redis', configured: !!credentials.upstashRedisUrl },
                  { name: 'Stripe', configured: !!credentials.stripeSecretKey },
                  { name: 'WorkOS', configured: !!credentials.workosApiKey },
                  { name: 'Grafana', configured: !!credentials.grafanaApiKey },
                  { name: 'Modal', configured: !!credentials.modalTokenId },
                ].map((service) => (
                  <div key={service.name} className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${
                      service.configured ? 'bg-green-500' : 'bg-gray-300'
                    }`} />
                    <span className="text-sm text-gray-600">{service.name}</span>
                    <span className={`text-xs ${
                      service.configured ? 'text-green-600' : 'text-gray-400'
                    }`}>
                      {service.configured ? 'Configured' : 'Not configured'}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-4 flex gap-3">
              <button
                onClick={onOpenCredentials}
                className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
              >
                Configure Credentials
              </button>
              {isConfigured && (
                <button
                  onClick={handleClearCredentials}
                  className="px-4 py-2 border border-red-300 text-red-600 rounded-lg hover:bg-red-50 transition-colors"
                >
                  Clear All
                </button>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Security */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-green-50 rounded-lg">
            <ShieldCheckIcon className="h-6 w-6 text-green-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">Security</h3>
            <p className="text-sm text-gray-500 mt-1">
              Manage security settings and access controls.
            </p>

            <div className="mt-4 space-y-4">
              <div className="flex items-center justify-between py-3 border-b border-gray-100">
                <div>
                  <div className="font-medium text-gray-900">Two-Factor Authentication</div>
                  <div className="text-sm text-gray-500">Add an extra layer of security</div>
                </div>
                <button className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50">
                  Enable
                </button>
              </div>

              <div className="flex items-center justify-between py-3 border-b border-gray-100">
                <div>
                  <div className="font-medium text-gray-900">API Key Rotation</div>
                  <div className="text-sm text-gray-500">Automatically rotate keys every 90 days</div>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input type="checkbox" className="sr-only peer" />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                </label>
              </div>

              <div className="flex items-center justify-between py-3">
                <div>
                  <div className="font-medium text-gray-900">IP Allowlist</div>
                  <div className="text-sm text-gray-500">Restrict API access to specific IPs</div>
                </div>
                <button className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm font-medium hover:bg-gray-50">
                  Configure
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-yellow-50 rounded-lg">
            <BellIcon className="h-6 w-6 text-yellow-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">Notifications</h3>
            <p className="text-sm text-gray-500 mt-1">
              Configure email and webhook notifications.
            </p>

            <div className="mt-4 space-y-4">
              {[
                { key: 'quotaWarning', label: 'Quota Warning', desc: 'Get notified when usage reaches 80%' },
                { key: 'usageReport', label: 'Weekly Usage Report', desc: 'Receive weekly usage summary' },
                { key: 'securityAlerts', label: 'Security Alerts', desc: 'Get notified of suspicious activity' },
              ].map((item) => (
                <div key={item.key} className="flex items-center justify-between py-3 border-b border-gray-100 last:border-0">
                  <div>
                    <div className="font-medium text-gray-900">{item.label}</div>
                    <div className="text-sm text-gray-500">{item.desc}</div>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      className="sr-only peer"
                      checked={notifications[item.key as keyof typeof notifications]}
                      onChange={(e) => setNotifications({
                        ...notifications,
                        [item.key]: e.target.checked,
                      })}
                    />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary-600"></div>
                  </label>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Webhooks */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-purple-50 rounded-lg">
            <GlobeAltIcon className="h-6 w-6 text-purple-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-gray-900">Webhooks</h3>
            <p className="text-sm text-gray-500 mt-1">
              Configure webhook endpoints for real-time events.
            </p>

            <div className="mt-4">
              <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                <p className="text-sm text-gray-600">
                  No webhooks configured. Add a webhook to receive real-time notifications about usage events, billing changes, and more.
                </p>
                <button className="mt-3 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors text-sm">
                  Add Webhook
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Danger Zone */}
      <div className="bg-white rounded-xl shadow-sm border border-red-200 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 bg-red-50 rounded-lg">
            <TrashIcon className="h-6 w-6 text-red-600" />
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-red-900">Danger Zone</h3>
            <p className="text-sm text-red-600 mt-1">
              Irreversible and destructive actions.
            </p>

            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between p-4 border border-red-200 rounded-lg">
                <div>
                  <div className="font-medium text-gray-900">Delete Organization</div>
                  <div className="text-sm text-gray-500">Permanently delete your organization and all data</div>
                </div>
                <button className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors">
                  Delete
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
