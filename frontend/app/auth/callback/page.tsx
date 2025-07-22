'use client'

import { useEffect, useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { supabase } from '../../lib/supabase'

function AuthCallbackContent() {
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
          setMessage('Successfully signed in!')
          
          // Clear URL fragments for security
          if (window.location.hash) {
            window.history.replaceState(null, '', window.location.pathname)
          }
          
          // Redirect to main app
          setTimeout(() => router.push('/'), 2000)
          return
        }

        // Check for magic link tokens in URL fragment
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
            setMessage('Successfully signed in!')
            
            // Clear URL fragments for security
            window.history.replaceState(null, '', window.location.pathname)
            
            // Redirect to main app after a short delay
            setTimeout(() => router.push('/'), 2000)
            return
          }
        }

        // Check for error in URL (from Supabase)
        const error = searchParams.get('error')
        const errorDescription = searchParams.get('error_description')
        
        if (error) {
          throw new Error(errorDescription || error)
        }

        // If we get here, no valid tokens were found
        throw new Error('No valid authentication tokens found in callback URL')
        
      } catch (error: unknown) {
        console.error('❌ Authentication callback failed:', error)
        setStatus('error')
        setMessage(error instanceof Error ? error.message : 'Authentication failed')
        
        // Redirect to sign in page after showing error
        setTimeout(() => router.push('/?error=auth_failed'), 3000)
      }
    }

    handleAuthCallback()
  }, [router, searchParams])

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-800/60 rounded-lg p-8 max-w-md w-full text-center">
        {status === 'loading' && (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-white mb-2">Signing you in...</h2>
            <p className="text-gray-400">Please wait while we verify your magic link</p>
          </>
        )}
        
        {status === 'success' && (
          <>
            <div className="text-green-500 text-4xl mb-4">✅</div>
            <h2 className="text-xl font-semibold text-white mb-2">Welcome to PicArcade!</h2>
            <p className="text-gray-400 mb-4">{message}</p>
            <p className="text-sm text-gray-500">Redirecting you to the app...</p>
          </>
        )}
        
        {status === 'error' && (
          <>
            <div className="text-red-500 text-4xl mb-4">❌</div>
            <h2 className="text-xl font-semibold text-white mb-2">Authentication Failed</h2>
            <p className="text-gray-400 mb-4">{message}</p>
            <p className="text-sm text-gray-500">Redirecting you back to sign in...</p>
          </>
        )}
      </div>
    </div>
  )
}

function LoadingFallback() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center p-4">
      <div className="bg-gray-800/60 rounded-lg p-8 max-w-md w-full text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
        <h2 className="text-xl font-semibold text-white mb-2">Loading...</h2>
        <p className="text-gray-400">Preparing authentication</p>
      </div>
    </div>
  )
}

export default function AuthCallback() {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <AuthCallbackContent />
    </Suspense>
  )
} 