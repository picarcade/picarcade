'use client'

import React, { useEffect, useState } from 'react'
import { X, ZoomIn, ZoomOut, RotateCw } from 'lucide-react'
import ShareButton from './ShareButton'

interface ImageMaximizeModalProps {
  isOpen: boolean
  onClose: () => void
  imageUrl: string
  altText?: string
}

export default function ImageMaximizeModal({ 
  isOpen, 
  onClose, 
  imageUrl, 
  altText = "Maximized image" 
}: ImageMaximizeModalProps) {
  const [scale, setScale] = useState(1)
  const [rotation, setRotation] = useState(0)
  const [translateX, setTranslateX] = useState(0)
  const [translateY, setTranslateY] = useState(0)
  const [isDragging, setIsDragging] = useState(false)
  const [lastTouch, setLastTouch] = useState({ x: 0, y: 0 })

  // Reset transforms when modal opens
  useEffect(() => {
    if (isOpen) {
      setScale(1)
      setRotation(0)
      setTranslateX(0)
      setTranslateY(0)
    }
  }, [isOpen])

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown)
      // Prevent body scroll when modal is open
      document.body.style.overflow = 'hidden'
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev * 1.5, 4))
  }

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev / 1.5, 0.5))
  }

  const handleRotate = () => {
    setRotation(prev => (prev + 90) % 360)
  }

  const handleReset = () => {
    setScale(1)
    setRotation(0)
    setTranslateX(0)
    setTranslateY(0)
  }

  // Touch/Mouse event handlers for pan and pinch
  const handleTouchStart = (e: React.TouchEvent) => {
    if (e.touches.length === 1) {
      setIsDragging(true)
      setLastTouch({ x: e.touches[0].clientX, y: e.touches[0].clientY })
    } else if (e.touches.length === 2) {
      // Handle pinch-to-zoom
      const distance = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      )
      setLastTouch({ x: distance, y: 0 })
    }
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    e.preventDefault()
    
    if (e.touches.length === 1 && isDragging && scale > 1) {
      const deltaX = e.touches[0].clientX - lastTouch.x
      const deltaY = e.touches[0].clientY - lastTouch.y
      
      setTranslateX(prev => prev + deltaX)
      setTranslateY(prev => prev + deltaY)
      setLastTouch({ x: e.touches[0].clientX, y: e.touches[0].clientY })
    } else if (e.touches.length === 2) {
      // Handle pinch-to-zoom
      const distance = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY
      )
      
      if (lastTouch.x > 0) {
        const scaleChange = distance / lastTouch.x
        setScale(prev => Math.max(0.5, Math.min(4, prev * scaleChange)))
      }
      setLastTouch({ x: distance, y: 0 })
    }
  }

  const handleTouchEnd = () => {
    setIsDragging(false)
    setLastTouch({ x: 0, y: 0 })
  }

  // Handle mouse events for desktop
  const handleMouseDown = (e: React.MouseEvent) => {
    if (scale > 1) {
      setIsDragging(true)
      setLastTouch({ x: e.clientX, y: e.clientY })
    }
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && scale > 1) {
      const deltaX = e.clientX - lastTouch.x
      const deltaY = e.clientY - lastTouch.y
      
      setTranslateX(prev => prev + deltaX)
      setTranslateY(prev => prev + deltaY)
      setLastTouch({ x: e.clientX, y: e.clientY })
    }
  }

  const handleMouseUp = () => {
    setIsDragging(false)
  }

  if (!isOpen) return null

  return (
    <div 
      className="fixed inset-0 bg-black/95 backdrop-blur-sm z-50 flex items-center justify-center"
      onClick={(e) => {
        // Only close if clicking on the backdrop, not the image
        if (e.target === e.currentTarget) {
          onClose()
        }
      }}
    >
      {/* Control buttons */}
      <div className="absolute top-4 right-4 flex gap-2 z-10">
        <ShareButton 
          url={imageUrl}
          title="Check out this amazing AI-generated image!"
          isVideo={false}
          size="lg"
          className="bg-black/50 hover:bg-black/70"
        />
        <button
          onClick={handleZoomOut}
          className="p-2 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors"
          title="Zoom out"
        >
          <ZoomOut className="w-5 h-5" />
        </button>
        <button
          onClick={handleZoomIn}
          className="p-2 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors"
          title="Zoom in"
        >
          <ZoomIn className="w-5 h-5" />
        </button>
        <button
          onClick={handleRotate}
          className="p-2 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors"
          title="Rotate"
        >
          <RotateCw className="w-5 h-5" />
        </button>
        <button
          onClick={onClose}
          className="p-2 bg-black/50 text-white rounded-full hover:bg-black/70 transition-colors"
          title="Close"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Reset button (when zoomed or rotated) */}
      {(scale !== 1 || rotation !== 0 || translateX !== 0 || translateY !== 0) && (
        <button
          onClick={handleReset}
          className="absolute top-4 left-4 px-3 py-1 bg-black/50 text-white text-sm rounded-full hover:bg-black/70 transition-colors z-10"
        >
          Reset
        </button>
      )}

      {/* Image container */}
      <div 
        className="relative max-w-full max-h-full flex items-center justify-center touch-none select-none"
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <img
          src={imageUrl}
          alt={altText}
          className="max-w-full max-h-full object-contain"
          style={{
            transform: `scale(${scale}) rotate(${rotation}deg) translate(${translateX / scale}px, ${translateY / scale}px)`,
            transformOrigin: 'center',
            transition: isDragging ? 'none' : 'transform 0.2s ease-out',
            cursor: scale > 1 ? (isDragging ? 'grabbing' : 'grab') : 'default',
          }}
          draggable={false}
          onError={(e) => {
            const target = e.target as HTMLImageElement
            target.style.display = 'none'
            const parent = target.parentElement
            if (parent) {
              parent.innerHTML = `
                <div class="text-white text-center p-8">
                  <p class="text-lg mb-2">Failed to load image</p>
                  <p class="text-sm opacity-75">The image could not be displayed</p>
                </div>
              `
            }
          }}
        />
      </div>

      {/* Instructions for mobile */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 text-center z-10 md:hidden">
        <div className="bg-black/50 text-white text-sm px-4 py-2 rounded-full">
          Pinch to zoom • Tap to close • Drag to pan
        </div>
      </div>

      {/* Instructions for desktop */}
      <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 text-center z-10 hidden md:block">
        <div className="bg-black/50 text-white text-sm px-4 py-2 rounded-full">
          Scroll to zoom • Drag to pan • Click outside to close
        </div>
      </div>
    </div>
  )
} 