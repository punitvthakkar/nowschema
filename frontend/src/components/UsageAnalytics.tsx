'use client'

import { useState } from 'react'
import {
  ArrowTrendingUpIcon,
  ArrowTrendingDownIcon,
  CalendarIcon,
} from '@heroicons/react/24/outline'

// Mock data for usage
const mockUsageData = {
  currentMonth: {
    queries: 12847,
    limit: 100000,
    cacheHitRate: 0.67,
    avgLatency: 142,
    requests: 8234,
  },
  previousMonth: {
    queries: 10250,
    limit: 100000,
    cacheHitRate: 0.58,
    avgLatency: 168,
    requests: 6789,
  },
  dailyUsage: [
    { date: 'Jan 14', queries: 420, cacheHits: 280 },
    { date: 'Jan 15', queries: 380, cacheHits: 250 },
    { date: 'Jan 16', queries: 510, cacheHits: 340 },
    { date: 'Jan 17', queries: 650, cacheHits: 450 },
    { date: 'Jan 18', queries: 480, cacheHits: 320 },
    { date: 'Jan 19', queries: 290, cacheHits: 200 },
    { date: 'Jan 20', queries: 560, cacheHits: 380 },
  ],
  byEndpoint: [
    { endpoint: '/search-get', queries: 6500, percentage: 50.6 },
    { endpoint: '/search-post', queries: 3200, percentage: 24.9 },
    { endpoint: '/batch-search', queries: 2847, percentage: 22.2 },
    { endpoint: '/stats', queries: 300, percentage: 2.3 },
  ],
}

export default function UsageAnalytics() {
  const [period, setPeriod] = useState<'7d' | '30d' | '90d'>('30d')

  const usage = mockUsageData.currentMonth
  const prevUsage = mockUsageData.previousMonth

  const queryChange = ((usage.queries - prevUsage.queries) / prevUsage.queries) * 100
  const latencyChange = ((usage.avgLatency - prevUsage.avgLatency) / prevUsage.avgLatency) * 100
  const cacheChange = ((usage.cacheHitRate - prevUsage.cacheHitRate) / prevUsage.cacheHitRate) * 100

  const quotaPercentage = (usage.queries / usage.limit) * 100

  return (
    <div className="space-y-6">
      {/* Period Selector */}
      <div className="flex items-center justify-between">
        <p className="text-gray-500">
          Monitor your API usage and performance metrics.
        </p>
        <div className="flex items-center gap-2 bg-gray-100 rounded-lg p-1">
          {(['7d', '30d', '90d'] as const).map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${
                period === p
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {p === '7d' ? '7 Days' : p === '30d' ? '30 Days' : '90 Days'}
            </button>
          ))}
        </div>
      </div>

      {/* Quota Progress */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Monthly Quota</h3>
          <span className="text-sm text-gray-500">
            Resets on Feb 1, 2024
          </span>
        </div>
        <div className="space-y-2">
          <div className="flex items-end justify-between">
            <span className="text-3xl font-bold text-gray-900">
              {usage.queries.toLocaleString()}
            </span>
            <span className="text-gray-500">
              of {usage.limit.toLocaleString()} queries
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className={`h-3 rounded-full transition-all ${
                quotaPercentage > 90
                  ? 'bg-red-500'
                  : quotaPercentage > 70
                  ? 'bg-yellow-500'
                  : 'bg-green-500'
              }`}
              style={{ width: `${Math.min(quotaPercentage, 100)}%` }}
            />
          </div>
          <div className="text-sm text-gray-500">
            {quotaPercentage.toFixed(1)}% used • {(usage.limit - usage.queries).toLocaleString()} remaining
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Total Queries */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Total Queries</span>
            <span className={`flex items-center gap-1 text-sm font-medium ${
              queryChange >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {queryChange >= 0 ? (
                <ArrowTrendingUpIcon className="h-4 w-4" />
              ) : (
                <ArrowTrendingDownIcon className="h-4 w-4" />
              )}
              {Math.abs(queryChange).toFixed(1)}%
            </span>
          </div>
          <span className="text-2xl font-bold text-gray-900">
            {usage.queries.toLocaleString()}
          </span>
          <span className="text-sm text-gray-500 block mt-1">
            vs {prevUsage.queries.toLocaleString()} last month
          </span>
        </div>

        {/* Cache Hit Rate */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Cache Hit Rate</span>
            <span className={`flex items-center gap-1 text-sm font-medium ${
              cacheChange >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {cacheChange >= 0 ? (
                <ArrowTrendingUpIcon className="h-4 w-4" />
              ) : (
                <ArrowTrendingDownIcon className="h-4 w-4" />
              )}
              {Math.abs(cacheChange).toFixed(1)}%
            </span>
          </div>
          <span className="text-2xl font-bold text-gray-900">
            {(usage.cacheHitRate * 100).toFixed(1)}%
          </span>
          <span className="text-sm text-gray-500 block mt-1">
            vs {(prevUsage.cacheHitRate * 100).toFixed(1)}% last month
          </span>
        </div>

        {/* Avg Latency */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-500">Avg Latency</span>
            <span className={`flex items-center gap-1 text-sm font-medium ${
              latencyChange <= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              {latencyChange <= 0 ? (
                <ArrowTrendingDownIcon className="h-4 w-4" />
              ) : (
                <ArrowTrendingUpIcon className="h-4 w-4" />
              )}
              {Math.abs(latencyChange).toFixed(1)}%
            </span>
          </div>
          <span className="text-2xl font-bold text-gray-900">
            {usage.avgLatency}ms
          </span>
          <span className="text-sm text-gray-500 block mt-1">
            vs {prevUsage.avgLatency}ms last month
          </span>
        </div>
      </div>

      {/* Usage by Endpoint */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Usage by Endpoint</h3>
        <div className="space-y-4">
          {mockUsageData.byEndpoint.map((endpoint) => (
            <div key={endpoint.endpoint}>
              <div className="flex items-center justify-between mb-1">
                <code className="text-sm font-mono text-gray-700">{endpoint.endpoint}</code>
                <span className="text-sm text-gray-500">
                  {endpoint.queries.toLocaleString()} ({endpoint.percentage}%)
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="h-2 rounded-full bg-primary-500"
                  style={{ width: `${endpoint.percentage}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Daily Usage Chart Placeholder */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Daily Usage</h3>
        <div className="h-64 flex items-end justify-between gap-2">
          {mockUsageData.dailyUsage.map((day, i) => (
            <div key={i} className="flex-1 flex flex-col items-center">
              <div className="w-full flex flex-col gap-1">
                <div
                  className="w-full bg-primary-500 rounded-t"
                  style={{ height: `${(day.queries / 700) * 200}px` }}
                  title={`${day.queries} queries`}
                />
                <div
                  className="w-full bg-green-400 rounded-b"
                  style={{ height: `${(day.cacheHits / 700) * 200}px` }}
                  title={`${day.cacheHits} cache hits`}
                />
              </div>
              <span className="text-xs text-gray-500 mt-2">{day.date.split(' ')[1]}</span>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-center gap-6 mt-4">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-primary-500 rounded"></span>
            <span className="text-sm text-gray-600">Total Queries</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 bg-green-400 rounded"></span>
            <span className="text-sm text-gray-600">Cache Hits</span>
          </div>
        </div>
      </div>
    </div>
  )
}
