'use client'

import { useState, useEffect } from 'react'
import { useAuth } from './AuthProvider'
import { Loader2, Mail } from 'lucide-react'
import { supabase } from '../lib/supabase'
import { useSearchParams, useRouter } from 'next/navigation'

interface LandingPageProps {
  onAuthSuccess?: () => void
}

export function LandingPage({ onAuthSuccess }: LandingPageProps) {
  const [email, setEmail] = useState('')
  const [error, setError] = useState('')
  const [googleLoading, setGoogleLoading] = useState(false)
  const [magicLinkLoading, setMagicLinkLoading] = useState(false)
  const [magicLinkSent, setMagicLinkSent] = useState(false)
  
  const { signInWithMagicLink } = useAuth()
  const searchParams = useSearchParams()
  const router = useRouter()

  // Handle OAuth callback errors and session changes
  useEffect(() => {
    // Listen for auth state changes to handle successful login
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange(async (event, session) => {
      console.log('Auth state change:', event, session?.user?.email)
      
      if (event === 'SIGNED_IN' && session) {
        console.log('✅ User successfully signed in:', session.user.email)
        setError('')
        setGoogleLoading(false)
        onAuthSuccess?.()
      } else if (event === 'SIGNED_OUT') {
        console.log('User signed out')
        setGoogleLoading(false)
      }
    })

    // Handle any URL-based errors (though less common with automatic handling)
    const errorParam = searchParams.get('error')
    const errorDescription = searchParams.get('error_description')
    const message = searchParams.get('message')
    
    if (errorParam) {
      console.log('OAuth URL Error:', {
        error: errorParam,
        error_description: errorDescription,
        message,
        fullUrl: window.location.href
      })
      
      let errorMessage = 'An error occurred during authentication.'
      
      switch (errorParam) {
        case 'access_denied':
          errorMessage = 'Access was denied. Please try again.'
          break
        case 'server_error':
          errorMessage = 'Server error occurred during authentication.'
          break
        case 'temporarily_unavailable':
          errorMessage = 'Authentication service is temporarily unavailable.'
          break
        default:
          errorMessage = message || errorDescription || errorParam || 'An error occurred during authentication.'
      }
      
      setError(errorMessage)
      setGoogleLoading(false)
      // Clean up the URL
      router.replace('/', { scroll: false })
    }

    return () => subscription.unsubscribe()
  }, [searchParams, router, onAuthSuccess])

  const handleMagicLink = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setMagicLinkLoading(true)

    try {
      const { error } = await signInWithMagicLink(email)
      if (error) {
        setError(error.message || 'Failed to send magic link')
      } else {
        setError('')
        setMagicLinkSent(true)
      }
    } catch {
      setError('An unexpected error occurred')
    } finally {
      setMagicLinkLoading(false)
    }
  }

  const handleGoogleAuth = async () => {
    setGoogleLoading(true)
    setError('')

    try {
      console.log('🚀 Starting Google OAuth with automatic callback handling:', {
        isProduction: process.env.NODE_ENV === 'production',
        currentOrigin: window.location.origin,
        supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL,
        hasAnonKey: !!process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
      })
      
      const { data, error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          // Remove custom redirectTo - let Supabase handle it automatically
          scopes: 'openid email profile',
          queryParams: {
            access_type: 'offline',
            prompt: 'consent'
          }
        },
      })

      if (error) {
        console.error('❌ Google auth error:', error)
        setError(`Failed to sign in with Google: ${error.message}`)
        setGoogleLoading(false)
      } else if (data?.url) {
        console.log('✅ Redirecting to Google OAuth:', data.url)
        // OAuth initiation successful, user will be redirected
        // Don't set loading to false as user will be redirected
      } else {
        console.error('❌ No redirect URL received from Supabase')
        setError('Failed to initiate Google authentication')
        setGoogleLoading(false)
      }
    } catch (error) {
      console.error('❌ Google auth exception:', error)
      setError(`An error occurred with Google authentication: ${error instanceof Error ? error.message : 'Unknown error'}`)
      setGoogleLoading(false)
    }
  }

  const resetForm = () => {
    setEmail('')
    setError('')
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-12">
          <img 
            src="/logo_with_text_white_trans.png" 
            alt="PicArcade" 
            className="h-32 mx-auto mb-6"
          />
          <h1 className="text-2xl font-bold text-white mb-2">
            Welcome to PicArcade
          </h1>
          <p className="text-gray-400">
            Create amazing content with AI-powered image generation
          </p>
        </div>

        {/* Main Auth Card */}
        <div className="bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 rounded-2xl p-8 shadow-2xl">
          {/* Error Message */}
          {error && (
            <div className="mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-lg">
              <p className="text-red-400 text-sm text-center">{error}</p>
            </div>
          )}

          {/* Google OAuth Button */}
          <div className="mb-6">
            <button
              onClick={handleGoogleAuth}
              disabled={googleLoading || magicLinkLoading}
              className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-50 text-gray-900 py-3 px-4 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              {googleLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
              )}
              Continue with Google
            </button>
          </div>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-600"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-gray-800/60 text-gray-400">or sign in with email</span>
            </div>
          </div>

          {/* Magic Link Form */}
          <div className="bg-gray-700/30 rounded-lg p-6">
            <form onSubmit={handleMagicLink} className="space-y-4">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                  Email Address
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 bg-gray-700/50 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-400 transition-colors"
                    placeholder="Enter your email for magic link"
                    required
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={magicLinkLoading}
                className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-50 text-gray-900 py-3 px-4 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
              >
                {magicLinkLoading ? (
                  <>
                    <Loader2 className="w-5 h-5 animate-spin" />
                    Sending magic link...
                  </>
                ) : (
                  <>
                    <Mail className="w-5 h-5" />
                    Send Magic Link
                  </>
                )}
              </button>
            </form>
          </div>

          {/* Magic Link Sent Message */}
          {magicLinkSent && (
            <div className="mt-6 text-center">
              <p className="text-gray-400 text-sm">
                We&apos;ve sent a magic link to <span className="text-white">{email}</span>
              </p>
              <p className="text-gray-500 text-xs mt-1">
                Click the link in your email to sign in
              </p>
            </div>
          )}

          {/* Reset Form Button */}
          {magicLinkSent && (
            <div className="mt-4 text-center">
              <button
                onClick={() => {
                  setMagicLinkSent(false)
                  resetForm()
                }}
                className="text-gray-400 hover:text-white transition-colors text-sm underline"
              >
                Try a different email
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-500 text-xs">
          <p>By continuing, you agree to our Terms of Service and Privacy Policy</p>
        </div>
      </div>
    </div>
  )
} 