import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://icgwpkroorulmsfdiuoh.supabase.co'
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImljZ3dwa3Jvb3J1bG1zZmRpdW9oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDkxODkwNjMsImV4cCI6MjA2NDc2NTA2M30.EcFRMaxCCRtS-ynKXZVrKbWdG_LI93zgaxrzW82BTYc'

export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true
  }
})

// Auth helper functions
export const authHelpers = {
  // Sign up new user
  async signUp(email: string, password: string, metadata?: any) {
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
  onAuthStateChange(callback: (event: string, session: any) => void) {
    return supabase.auth.onAuthStateChange(callback)
  }
}

// API helper functions with authentication
export const apiHelpers = {
  // Get authorization header for API calls
  async getAuthHeader(): Promise<Record<string, string>> {
    try {
      // Get session from localStorage (from our custom auth system)
      const storedSession = localStorage.getItem('auth_session')
      if (storedSession) {
        const session = JSON.parse(storedSession)
        if (session?.access_token) {
          return {
            'Authorization': `Bearer ${session.access_token}`,
            'Content-Type': 'application/json'
          }
        }
      }
    } catch (error) {
      console.warn('Failed to get auth token from localStorage:', error)
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