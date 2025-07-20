"use client"
import PerplexityInterface from './components/PerplexityInterface'
import { LandingPage } from './components/LandingPage'
import { useAuth } from './components/AuthProvider'

export default function Home() {
  const { user, loading } = useAuth()
  
  // Show loading state while checking authentication
  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center">
          <img 
            src="/logo_with_text_white_trans.png" 
            alt="PicArcade" 
            className="h-32 mx-auto mb-6 animate-pulse"
          />
          <div className="text-white text-lg">Loading...</div>
        </div>
      </div>
    )
  }
  
  // Show landing page if user is not authenticated
  if (!user) {
    return <LandingPage />
  }
  
  // Show main interface if user is authenticated
  return <PerplexityInterface />
}
