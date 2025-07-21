import { createClient } from '@supabase/supabase-js'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const error = requestUrl.searchParams.get('error')
  const error_description = requestUrl.searchParams.get('error_description')
  const origin = requestUrl.origin
  const isProduction = process.env.NODE_ENV === 'production'
  const productionUrl = process.env.NEXT_PUBLIC_PRODUCTION_URL

  console.log('OAuth Callback Debug:', {
    code: code ? 'present' : 'missing',
    error,
    error_description,
    origin,
    isProduction,
    productionUrl,
    fullUrl: request.url,
    searchParams: Object.fromEntries(requestUrl.searchParams.entries())
  })

  // Handle OAuth errors from provider
  if (error) {
    console.error('OAuth provider error:', { error, error_description })
    let errorRedirectUrl = `${origin}/?error=${error}&error_description=${encodeURIComponent(error_description || error)}`
    
    if (productionUrl) {
      errorRedirectUrl = `${productionUrl}/?error=${error}&error_description=${encodeURIComponent(error_description || error)}`
    } else if (isProduction && origin.includes('vercel.app')) {
      errorRedirectUrl = `https://picarcade.ai/?error=${error}&error_description=${encodeURIComponent(error_description || error)}`
    }
    
    return NextResponse.redirect(errorRedirectUrl)
  }

  if (code) {
    // Use hardcoded values since server-side can't reliably access NEXT_PUBLIC_ vars
    const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL || 'https://izfjglgvaqrqaywfniwi.supabase.co'
    const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Iml6ZmpnbGd2YXFycWF5d2ZuaXdpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTMwNTcwNzEsImV4cCI6MjA2ODYzMzA3MX0.IRI6lerdkg5CAVUNmsSqLN9DT983YNxH8orRB5fllfQ'
    
    console.log('Creating Supabase client with:', {
      url: supabaseUrl,
      keyExists: !!supabaseAnonKey
    })

    const supabase = createClient(supabaseUrl, supabaseAnonKey, {
      auth: {
        flowType: 'pkce',
        autoRefreshToken: true,
        persistSession: false, // Don't persist on server side
        detectSessionInUrl: false // Disable to avoid conflicts
      }
    })

    console.log('Supabase client created, attempting to exchange code for session')

    try {
      const { data, error } = await supabase.auth.exchangeCodeForSession(code)
      
      if (!error && data.session) {
        console.log('OAuth callback successful!', {
          userId: data.user?.id,
          email: data.user?.email
        })
        
        // Successful authentication - redirect to main app
        let redirectUrl = `${origin}/`
        
        if (productionUrl) {
          redirectUrl = `${productionUrl}/`
        } else if (isProduction && origin.includes('vercel.app')) {
          redirectUrl = 'https://picarcade.ai/'
        }
        
        console.log('Redirecting to:', redirectUrl)
        return NextResponse.redirect(redirectUrl)
      } else {
        console.error('OAuth callback error:', error)
        let errorRedirectUrl = `${origin}/?error=auth_error&message=${encodeURIComponent(error?.message || 'Authentication failed')}`
        
        if (productionUrl) {
          errorRedirectUrl = `${productionUrl}/?error=auth_error&message=${encodeURIComponent(error?.message || 'Authentication failed')}`
        } else if (isProduction && origin.includes('vercel.app')) {
          errorRedirectUrl = `https://picarcade.ai/?error=auth_error&message=${encodeURIComponent(error?.message || 'Authentication failed')}`
        }
        
        console.log('Error redirect URL:', errorRedirectUrl)
        return NextResponse.redirect(errorRedirectUrl)
      }
    } catch (error) {
      console.error('OAuth callback exception:', error)
      let errorRedirectUrl = `${origin}/?error=auth_error&message=${encodeURIComponent('Authentication exception occurred')}`
      
      if (productionUrl) {
        errorRedirectUrl = `${productionUrl}/?error=auth_error&message=${encodeURIComponent('Authentication exception occurred')}`
      } else if (isProduction && origin.includes('vercel.app')) {
        errorRedirectUrl = `https://picarcade.ai/?error=auth_error&message=${encodeURIComponent('Authentication exception occurred')}`
      }
      
      console.log('Exception redirect URL:', errorRedirectUrl)
      return NextResponse.redirect(errorRedirectUrl)
    }
  }

  // Return the user to an error page with some instructions
  console.log('No code parameter found in callback')
  let errorRedirectUrl = `${origin}/?error=no_code&message=${encodeURIComponent('No authorization code received')}`
  
  if (productionUrl) {
    errorRedirectUrl = `${productionUrl}/?error=no_code&message=${encodeURIComponent('No authorization code received')}`
  } else if (isProduction && origin.includes('vercel.app')) {
    errorRedirectUrl = `https://picarcade.ai/?error=no_code&message=${encodeURIComponent('No authorization code received')}`
  }
  
  console.log('No code redirect URL:', errorRedirectUrl)
  return NextResponse.redirect(errorRedirectUrl)
} 