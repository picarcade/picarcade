'use client'

import { useEffect, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { supabase } from '../../lib/supabase'

export default function AuthCallback() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const handleAuthCallback = async () => {
      try {
        // First, check if we already have an active session
        console.log('🔍 Checking for existing session...')
        const { data: { session: existingSession }, error: sessionError } = await supabase.auth.getSession()
        
        if (sessionError) {
          console.error('❌ Error checking session:', sessionError)
          throw sessionError
        }

        if (existingSession) {
          console.log('✅ Session already exists, magic link was processed automatically:', {
            userEmail: existingSession.user.email,
            sessionId: existingSession.access_token.substring(0, 10) + '...'
          })
          
          setStatus('success')
          setMessage(`Welcome back, ${existingSession.user.email}!`)
          
          // Clear any URL fragments for security
          if (window.location.hash) {
            window.history.replaceState({}, document.title, window.location.pathname)
          }
          
          // Wait a moment to show success message, then redirect
          setTimeout(() => {
            router.push('/') // Redirect to dashboard or home page
          }, 2000)
          return
        }

        // If no existing session, try to process tokens from URL fragment
        console.log('🔍 No existing session, checking URL for tokens...')
        const hashParams = new URLSearchParams(window.location.hash.substring(1))
        const accessToken = hashParams.get('access_token')
        const refreshToken = hashParams.get('refresh_token')

        // Handle magic link authentication (tokens in URL fragment)
        if (accessToken && refreshToken) {
          console.log('🔐 Processing magic link authentication...')
          console.log('📊 Token details:', {
            accessTokenLength: accessToken.length,
            refreshTokenLength: refreshToken.length,
            accessTokenStart: accessToken.substring(0, 10) + '...',
          })
          
          // Set the session with the tokens from the URL
          const { data, error } = await supabase.auth.setSession({
            access_token: accessToken,
            refresh_token: refreshToken,
          })

          console.log('📋 setSession result:', { data: !!data.session, error: error?.message })

          if (error) {
            console.error('❌ setSession error details:', error)
            throw new Error(`Session setup failed: ${error.message}`)
          }

          if (data.user && data.session) {
            console.log('✅ Magic link authentication successful:', {
              userEmail: data.user.email,
              sessionId: data.session.access_token.substring(0, 10) + '...'
            })
            
            // Try refreshing the session to ensure it's properly established
            console.log('🔄 Refreshing session to ensure persistence...')
            const { error: refreshError } = await supabase.auth.refreshSession()
            if (refreshError) {
              console.warn('⚠️ Session refresh warning:', refreshError.message)
              // Don't throw here, continue with the flow
            } else {
              console.log('✅ Session refreshed successfully')
            }
            
            setStatus('success')
            setMessage(`Welcome back, ${data.user.email}!`)
            
            // Clear the URL fragments for security
            window.history.replaceState({}, document.title, window.location.pathname)
            
            // Wait a moment to show success message, then redirect
            setTimeout(() => {
              router.push('/') // Redirect to dashboard or home page
            }, 2000)
            return
          } else {
            throw new Error('Session created but missing user or session data')
          }
        }

        // Handle OTP verification (token_hash in search params) - for other auth flows
        const tokenHash = searchParams.get('token_hash')
        
        if (tokenHash) {
          console.log('🔐 Processing OTP verification...')
          
          // Verify the OTP token
          const { data, error } = await supabase.auth.verifyOtp({
            token_hash: tokenHash,
            type: 'email',
          })

          if (error) {
            throw error
          }

          if (data.user) {
            console.log('✅ OTP verification successful:', data.user.email)
            setStatus('success')
            setMessage(`Welcome back, ${data.user.email}!`)
            
            // Wait a moment to show success message, then redirect
            setTimeout(() => {
              router.push('/') // Redirect to dashboard or home page
            }, 2000)
            return
          }
        }

        // If we get here, no valid tokens were found
        throw new Error('No valid authentication tokens found in callback URL')

      } catch (error: unknown) {
        console.error('❌ Authentication callback failed:', error)
        setStatus('error')
        setMessage(error instanceof Error ? error.message : 'Authentication failed')
        
        // Redirect to login page after showing error
        setTimeout(() => {
          router.push('/?error=auth_failed')
        }, 3000)
      }
    }

    handleAuthCallback()
  }, [searchParams, router])

  if (status === 'loading') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="animate-spin mx-auto mb-4 w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full"></div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Verifying your magic link...
          </h2>
          <p className="text-gray-600">
            Please wait while we sign you in securely.
          </p>
        </div>
      </div>
    )
  }

  if (status === 'success') {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
          <div className="text-green-500 text-5xl mb-4">✅</div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            Sign in successful!
          </h2>
          <p className="text-gray-600 mb-4">{message}</p>
          <p className="text-sm text-gray-500">
            Redirecting you to the app...
          </p>
        </div>
      </div>
    )
  }

  // Error state
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        <div className="text-red-500 text-5xl mb-4">❌</div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">
          Sign in failed
        </h2>
        <p className="text-gray-600 mb-4">{message}</p>
        <div className="space-y-2">
          <p className="text-sm text-gray-500">
            Redirecting you back to sign in...
          </p>
          <button
            onClick={() => router.push('/')}
            className="text-blue-600 hover:text-blue-700 text-sm underline"
          >
            Go back now
          </button>
        </div>
      </div>
    </div>
  )
} 