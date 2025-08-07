"use client"
import React, { useState } from 'react'
import { Share2, Copy, Download, ExternalLink, Facebook, Twitter, Instagram, Check } from 'lucide-react'

interface ShareButtonProps {
  url: string
  title?: string
  isVideo?: boolean
  className?: string
  showText?: boolean
  size?: 'sm' | 'md' | 'lg'
}

export default function ShareButton({ 
  url, 
  title = "Check out this AI-generated content!", 
  isVideo = false, 
  className = "",
  showText = false,
  size = 'md'
}: ShareButtonProps) {
  const [showShareMenu, setShowShareMenu] = useState(false)
  const [copied, setCopied] = useState(false)

  const sizeClasses = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4', 
    lg: 'w-5 h-5'
  }

  const buttonSizeClasses = {
    sm: 'p-1',
    md: 'p-2',
    lg: 'p-3'
  }

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch (err) {
      console.error('Failed to copy URL:', err)
    }
  }

  const downloadMedia = async () => {
    try {
      const response = await fetch(url)
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      link.download = `ai-generated-${isVideo ? 'video' : 'image'}-${Date.now()}.${isVideo ? 'mp4' : 'jpg'}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err) {
      console.error('Failed to download media:', err)
      // Fallback: open in new tab
      window.open(url, '_blank')
    }
  }

  const shareToSocial = (platform: string) => {
    const encodedUrl = encodeURIComponent(url)
    const encodedTitle = encodeURIComponent(title)
    
    let shareUrl = ''
    
    switch (platform) {
      case 'twitter':
        shareUrl = `https://twitter.com/intent/tweet?text=${encodedTitle}&url=${encodedUrl}`
        break
      case 'facebook':
        shareUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodedUrl}`
        break
      case 'reddit':
        shareUrl = `https://reddit.com/submit?url=${encodedUrl}&title=${encodedTitle}`
        break
      case 'pinterest':
        if (!isVideo) {
          shareUrl = `https://pinterest.com/pin/create/button/?url=${encodedUrl}&media=${encodedUrl}&description=${encodedTitle}`
        }
        break
      default:
        return
    }
    
    if (shareUrl) {
      window.open(shareUrl, '_blank', 'width=600,height=400')
    }
  }

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: title,
          url: url,
        })
      } catch (err) {
        console.error('Native share failed:', err)
      }
    }
  }

  const hasNativeShare = typeof navigator !== 'undefined' && navigator.share

  return (
    <div className="relative">
      <button
        onClick={(e) => {
          e.stopPropagation()
          setShowShareMenu(!showShareMenu)
        }}
        className={`flex items-center gap-2 ${buttonSizeClasses[size]} bg-gray-600 text-white rounded-full hover:bg-gray-700 transition-colors ${className}`}
        title="Share"
      >
        <Share2 className={sizeClasses[size]} />
        {showText && <span className="text-sm">Share</span>}
      </button>

      {showShareMenu && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-40"
            onClick={() => setShowShareMenu(false)}
          />
          
          {/* Share menu */}
          <div className="absolute top-full right-0 mt-2 bg-white rounded-lg shadow-lg border border-gray-200 p-2 z-50 min-w-48">
            {/* Copy URL */}
            <button
              onClick={() => {
                copyToClipboard()
                setShowShareMenu(false)
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              {copied ? <Check className="w-4 h-4 text-green-600" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copied!' : 'Copy URL'}
            </button>

            {/* Download */}
            <button
              onClick={() => {
                downloadMedia()
                setShowShareMenu(false)
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              <Download className="w-4 h-4" />
              Download {isVideo ? 'Video' : 'Image'}
            </button>

            {/* Open in new tab */}
            <button
              onClick={() => {
                window.open(url, '_blank')
                setShowShareMenu(false)
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              Open in New Tab
            </button>

            <hr className="my-2 border-gray-200" />

            {/* Native share (mobile) */}
            {hasNativeShare && (
              <button
                onClick={() => {
                  handleNativeShare()
                  setShowShareMenu(false)
                }}
                className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
              >
                <Share2 className="w-4 h-4" />
                Share...
              </button>
            )}

            {/* Social media options */}
            <button
              onClick={() => {
                shareToSocial('twitter')
                setShowShareMenu(false)
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              <div className="w-4 h-4 bg-blue-400 rounded-sm flex items-center justify-center">
                <span className="text-white text-xs font-bold">𝕏</span>
              </div>
              Share on X (Twitter)
            </button>

            <button
              onClick={() => {
                shareToSocial('facebook')
                setShowShareMenu(false)
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              <div className="w-4 h-4 bg-blue-600 rounded-sm flex items-center justify-center">
                <span className="text-white text-xs font-bold">f</span>
              </div>
              Share on Facebook
            </button>

            <button
              onClick={() => {
                shareToSocial('reddit')
                setShowShareMenu(false)
              }}
              className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
            >
              <div className="w-4 h-4 bg-orange-600 rounded-sm flex items-center justify-center">
                <span className="text-white text-xs font-bold">r</span>
              </div>
              Share on Reddit
            </button>

            {/* Pinterest for images only */}
            {!isVideo && (
              <button
                onClick={() => {
                  shareToSocial('pinterest')
                  setShowShareMenu(false)
                }}
                className="w-full flex items-center gap-3 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
              >
                <div className="w-4 h-4 bg-red-600 rounded-sm flex items-center justify-center">
                  <span className="text-white text-xs font-bold">P</span>
                </div>
                Share on Pinterest
              </button>
            )}
          </div>
        </>
      )}
    </div>
  )
}