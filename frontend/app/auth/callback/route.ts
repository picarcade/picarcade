import { createClient } from '@supabase/supabase-js'
import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const requestUrl = new URL(request.url)
  const code = requestUrl.searchParams.get('code')
  const origin = requestUrl.origin

  if (code) {
    const supabase = createClient(
      process.env.NEXT_PUBLIC_SUPABASE_URL!,
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!
    )

    try {
      const { error } = await supabase.auth.exchangeCodeForSession(code)
      
      if (!error) {
        // Successful authentication - redirect to main app
        return NextResponse.redirect(`${origin}/`)
      } else {
        console.error('OAuth callback error:', error)
        return NextResponse.redirect(`${origin}/?error=auth_error`)
      }
    } catch (error) {
      console.error('OAuth callback exception:', error)
      return NextResponse.redirect(`${origin}/?error=auth_error`)
    }
  }

  // Return the user to an error page with some instructions
  return NextResponse.redirect(`${origin}/?error=no_code`)
} 