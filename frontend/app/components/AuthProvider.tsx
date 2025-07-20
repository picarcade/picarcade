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
      setLoading(false)
      setSession(session)
      setUser(session?.user ?? null)

      if (event === 'SIGNED_IN' && session) {
        console.log('User signed in:', session.user.email)
      }
      if (event === 'SIGNED_OUT') {
        console.log('User signed out')
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

  const signOut = async () => {
    try {
      const { error } = await supabase.auth.signOut()
      if (error) {
        console.error('Sign out error:', error)
      }
    } catch (error) {
      console.error('Sign out error:', error)
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