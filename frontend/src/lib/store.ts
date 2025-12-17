import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface ServiceCredentials {
  // Modal
  modalTokenId: string
  modalTokenSecret: string

  // Supabase
  supabaseUrl: string
  supabaseAnonKey: string
  supabaseServiceKey: string

  // Upstash Redis
  upstashRedisUrl: string
  upstashRedisToken: string

  // Stripe
  stripeSecretKey: string
  stripeWebhookSecret: string
  stripePriceIdStarter: string
  stripePriceIdProfessional: string
  stripePriceIdEnterprise: string

  // WorkOS
  workosApiKey: string
  workosClientId: string

  // Grafana
  grafanaApiKey: string
  grafanaEndpoint: string

  // App settings
  apiBaseUrl: string
  jwtSecret: string
}

interface ConfigState {
  credentials: ServiceCredentials
  isConfigured: boolean
  setCredentials: (creds: Partial<ServiceCredentials>) => void
  clearCredentials: () => void
  exportAsEnv: () => string
  exportAsModalSecrets: () => string
}

const defaultCredentials: ServiceCredentials = {
  modalTokenId: '',
  modalTokenSecret: '',
  supabaseUrl: '',
  supabaseAnonKey: '',
  supabaseServiceKey: '',
  upstashRedisUrl: '',
  upstashRedisToken: '',
  stripeSecretKey: '',
  stripeWebhookSecret: '',
  stripePriceIdStarter: '',
  stripePriceIdProfessional: '',
  stripePriceIdEnterprise: '',
  workosApiKey: '',
  workosClientId: '',
  grafanaApiKey: '',
  grafanaEndpoint: '',
  apiBaseUrl: 'https://punitvthakkar--uniclass-api-uniclasssearchservice',
  jwtSecret: '',
}

export const useConfigStore = create<ConfigState>()(
  persist(
    (set, get) => ({
      credentials: defaultCredentials,
      isConfigured: false,

      setCredentials: (creds) => {
        const newCreds = { ...get().credentials, ...creds }
        const isConfigured = Boolean(
          newCreds.supabaseUrl &&
          newCreds.supabaseServiceKey &&
          newCreds.upstashRedisUrl
        )
        set({ credentials: newCreds, isConfigured })
      },

      clearCredentials: () => {
        set({ credentials: defaultCredentials, isConfigured: false })
      },

      exportAsEnv: () => {
        const creds = get().credentials
        return `# Uniclass API Environment Variables
# Generated from Admin Dashboard

# Modal
MODAL_TOKEN_ID=${creds.modalTokenId}
MODAL_TOKEN_SECRET=${creds.modalTokenSecret}

# Supabase
SUPABASE_URL=${creds.supabaseUrl}
SUPABASE_ANON_KEY=${creds.supabaseAnonKey}
SUPABASE_SERVICE_KEY=${creds.supabaseServiceKey}

# Upstash Redis
UPSTASH_REDIS_URL=${creds.upstashRedisUrl}
UPSTASH_REDIS_TOKEN=${creds.upstashRedisToken}

# Stripe
STRIPE_SECRET_KEY=${creds.stripeSecretKey}
STRIPE_WEBHOOK_SECRET=${creds.stripeWebhookSecret}
STRIPE_PRICE_ID_STARTER=${creds.stripePriceIdStarter}
STRIPE_PRICE_ID_PROFESSIONAL=${creds.stripePriceIdProfessional}
STRIPE_PRICE_ID_ENTERPRISE=${creds.stripePriceIdEnterprise}

# WorkOS
WORKOS_API_KEY=${creds.workosApiKey}
WORKOS_CLIENT_ID=${creds.workosClientId}

# Grafana
GRAFANA_API_KEY=${creds.grafanaApiKey}
GRAFANA_ENDPOINT=${creds.grafanaEndpoint}

# App
API_BASE_URL=${creds.apiBaseUrl}
JWT_SECRET=${creds.jwtSecret}
ENVIRONMENT=production
`
      },

      exportAsModalSecrets: () => {
        const creds = get().credentials
        const secrets = {
          SUPABASE_URL: creds.supabaseUrl,
          SUPABASE_ANON_KEY: creds.supabaseAnonKey,
          SUPABASE_SERVICE_KEY: creds.supabaseServiceKey,
          UPSTASH_REDIS_URL: creds.upstashRedisUrl,
          UPSTASH_REDIS_TOKEN: creds.upstashRedisToken,
          STRIPE_SECRET_KEY: creds.stripeSecretKey,
          STRIPE_WEBHOOK_SECRET: creds.stripeWebhookSecret,
          STRIPE_PRICE_ID_STARTER: creds.stripePriceIdStarter,
          STRIPE_PRICE_ID_PROFESSIONAL: creds.stripePriceIdProfessional,
          STRIPE_PRICE_ID_ENTERPRISE: creds.stripePriceIdEnterprise,
          WORKOS_API_KEY: creds.workosApiKey,
          WORKOS_CLIENT_ID: creds.workosClientId,
          GRAFANA_API_KEY: creds.grafanaApiKey,
          GRAFANA_ENDPOINT: creds.grafanaEndpoint,
          JWT_SECRET: creds.jwtSecret,
          ENVIRONMENT: 'production',
        }

        // Generate Modal CLI command
        const args = Object.entries(secrets)
          .filter(([_, v]) => v)
          .map(([k, v]) => `${k}=${v}`)
          .join(' ')

        return `modal secret create uniclass-enterprise-secrets ${args}`
      },
    }),
    {
      name: 'uniclass-config',
    }
  )
)

// API Keys store
interface APIKey {
  id: string
  name: string
  prefix: string
  scopes: string[]
  isActive: boolean
  createdAt: string
  lastUsedAt: string | null
}

interface APIKeysState {
  keys: APIKey[]
  setKeys: (keys: APIKey[]) => void
  addKey: (key: APIKey) => void
  removeKey: (id: string) => void
}

export const useAPIKeysStore = create<APIKeysState>((set) => ({
  keys: [],
  setKeys: (keys) => set({ keys }),
  addKey: (key) => set((state) => ({ keys: [...state.keys, key] })),
  removeKey: (id) => set((state) => ({
    keys: state.keys.filter(k => k.id !== id)
  })),
}))

// Usage stats store
interface UsageStats {
  totalQueries: number
  quotaLimit: number
  quotaRemaining: number
  quotaReset: string
  cacheHitRate: number
}

interface UsageState {
  stats: UsageStats | null
  loading: boolean
  setStats: (stats: UsageStats) => void
  setLoading: (loading: boolean) => void
}

export const useUsageStore = create<UsageState>((set) => ({
  stats: null,
  loading: false,
  setStats: (stats) => set({ stats }),
  setLoading: (loading) => set({ loading }),
}))
