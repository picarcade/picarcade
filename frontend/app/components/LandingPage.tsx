'use client'

import React, { useState } from 'react'
import { useAuth } from './AuthProvider'
import { Mail, Lock, Eye, EyeOff, Loader2 } from 'lucide-react'
import { supabase } from '../lib/supabase'

interface LandingPageProps {
  onAuthSuccess?: () => void
}

export function LandingPage({ onAuthSuccess }: LandingPageProps) {
  const [mode, setMode] = useState<'signin' | 'signup'>('signin')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [socialLoading, setSocialLoading] = useState<'google' | 'facebook' | null>(null)
  
  const { signIn, signUp } = useAuth()

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      if (mode === 'signup') {
        if (password !== confirmPassword) {
          setError('Passwords do not match')
          return
        }
        
        if (password.length < 6) {
          setError('Password must be at least 6 characters')
          return
        }

        const { error } = await signUp(email, password)
        if (error) {
          setError(error.message || 'Failed to create account')
        } else {
          setError('')
          onAuthSuccess?.()
        }
      } else {
        const { error } = await signIn(email, password)
        if (error) {
          setError(error.message || 'Failed to sign in')
        } else {
          setError('')
          onAuthSuccess?.()
        }
      }
    } catch {
      setError('An unexpected error occurred')
    } finally {
      setIsLoading(false)
    }
  }

  const handleSocialAuth = async (provider: 'google' | 'facebook') => {
    setSocialLoading(provider)
    setError('')

    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: {
          redirectTo: `${window.location.origin}`,
        },
      })

      if (error) {
        setError(`Failed to sign in with ${provider}`)
        console.error(`${provider} auth error:`, error)
      }
    } catch (error) {
      setError(`An error occurred with ${provider} authentication`)
      console.error(`${provider} auth error:`, error)
    } finally {
      setSocialLoading(null)
    }
  }

  const resetForm = () => {
    setEmail('')
    setPassword('')
    setConfirmPassword('')
    setError('')
  }

  const switchMode = () => {
    setMode(mode === 'signin' ? 'signup' : 'signin')
    resetForm()
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
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-white text-center mb-2">
              {mode === 'signin' ? 'Sign In' : 'Create Account'}
            </h2>
            <p className="text-gray-400 text-center text-sm">
              {mode === 'signin' 
                ? 'Welcome back! Sign in to continue creating' 
                : 'Join thousands of creators using AI to bring their ideas to life'
              }
            </p>
          </div>

          {/* Social Auth Buttons */}
          <div className="space-y-3 mb-6">
            <button
              onClick={() => handleSocialAuth('google')}
              disabled={socialLoading !== null || isLoading}
              className="w-full flex items-center justify-center gap-3 bg-white hover:bg-gray-50 text-gray-900 py-3 px-4 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              {socialLoading === 'google' ? (
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

            <button
              onClick={() => handleSocialAuth('facebook')}
              disabled={socialLoading !== null || isLoading}
              className="w-full flex items-center justify-center gap-3 bg-[#1877F2] hover:bg-[#166FE5] text-white py-3 px-4 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-sm"
            >
              {socialLoading === 'facebook' ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z"/>
                </svg>
              )}
              Continue with Facebook
            </button>
          </div>

          {/* Divider */}
          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-600"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-gray-800/60 text-gray-400">or continue with email</span>
            </div>
          </div>

          {/* Email Form */}
          <form onSubmit={handleEmailSubmit} className="space-y-4">
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
                  placeholder="Enter your email"
                  required
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                Password
              </label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-12 py-3 bg-gray-700/50 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-400 transition-colors"
                  placeholder="Enter your password"
                  required
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {mode === 'signup' && (
              <div>
                <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-2">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={20} />
                  <input
                    id="confirmPassword"
                    type={showConfirmPassword ? 'text' : 'password'}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full pl-10 pr-12 py-3 bg-gray-700/50 border border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-white placeholder-gray-400 transition-colors"
                    placeholder="Confirm your password"
                    required
                    minLength={6}
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-300"
                  >
                    {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
              </div>
            )}

            {error && (
              <div className="bg-red-500/20 border border-red-500/50 text-red-300 px-4 py-3 rounded-lg text-sm">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading || socialLoading !== null}
              className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white py-3 px-4 rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
            >
              {isLoading ? (
                <div className="flex items-center justify-center gap-2">
                  <Loader2 className="w-5 h-5 animate-spin" />
                  {mode === 'signin' ? 'Signing In...' : 'Creating Account...'}
                </div>
              ) : (
                mode === 'signin' ? 'Sign In' : 'Create Account'
              )}
            </button>
          </form>

          {/* Mode Switch */}
          <div className="mt-6 text-center">
            <p className="text-gray-400 text-sm">
              {mode === 'signin' ? "Don't have an account?" : 'Already have an account?'}
              <button
                onClick={switchMode}
                className="ml-2 text-blue-400 hover:text-blue-300 font-medium transition-colors"
              >
                {mode === 'signin' ? 'Sign up' : 'Sign in'}
              </button>
            </p>
          </div>

          {mode === 'signup' && (
            <div className="mt-4 text-xs text-gray-500 text-center">
              By creating an account, you agree to our{' '}
              <a href="#" className="text-blue-400 hover:text-blue-300 underline">Terms of Service</a>
              {' '}and{' '}
              <a href="#" className="text-blue-400 hover:text-blue-300 underline">Privacy Policy</a>.
            </div>
          )}
        </div>

        {/* Features Preview */}
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4 text-center">
          <div className="text-gray-400">
            <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full mx-auto mb-2 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clipRule="evenodd" />
              </svg>
            </div>
            <p className="text-sm">AI Image Generation</p>
          </div>
          <div className="text-gray-400">
            <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full mx-auto mb-2 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M3 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1zm0 4a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <p className="text-sm">Smart Editing</p>
          </div>
          <div className="text-gray-400">
            <div className="w-8 h-8 bg-gradient-to-r from-pink-500 to-red-500 rounded-full mx-auto mb-2 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" />
              </svg>
            </div>
            <p className="text-sm">Creative Tools</p>
          </div>
        </div>
      </div>
    </div>
  )
} 