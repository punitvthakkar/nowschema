'use client'

import { useState } from 'react'
import {
  CheckIcon,
  XMarkIcon,
  CreditCardIcon,
  DocumentTextIcon,
} from '@heroicons/react/24/outline'
import toast from 'react-hot-toast'

const plans = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    description: 'For testing and small projects',
    features: [
      { name: '1,000 queries/month', included: true },
      { name: '10 requests/minute', included: true },
      { name: 'Single search', included: true },
      { name: 'Batch search', included: false },
      { name: 'Priority support', included: false },
      { name: 'SSO', included: false },
      { name: 'SLA', included: false },
    ],
  },
  {
    id: 'starter',
    name: 'Starter',
    price: 29,
    description: 'For growing teams',
    features: [
      { name: '10,000 queries/month', included: true },
      { name: '60 requests/minute', included: true },
      { name: 'Single search', included: true },
      { name: 'Batch search', included: true },
      { name: 'Email support', included: true },
      { name: 'SSO', included: false },
      { name: 'SLA', included: false },
    ],
    popular: true,
  },
  {
    id: 'professional',
    name: 'Professional',
    price: 99,
    description: 'For production workloads',
    features: [
      { name: '100,000 queries/month', included: true },
      { name: '300 requests/minute', included: true },
      { name: 'Single search', included: true },
      { name: 'Batch search', included: true },
      { name: 'Priority support', included: true },
      { name: 'Analytics dashboard', included: true },
      { name: 'SLA', included: false },
    ],
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 499,
    description: 'For large organizations',
    features: [
      { name: '1,000,000 queries/month', included: true },
      { name: '1,000 requests/minute', included: true },
      { name: 'Single search', included: true },
      { name: 'Batch search', included: true },
      { name: 'Dedicated support', included: true },
      { name: 'SSO (SAML/OIDC)', included: true },
      { name: '99.9% SLA', included: true },
    ],
  },
]

const mockInvoices = [
  { id: '1', date: 'Jan 1, 2024', amount: 99, status: 'paid' },
  { id: '2', date: 'Dec 1, 2023', amount: 99, status: 'paid' },
  { id: '3', date: 'Nov 1, 2023', amount: 99, status: 'paid' },
]

export default function Billing() {
  const [currentPlan, setCurrentPlan] = useState('professional')
  const [loading, setLoading] = useState<string | null>(null)

  const handleUpgrade = async (planId: string) => {
    if (planId === currentPlan) return

    setLoading(planId)
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    setLoading(null)

    if (planId === 'enterprise') {
      toast.success('Contact sales for Enterprise plan')
    } else {
      setCurrentPlan(planId)
      toast.success(`Switched to ${plans.find(p => p.id === planId)?.name} plan`)
    }
  }

  return (
    <div className="space-y-8">
      {/* Current Plan */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Current Plan</h3>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-gray-900">
                {plans.find(p => p.id === currentPlan)?.name}
              </span>
              <span className="px-2 py-0.5 bg-green-100 text-green-700 text-sm font-medium rounded">
                Active
              </span>
            </div>
            <p className="text-gray-500 mt-1">
              ${plans.find(p => p.id === currentPlan)?.price}/month • Renews on Feb 1, 2024
            </p>
          </div>
          <button className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50">
            Manage Subscription
          </button>
        </div>
      </div>

      {/* Plans Grid */}
      <div>
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Available Plans</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {plans.map((plan) => (
            <div
              key={plan.id}
              className={`bg-white rounded-xl shadow-sm border-2 p-6 ${
                plan.id === currentPlan
                  ? 'border-primary-500'
                  : plan.popular
                  ? 'border-yellow-400'
                  : 'border-gray-200'
              }`}
            >
              {plan.popular && (
                <span className="inline-block px-2 py-0.5 bg-yellow-100 text-yellow-800 text-xs font-medium rounded mb-3">
                  Most Popular
                </span>
              )}
              <h4 className="text-lg font-semibold text-gray-900">{plan.name}</h4>
              <p className="text-sm text-gray-500 mt-1">{plan.description}</p>

              <div className="mt-4">
                <span className="text-3xl font-bold text-gray-900">${plan.price}</span>
                <span className="text-gray-500">/month</span>
              </div>

              <ul className="mt-6 space-y-3">
                {plan.features.map((feature, i) => (
                  <li key={i} className="flex items-center gap-2">
                    {feature.included ? (
                      <CheckIcon className="h-5 w-5 text-green-500" />
                    ) : (
                      <XMarkIcon className="h-5 w-5 text-gray-300" />
                    )}
                    <span className={feature.included ? 'text-gray-700' : 'text-gray-400'}>
                      {feature.name}
                    </span>
                  </li>
                ))}
              </ul>

              <button
                onClick={() => handleUpgrade(plan.id)}
                disabled={plan.id === currentPlan || loading !== null}
                className={`w-full mt-6 px-4 py-2 rounded-lg font-medium transition-colors ${
                  plan.id === currentPlan
                    ? 'bg-gray-100 text-gray-500 cursor-default'
                    : 'bg-primary-600 text-white hover:bg-primary-700'
                } disabled:opacity-50`}
              >
                {loading === plan.id ? (
                  <span className="flex items-center justify-center gap-2">
                    <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Processing...
                  </span>
                ) : plan.id === currentPlan ? (
                  'Current Plan'
                ) : plan.id === 'enterprise' ? (
                  'Contact Sales'
                ) : (
                  'Upgrade'
                )}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Payment Method */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Payment Method</h3>
        <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
          <div className="flex items-center gap-4">
            <div className="w-12 h-8 bg-gradient-to-r from-blue-600 to-blue-400 rounded flex items-center justify-center">
              <CreditCardIcon className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="font-medium text-gray-900">•••• •••• •••• 4242</div>
              <div className="text-sm text-gray-500">Expires 12/2025</div>
            </div>
          </div>
          <button className="text-primary-600 hover:text-primary-700 text-sm font-medium">
            Update
          </button>
        </div>
      </div>

      {/* Invoices */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Billing History</h3>
        <table className="min-w-full">
          <thead>
            <tr className="border-b border-gray-200">
              <th className="text-left py-3 text-sm font-medium text-gray-500">Date</th>
              <th className="text-left py-3 text-sm font-medium text-gray-500">Amount</th>
              <th className="text-left py-3 text-sm font-medium text-gray-500">Status</th>
              <th className="text-right py-3 text-sm font-medium text-gray-500">Invoice</th>
            </tr>
          </thead>
          <tbody>
            {mockInvoices.map((invoice) => (
              <tr key={invoice.id} className="border-b border-gray-100 last:border-0">
                <td className="py-3 text-sm text-gray-900">{invoice.date}</td>
                <td className="py-3 text-sm text-gray-900">${invoice.amount}.00</td>
                <td className="py-3">
                  <span className="px-2 py-0.5 bg-green-100 text-green-700 text-xs font-medium rounded capitalize">
                    {invoice.status}
                  </span>
                </td>
                <td className="py-3 text-right">
                  <button className="text-primary-600 hover:text-primary-700 text-sm font-medium inline-flex items-center gap-1">
                    <DocumentTextIcon className="h-4 w-4" />
                    Download
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
