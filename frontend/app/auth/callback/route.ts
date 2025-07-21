import { createClient } from '@supabase/supabase-js'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const origin = requestUrl.origin
  const isProduction = process.env.NODE_ENV === 'production'
  const productionUrl = process.env.NEXT_PUBLIC_PRODUCTION_URL

  if (code) {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )

    try {
      const { error } = await supabase.auth.exchangeCodeForSession(code)
      
      if (!error) {
        // Successful authentication - redirect to main app
        // Use environment variable, then picarcade.ai in production, otherwise use current origin
        let redirectUrl = `${origin}/`
        
        if (productionUrl) {
          redirectUrl = `${productionUrl}/`
        } else if (isProduction && origin.includes('vercel.app')) {
          redirectUrl = 'https://picarcade.ai/'
        }
        
        return NextResponse.redirect(redirectUrl)
      } else {
        console.error('OAuth callback error:', error)
        let errorRedirectUrl = `${origin}/?error=auth_error`
        
        if (productionUrl) {
          errorRedirectUrl = `${productionUrl}/?error=auth_error`
        } else if (isProduction && origin.includes('vercel.app')) {
          errorRedirectUrl = 'https://picarcade.ai/?error=auth_error'
        }
        
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
      
      return NextResponse.redirect(errorRedirectUrl)
    }
  }

  // Return the user to an error page with some instructions
  let errorRedirectUrl = `${origin}/?error=no_code`
  
  if (productionUrl) {
    errorRedirectUrl = `${productionUrl}/?error=no_code`
  } else if (isProduction && origin.includes('vercel.app')) {
    errorRedirectUrl = 'https://picarcade.ai/?error=no_code'
  }
  
  return NextResponse.redirect(errorRedirectUrl)
} 