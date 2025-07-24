'use client'

import React, { useState } from 'react'
import { useAuth } from './AuthProvider'

interface MagicLinkAuthProps {
  onSuccess?: () => void
  className?: string
}

export function MagicLinkAuth({ onSuccess, className = '' }: MagicLinkAuthProps) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [sent, setSent] = useState(false)
  const [error, setError] = useState('')

  const { signInWithMagicLink } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!email.trim()) return

    setLoading(true)
    setError('')

    try {
      const { error } = await signInWithMagicLink(email)
      
      if (error) {
        setError(error.message || 'Failed to send magic link')
      } else {
        setSent(true)
        // Call success callback if provided
        onSuccess?.()
      }
    } catch (error) {
      setError('An unexpected error occurred')
      console.error('Magic link error:', error)
    } finally {
      setLoading(false)
    }
  }

  const resetForm = () => {
    setEmail('')
    setError('')
    setSent(false)
    setLoading(false)
  }

  if (sent) {
    return (
      <div className={`text-center space-y-4 ${className}`}>
        <div className="p-6 bg-green-50 border border-green-200 rounded-lg">
          <div className="text-green-600 text-lg font-medium mb-2">
            📧 Check your email!
          </div>
          <p className="text-green-700 mb-4">
            We&apos;ve sent a magic link to <strong>{email}</strong>
          </p>
          <p className="text-sm text-green-600">
            Click the link in your email to sign in. The link will expire in 1 hour.
          </p>
        </div>
        
        <button
          onClick={resetForm}
          className="text-blue-600 hover:text-blue-700 text-sm underline"
        >
          Try a different email
        </button>
      </div>
    )
  }

  return (
    <div className={`space-y-4 ${className}`}>
      <div className="text-center mb-6">
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          ✨ Sign in with Magic Link
        </h3>
        <p className="text-sm text-gray-600">
          No password required. We&apos;ll send you a secure link to sign in.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="magic-email" className="sr-only">
            Email address
          </label>
          <input
            id="magic-email"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Enter your email address"
            required
            disabled={loading}
            className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-700 text-sm">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !email.trim()}
          className="w-full bg-blue-600 text-white py-3 px-4 rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Sending magic link...
            </span>
          ) : (
            'Send Magic Link'
          )}
        </button>
      </form>

      <div className="text-xs text-gray-500 text-center">
        Magic links are secure, temporary, and expire after 1 hour for your protection.
      </div>
    </div>
  )
} 