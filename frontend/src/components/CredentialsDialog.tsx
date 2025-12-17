'use client'

import { Fragment, useState } from 'react'
import { Dialog, Transition, Tab } from '@headlessui/react'
import { XMarkIcon, ClipboardDocumentIcon, CheckIcon } from '@heroicons/react/24/outline'
import { useConfigStore, ServiceCredentials } from '@/lib/store'
import toast from 'react-hot-toast'
import clsx from 'clsx'

interface Props {
  open: boolean
  onClose: () => void
}

interface CredentialField {
  key: keyof ServiceCredentials
  label: string
  placeholder: string
  type?: 'text' | 'password'
  required?: boolean
  helpText?: string
}

const credentialGroups: {
  id: string
  name: string
  icon: string
  description: string
  fields: CredentialField[]
}[] = [
  {
    id: 'modal',
    name: 'Modal',
    icon: '🚀',
    description: 'API hosting platform',
    fields: [
      { key: 'modalTokenId', label: 'Token ID', placeholder: 'ak-...', helpText: 'From modal.com dashboard' },
      { key: 'modalTokenSecret', label: 'Token Secret', placeholder: 'as-...', type: 'password' },
    ],
  },
  {
    id: 'supabase',
    name: 'Supabase',
    icon: '⚡',
    description: 'Database & Authentication',
    fields: [
      { key: 'supabaseUrl', label: 'Project URL', placeholder: 'https://xxx.supabase.co', required: true },
      { key: 'supabaseAnonKey', label: 'Anon Key', placeholder: 'eyJ...', type: 'password' },
      { key: 'supabaseServiceKey', label: 'Service Key', placeholder: 'eyJ...', type: 'password', required: true, helpText: 'Required for backend operations' },
    ],
  },
  {
    id: 'upstash',
    name: 'Upstash Redis',
    icon: '🔴',
    description: 'Caching & Rate Limiting',
    fields: [
      { key: 'upstashRedisUrl', label: 'REST URL', placeholder: 'https://xxx.upstash.io', required: true },
      { key: 'upstashRedisToken', label: 'REST Token', placeholder: 'AX...', type: 'password', required: true },
    ],
  },
  {
    id: 'stripe',
    name: 'Stripe',
    icon: '💳',
    description: 'Payments & Subscriptions',
    fields: [
      { key: 'stripeSecretKey', label: 'Secret Key', placeholder: 'sk_live_...', type: 'password' },
      { key: 'stripeWebhookSecret', label: 'Webhook Secret', placeholder: 'whsec_...', type: 'password' },
      { key: 'stripePriceIdStarter', label: 'Starter Price ID', placeholder: 'price_...' },
      { key: 'stripePriceIdProfessional', label: 'Professional Price ID', placeholder: 'price_...' },
      { key: 'stripePriceIdEnterprise', label: 'Enterprise Price ID', placeholder: 'price_...' },
    ],
  },
  {
    id: 'workos',
    name: 'WorkOS',
    icon: '🔐',
    description: 'Enterprise SSO',
    fields: [
      { key: 'workosApiKey', label: 'API Key', placeholder: 'sk_...', type: 'password' },
      { key: 'workosClientId', label: 'Client ID', placeholder: 'client_...' },
    ],
  },
  {
    id: 'grafana',
    name: 'Grafana Cloud',
    icon: '📊',
    description: 'Observability & Metrics',
    fields: [
      { key: 'grafanaApiKey', label: 'API Key', placeholder: 'glc_...', type: 'password' },
      { key: 'grafanaEndpoint', label: 'Endpoint', placeholder: 'https://xxx.grafana.net' },
    ],
  },
  {
    id: 'app',
    name: 'App Settings',
    icon: '⚙️',
    description: 'Application configuration',
    fields: [
      { key: 'apiBaseUrl', label: 'API Base URL', placeholder: 'https://...modal.run' },
      { key: 'jwtSecret', label: 'JWT Secret', placeholder: 'Auto-generated', type: 'password', helpText: 'Leave empty to auto-generate' },
    ],
  },
]

