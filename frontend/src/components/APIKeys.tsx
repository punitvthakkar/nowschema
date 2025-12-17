'use client'

import { useState } from 'react'
import {
  PlusIcon,
  TrashIcon,
  ClipboardDocumentIcon,
  CheckIcon,
  EyeIcon,
  EyeSlashIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

interface APIKey {
  id: string
  name: string
  prefix: string
  scopes: string[]
  isActive: boolean
  createdAt: string
  lastUsedAt: string | null
}

// Mock data - replace with actual API calls
const mockKeys: APIKey[] = [
  {
    id: '1',
    name: 'Production API Key',
    prefix: 'uc_live_abc1',
    scopes: ['search', 'batch'],
    isActive: true,
    createdAt: '2024-01-15T10:00:00Z',
    lastUsedAt: '2024-01-20T15:30:00Z',
  },
  {
    id: '2',
    name: 'Development Key',
    prefix: 'uc_test_xyz9',
    scopes: ['search'],
    isActive: true,
    createdAt: '2024-01-10T08:00:00Z',
    lastUsedAt: '2024-01-18T12:00:00Z',
  },
  {
    id: '3',
    name: 'Excel Plugin',
    prefix: 'uc_live_def2',
    scopes: ['search', 'batch'],
    isActive: false,
    createdAt: '2024-01-05T14:00:00Z',
    lastUsedAt: null,
  },
]

export default function APIKeys() {
  const [keys, setKeys] = useState<APIKey[]>(mockKeys)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [newKey, setNewKey] = useState<string | null>(null)
  const [copied, setCopied] = useState<string | null>(null)

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(id)
    toast.success('Copied to clipboard')
    setTimeout(() => setCopied(null), 2000)
  }

  const handleCreate = () => {
    // Simulate key creation
    const generatedKey = `uc_live_${Math.random().toString(36).substring(2, 15)}`
    setNewKey(generatedKey)

    const newKeyObj: APIKey = {
      id: String(Date.now()),
      name: 'New API Key',
      prefix: generatedKey.substring(0, 12),
      scopes: ['search'],
      isActive: true,
      createdAt: new Date().toISOString(),
      lastUsedAt: null,
    }
    setKeys([newKeyObj, ...keys])
    toast.success('API key created!')
  }

  const handleRevoke = (id: string) => {
    setKeys(keys.map(k => k.id === id ? { ...k, isActive: false } : k))
    toast.success('API key revoked')
  }

  const formatDate = (date: string | null) => {
    if (!date) return 'Never'
    return new Date(date).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <p className="text-gray-500">
            Manage API keys for your applications. Each key can have specific scopes and rate limits.
          </p>
        </div>
        <button
          onClick={handleCreate}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          <PlusIcon className="h-5 w-5" />
          Create Key
        </button>
      </div>

      {/* New Key Alert */}
      {newKey && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-start justify-between">
            <div>
              <h4 className="font-medium text-green-800">New API Key Created</h4>
              <p className="text-sm text-green-700 mt-1">
                Make sure to copy your API key now. You won&apos;t be able to see it again!
              </p>
              <div className="mt-3 flex items-center gap-3">
                <code className="bg-green-100 px-3 py-1.5 rounded font-mono text-sm text-green-900">
                  {newKey}
                </code>
                <button
                  onClick={() => handleCopy(newKey, 'new')}
                  className="p-2 text-green-600 hover:text-green-800 hover:bg-green-100 rounded"
                >
                  {copied === 'new' ? (
                    <CheckIcon className="h-5 w-5" />
                  ) : (
                    <ClipboardDocumentIcon className="h-5 w-5" />
                  )}
                </button>
              </div>
            </div>
            <button
              onClick={() => setNewKey(null)}
              className="text-green-600 hover:text-green-800"
            >
              Dismiss
            </button>
          </div>
        </div>
      )}

      {/* Keys Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Name
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Key
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Scopes
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Last Used
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Created
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {keys.map((key) => (
              <tr key={key.id} className={!key.isActive ? 'bg-gray-50' : ''}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="font-medium text-gray-900">{key.name}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <code className="text-sm text-gray-600 bg-gray-100 px-2 py-1 rounded">
                      {key.prefix}...
                    </code>
                    <button
                      onClick={() => handleCopy(key.prefix + '...', key.id)}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      {copied === key.id ? (
                        <CheckIcon className="h-4 w-4 text-green-500" />
                      ) : (
                        <ClipboardDocumentIcon className="h-4 w-4" />
                      )}
                    </button>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex gap-1">
                    {key.scopes.map((scope) => (
                      <span
                        key={scope}
                        className="px-2 py-0.5 text-xs font-medium bg-primary-50 text-primary-700 rounded"
                      >
                        {scope}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  {key.isActive ? (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-green-50 text-green-700 rounded">
                      <span className="w-1.5 h-1.5 bg-green-500 rounded-full"></span>
                      Active
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-600 rounded">
                      <span className="w-1.5 h-1.5 bg-gray-400 rounded-full"></span>
                      Revoked
                    </span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(key.lastUsedAt)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {formatDate(key.createdAt)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right">
                  {key.isActive && (
                    <button
                      onClick={() => handleRevoke(key.id)}
                      className="text-red-600 hover:text-red-800 p-2 hover:bg-red-50 rounded"
                      title="Revoke key"
                    >
                      <TrashIcon className="h-5 w-5" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Usage Info */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h4 className="font-medium text-blue-800">API Key Best Practices</h4>
        <ul className="mt-2 text-sm text-blue-700 space-y-1">
          <li>• Use separate keys for development and production environments</li>
          <li>• Rotate keys regularly for security</li>
          <li>• Never expose keys in client-side code or version control</li>
          <li>• Use the minimum required scopes for each key</li>
        </ul>
      </div>
    </div>
  )
}
