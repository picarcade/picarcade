'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { supabase } from '../lib/supabase'
import type { User, Session } from '@supabase/supabase-js'

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<{ error: Error | null }>
  signUp: (email: string, password: string, metadata?: Record<string, unknown>) => Promise<{ error: Error | null }>
  signInWithMagicLink: (email: string) => Promise<{ error: Error | null }>
  signOut: () => Promise<void>
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Get initial session from Supabase
    const getInitialSession = async () => {
      try {
        const { data: { session }, error } = await supabase.auth.getSession()
        if (error) {
          console.error('Error getting session:', error)
        } else if (session) {
          setSession(session)
          setUser(session.user)
          // Store access token for API calls
          if (session.access_token) {
            localStorage.setItem('access_token', session.access_token)
            console.log('🔑 Initial access token stored for API calls')
          }
        }
      } catch (error) {
        console.error('Error getting initial session:', error)
      } finally {
        setLoading(false)
      }
    }

    getInitialSession()

    // Listen for changes in auth state
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('🔔 Auth state change:', { 
        event, 
        hasSession: !!session, 
        userEmail: session?.user?.email,
        sessionId: session?.access_token?.substring(0, 10) + '...' || 'none'
      })
      
      setLoading(false)
      setSession(session)
      setUser(session?.user ?? null)

      // Store/clear access token for API calls while preserving user ID behavior
      if (session?.access_token) {
        localStorage.setItem('access_token', session.access_token)
        console.log('🔑 Access token stored for API calls')
      } else {
        localStorage.removeItem('access_token')
        console.log('🔑 Access token cleared')
      }

      if (event === 'SIGNED_IN' && session) {
        console.log('✅ User signed in via AuthProvider:', session.user.email)
      }
      if (event === 'SIGNED_OUT') {
        console.log('🚪 User signed out via AuthProvider')
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const signIn = async (email: string, password: string) => {
    try {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      
      if (error) {
        return { error: error as Error }
      }
      
      return { error: null }
    } catch (error) {
      console.error('Sign in error:', error)
      return { error: error as Error }
    }
  }

  const signUp = async (email: string, password: string, metadata?: Record<string, unknown>) => {
    try {
      const { error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: metadata,
        },
      })
      
      if (error) {
        return { error: error as Error }
      }
      
      return { error: null }
    } catch (error) {
      console.error('Sign up error:', error)
      return { error: error as Error }
    }
  }

  const signInWithMagicLink = async (email: string) => {
    try {
      const { error } = await supabase.auth.signInWithOtp({
        email,
        options: {
          emailRedirectTo: `${window.location.origin}/auth/callback`, // Adjust redirect URL as needed
        },
      })

      if (error) {
        return { error: error as Error }
      }

      return { error: null }
    } catch (error) {
      console.error('Magic link sign in error:', error)
      return { error: error as Error }
    }
  }

  const signOut = async () => {
    try {
      console.log('🚪 Starting sign out process...')
      
      // Try to sign out through Supabase first
      const { error } = await supabase.auth.signOut()
      
      if (error) {
        console.warn('Supabase sign out error (continuing with local cleanup):', error)
        
        // If Supabase signOut fails, force local session cleanup
        console.log('🧹 Forcing local session cleanup...')
        
        // Clear local state
        setUser(null)
        setSession(null)
        
        // Clear any localStorage items related to auth
        try {
          localStorage.removeItem('access_token') // Clear our stored access token
          localStorage.removeItem('sb-izfjglgvaqrqaywfniwi-auth-token')
          localStorage.removeItem('supabase.auth.token')
          localStorage.removeItem('auth_session')
          localStorage.removeItem('picarcade_user_id') // Clear user ID as well
        } catch (storageError) {
          console.warn('Error clearing localStorage:', storageError)
        }
        
        console.log('✅ Local session cleanup completed')
      } else {
        console.log('✅ Supabase sign out successful')
      }
    } catch (error) {
      console.error('Critical sign out error:', error)
      
      // Force cleanup even on critical errors
      setUser(null)
      setSession(null)
      
      // Clear localStorage as fallback
      try {
        localStorage.removeItem('access_token') // Clear our stored access token
        localStorage.removeItem('sb-izfjglgvaqrqaywfniwi-auth-token')
        localStorage.removeItem('supabase.auth.token')
        localStorage.removeItem('auth_session')
        localStorage.removeItem('picarcade_user_id') // Clear user ID as well
      } catch (storageError) {
        console.warn('Error clearing localStorage during fallback:', storageError)
      }
    }
  }

  const refreshSession = async () => {
    try {
      const { error } = await supabase.auth.refreshSession()
      if (error) {
        console.error('Refresh session error:', error)
      }
    } catch (error) {
      console.error('Refresh session error:', error)
    }
  }

  const value = {
    user,
    session,
    loading,
    signIn,
    signUp,
    signInWithMagicLink,
    signOut,
    refreshSession
  }

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
} 