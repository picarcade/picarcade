'use client'

import React, { createContext, useContext, useEffect, useState } from 'react'
import { authAPI } from '../lib/api'

interface User {
  id: string
  email: string
  [key: string]: any
}

interface Session {
  access_token: string
  refresh_token: string
  user: User
  [key: string]: any
}

interface AuthContextType {
  user: User | null
  session: Session | null
  loading: boolean
  signIn: (email: string, password: string) => Promise<{ error: any }>
  signUp: (email: string, password: string, metadata?: any) => Promise<{ error: any }>
  signOut: () => Promise<void>
  refreshSession: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [loading, setLoading] = useState(true)

  // Helper to save session to localStorage
  const saveSession = (sessionData: Session) => {
    localStorage.setItem('auth_session', JSON.stringify(sessionData))
    setSession(sessionData)
    setUser(sessionData.user)
  }

  // Helper to clear session from localStorage
  const clearSession = () => {
    localStorage.removeItem('auth_session')
    setSession(null)
    setUser(null)
  }

  // Helper to get session from localStorage
  const getStoredSession = (): Session | null => {
    try {
      const stored = localStorage.getItem('auth_session')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  }

  useEffect(() => {
    // Get initial session from localStorage
    const getInitialSession = async () => {
      try {
        const storedSession = getStoredSession()
        if (storedSession) {
          // Validate the stored session with backend
          try {
            const response = await authAPI.validateToken()
            if (response.valid) {
              setSession(storedSession)
              setUser(storedSession.user)
            } else {
              // Session is invalid, clear it
              clearSession()
            }
          } catch (error) {
            console.error('Session validation failed:', error)
            clearSession()
          }
        }
      } catch (error) {
        console.error('Error getting initial session:', error)
      } finally {
        setLoading(false)
      }
    }

    getInitialSession()
  }, [])

  const signIn = async (email: string, password: string) => {
    setLoading(true)
    try {
      const response = await authAPI.login(email, password)
      
      const sessionData: Session = {
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        user: response.user,
        ...response.session
      }
      
      saveSession(sessionData)
      return { error: null }
    } catch (error) {
      console.error('Sign in error:', error)
      return { error }
    } finally {
      setLoading(false)
    }
  }

  const signUp = async (email: string, password: string, metadata?: any) => {
    setLoading(true)
    try {
      const response = await authAPI.register(email, password, metadata)
      
      const sessionData: Session = {
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        user: response.user,
        ...response.session
      }
      
      saveSession(sessionData)
      return { error: null }
    } catch (error) {
      console.error('Sign up error:', error)
      return { error }
    } finally {
      setLoading(false)
    }
  }

  const signOut = async () => {
    setLoading(true)
    try {
      await authAPI.logout()
    } catch (error) {
      console.error('Sign out error:', error)
    } finally {
      clearSession()
      setLoading(false)
    }
  }

  const refreshSession = async () => {
    try {
      const currentSession = getStoredSession()
      if (currentSession?.refresh_token) {
        const response = await authAPI.refreshToken(currentSession.refresh_token)
        
        const sessionData: Session = {
          access_token: response.access_token,
          refresh_token: response.refresh_token,
          user: response.user,
          ...response.session
        }
        
        saveSession(sessionData)
      }
    } catch (error) {
      console.error('Refresh session error:', error)
      clearSession()
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