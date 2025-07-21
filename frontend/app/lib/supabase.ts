import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://izfjglgvaqrqaywfniwi.supabase.co'
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6ZmpnbGd2YXFycWF5d2ZuaXdpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwNTcwNzEsImV4cCI6MjA2ODYzMzA3MX0.IRI6lerdkg5CAVUNmsSqLN9DT983YNxH8orRB5fllfQ'

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    flowType: 'pkce',
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true // Let Supabase automatically handle OAuth callbacks
  }
})

// Auth helper functions
export const authHelpers = {
  // Sign up new user
  async signUp(email: string, password: string, metadata?: Record<string, unknown>) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: metadata
      }
    })
    return { data, error }
  },

  // Sign in existing user
  async signIn(email: string, password: string) {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    })
    return { data, error }
  },

  // Sign out current user
  async signOut() {
    const { error } = await supabase.auth.signOut()
    return { error }
  },

  // Get current session
  async getSession() {
    const { data: { session }, error } = await supabase.auth.getSession()
    return { session, error }
  },

  // Get current user
  async getUser() {
    const { data: { user }, error } = await supabase.auth.getUser()
    return { user, error }
  },

  // Refresh session
  async refreshSession() {
    const { data, error } = await supabase.auth.refreshSession()
    return { data, error }
  },

  // Listen to auth state changes
  onAuthStateChange(callback: (event: string, session: unknown) => void) {
    return supabase.auth.onAuthStateChange(callback)
  }
}

// API helper functions with authentication
export const apiHelpers = {
  // Get authorization header for API calls
  async getAuthHeader(): Promise<Record<string, string>> {
    try {
      console.log('[Supabase Auth] Getting session from Supabase...')
      // Get session from Supabase
      const { data: { session }, error } = await supabase.auth.getSession()
      console.log('[Supabase Auth] Session result:', {
        hasSession: !!session,
        hasAccessToken: !!session?.access_token,
        tokenPreview: session?.access_token ? session.access_token.substring(0, 50) + '...' : 'none',
        error: error?.message,
        userEmail: session?.user?.email
      })
      
      if (!error && session?.access_token) {
        console.log('[Supabase Auth] ✅ Using Supabase OAuth token')
        return {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json'
        }
      }
      
      console.log('[Supabase Auth] No Supabase session, checking localStorage fallback...')
      // Fallback: check localStorage for custom auth session
      const storedSession = localStorage.getItem('auth_session')
      if (storedSession) {
        console.log('[Supabase Auth] Found stored session in localStorage')
        const session = JSON.parse(storedSession)
        if (session?.access_token) {
          console.log('[Supabase Auth] ✅ Using localStorage token')
          return {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          }
        }
      }
      
      console.log('[Supabase Auth] ❌ No authentication token available')
    } catch (error) {
      console.warn('[Supabase Auth] ❌ Failed to get auth token:', error)
    }
    
    return {
      'Content-Type': 'application/json'
    }
  },

  // Make authenticated API call
  async authenticatedFetch(url: string, options: RequestInit = {}) {
    const authHeaders = await this.getAuthHeader()
    
    return fetch(url, {
      ...options,
      headers: {
        ...authHeaders,
        ...(options.headers as Record<string, string> || {})
      }
    })
  }
} 