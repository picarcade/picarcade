import { createClient } from '@supabase/supabase-js'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const origin = requestUrl.origin
  const isProduction = process.env.NODE_ENV === 'production'
  const productionUrl = process.env.NEXT_PUBLIC_PRODUCTION_URL

  console.log('OAuth Callback Debug:', {
    code: code ? 'present' : 'missing',
    origin,
    isProduction,
    productionUrl,
    fullUrl: request.url,
    searchParams: Object.fromEntries(requestUrl.searchParams.entries())
  })

  if (code) {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )

    console.log('Supabase client created, attempting to exchange code for session')

    try {
      const { error } = await supabase.auth.exchangeCodeForSession(code)
      
      if (!error) {
        console.log('OAuth callback successful!')
        // Successful authentication - redirect to main app
        // Use environment variable, then picarcade.ai in production, otherwise use current origin
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
        let errorRedirectUrl = `${origin}/?error=auth_error`
        
        if (productionUrl) {
          errorRedirectUrl = `${productionUrl}/?error=auth_error`
        } else if (isProduction && origin.includes('vercel.app')) {
          errorRedirectUrl = 'https://picarcade.ai/?error=auth_error'
        }
        
        console.log('Error redirect URL:', errorRedirectUrl)
        return NextResponse.redirect(errorRedirectUrl)
      }
    } catch (error) {
      console.error('OAuth callback exception:', error)
      let errorRedirectUrl = `${origin}/?error=auth_error`
      
      if (productionUrl) {
        errorRedirectUrl = `${productionUrl}/?error=auth_error`
      } else if (isProduction && origin.includes('vercel.app')) {
        errorRedirectUrl = 'https://picarcade.ai/?error=auth_error'
      }
      
      console.log('Exception redirect URL:', errorRedirectUrl)
      return NextResponse.redirect(errorRedirectUrl)
    }
  }

  // Return the user to an error page with some instructions
  console.log('No code parameter found in callback')
  let errorRedirectUrl = `${origin}/?error=no_code`
  
  if (productionUrl) {
    errorRedirectUrl = `${productionUrl}/?error=no_code`
  } else if (isProduction && origin.includes('vercel.app')) {
    errorRedirectUrl = 'https://picarcade.ai/?error=no_code'
  }
  
  console.log('No code redirect URL:', errorRedirectUrl)
  return NextResponse.redirect(errorRedirectUrl)
} 