export default function CredentialsDialog({ open, onClose }: Props) {
  const { credentials, setCredentials, exportAsEnv, exportAsModalSecrets } = useConfigStore()
  const [localCreds, setLocalCreds] = useState<ServiceCredentials>(credentials)
  const [copied, setCopied] = useState<string | null>(null)

  const handleChange = (key: keyof ServiceCredentials, value: string) => {
    setLocalCreds(prev => ({ ...prev, [key]: value }))
  }

  const handleSave = () => {
    // Generate JWT secret if empty
    if (!localCreds.jwtSecret) {
      const array = new Uint8Array(32)
      crypto.getRandomValues(array)
      localCreds.jwtSecret = Array.from(array, b => b.toString(16).padStart(2, '0')).join('')
    }

    setCredentials(localCreds)
    toast.success('Credentials saved successfully!')
    onClose()
  }

  const handleCopy = async (text: string, label: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(label)
    toast.success(`${label} copied to clipboard`)
    setTimeout(() => setCopied(null), 2000)
  }

  const handleExportEnv = () => {
    setCredentials(localCreds) // Save first
    handleCopy(exportAsEnv(), 'Environment variables')
  }

  const handleExportModal = () => {
    setCredentials(localCreds) // Save first
    handleCopy(exportAsModalSecrets(), 'Modal command')
  }

  return (
    <Transition appear show={open} as={Fragment}>
      <Dialog as="div" className="relative z-50" onClose={onClose}>
        <Transition.Child
          as={Fragment}
          enter="ease-out duration-300"
          enterFrom="opacity-0"
          enterTo="opacity-100"
          leave="ease-in duration-200"
          leaveFrom="opacity-100"
          leaveTo="opacity-0"
        >
          <div className="fixed inset-0 bg-black/50" />
        </Transition.Child>

        <div className="fixed inset-0 overflow-y-auto">
          <div className="flex min-h-full items-center justify-center p-4">
            <Transition.Child
              as={Fragment}
              enter="ease-out duration-300"
              enterFrom="opacity-0 scale-95"
              enterTo="opacity-100 scale-100"
              leave="ease-in duration-200"
              leaveFrom="opacity-100 scale-100"
              leaveTo="opacity-0 scale-95"
            >
              <Dialog.Panel className="w-full max-w-4xl transform overflow-hidden rounded-2xl bg-white shadow-xl transition-all">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
                  <div>
                    <Dialog.Title className="text-xl font-semibold text-gray-900">
                      🔑 Master Credentials Configuration
                    </Dialog.Title>
                    <p className="mt-1 text-sm text-gray-500">
                      Configure all service credentials in one place. These are stored locally and used to generate deployment commands.
                    </p>
                  </div>
                  <button
                    onClick={onClose}
                    className="rounded-lg p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100"
                  >
                    <XMarkIcon className="h-5 w-5" />
                  </button>
                </div>

                {/* Content */}
                <div className="max-h-[60vh] overflow-y-auto">
                  <Tab.Group>
                    <Tab.List className="flex space-x-1 bg-gray-100 p-1 mx-6 mt-4 rounded-lg">
                      {credentialGroups.map((group) => (
                        <Tab
                          key={group.id}
                          className={({ selected }) =>
                            clsx(
                              'flex-1 rounded-lg py-2 px-3 text-sm font-medium transition-colors',
                              selected
                                ? 'bg-white text-primary-700 shadow'
                                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                            )
                          }
                        >
                          <span className="mr-1">{group.icon}</span>
                          <span className="hidden sm:inline">{group.name}</span>
                        </Tab>
                      ))}
                    </Tab.List>

                    <Tab.Panels className="p-6">
                      {credentialGroups.map((group) => (
                        <Tab.Panel key={group.id}>
                          <div className="mb-4">
                            <h3 className="text-lg font-medium text-gray-900">
                              {group.icon} {group.name}
                            </h3>
                            <p className="text-sm text-gray-500">{group.description}</p>
                          </div>

                          <div className="space-y-4">
                            {group.fields.map((field) => (
                              <div key={field.key}>
                                <label className="block text-sm font-medium text-gray-700 mb-1">
                                  {field.label}
                                  {field.required && (
                                    <span className="text-red-500 ml-1">*</span>
                                  )}
                                </label>
                                <input
                                  type={field.type || 'text'}
                                  value={localCreds[field.key]}
                                  onChange={(e) => handleChange(field.key, e.target.value)}
                                  placeholder={field.placeholder}
                                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 text-sm"
                                />
                                {field.helpText && (
                                  <p className="mt-1 text-xs text-gray-500">{field.helpText}</p>
                                )}
                              </div>
                            ))}
                          </div>
                        </Tab.Panel>
                      ))}
                    </Tab.Panels>
                  </Tab.Group>
                </div>

                {/* Export Section */}
                <div className="px-6 py-4 bg-gray-50 border-t border-gray-200">
                  <h4 className="text-sm font-medium text-gray-900 mb-3">Export Credentials</h4>
                  <div className="flex flex-wrap gap-3">
                    <button
                      onClick={handleExportEnv}
                      className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                    >
                      {copied === 'Environment variables' ? (
                        <CheckIcon className="h-4 w-4 mr-2 text-green-500" />
                      ) : (
                        <ClipboardDocumentIcon className="h-4 w-4 mr-2" />
                      )}
                      Copy as .env
                    </button>
                    <button
                      onClick={handleExportModal}
                      className="inline-flex items-center px-4 py-2 border border-gray-300 rounded-lg text-sm font-medium text-gray-700 bg-white hover:bg-gray-50"
                    >
                      {copied === 'Modal command' ? (
                        <CheckIcon className="h-4 w-4 mr-2 text-green-500" />
                      ) : (
                        <ClipboardDocumentIcon className="h-4 w-4 mr-2" />
                      )}
                      Copy Modal Secret Command
                    </button>
                  </div>
                  <p className="mt-2 text-xs text-gray-500">
                    Run the Modal command to create secrets, then deploy with: <code className="bg-gray-200 px-1 rounded">modal deploy modal_api.py</code>
                  </p>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200">
                  <button
                    onClick={onClose}
                    className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    className="px-4 py-2 bg-primary-600 text-white text-sm font-medium rounded-lg hover:bg-primary-700 transition-colors"
                  >
                    Save Configuration
                  </button>
                </div>
              </Dialog.Panel>
            </Transition.Child>
          </div>
        </div>
      </Dialog>
    </Transition>
  )
}
