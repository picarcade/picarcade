'use client'

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Tag } from 'lucide-react'
import { getUserReferences } from '../lib/api'
import type { Reference } from '../types'

interface ReferenceDropdownProps {
  isOpen: boolean
  searchTerm: string
  onSelect: (tag: string) => void
  onClose: () => void
  userId: string
  position: { top: number; left: number }
}

export default function ReferenceDropdown({
  isOpen,
  searchTerm,
  onSelect,
  onClose,
  userId,
  position
}: ReferenceDropdownProps) {
  const [references, setReferences] = useState<Reference[]>([])
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Load references when dropdown opens
  useEffect(() => {
    if (isOpen && userId) {
      loadReferences()
    }
  }, [isOpen, userId])

  // Reset selected index when search term changes
  useEffect(() => {
    setSelectedIndex(0)
  }, [searchTerm])

  const loadReferences = async () => {
    setIsLoading(true)
    try {
      const data = await getUserReferences(userId)
      setReferences(data)
    } catch (error) {
      console.error('Failed to load references:', error)
      setReferences([])
    } finally {
      setIsLoading(false)
    }
  }

  // Filter references based on search term
  const filteredReferences = useMemo(() => {
    if (!searchTerm) return references
    return references.filter(ref => 
      ref.tag.toLowerCase().includes(searchTerm.toLowerCase())
    )
  }, [references, searchTerm])

  // Handle keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex(prev => 
            prev < filteredReferences.length - 1 ? prev + 1 : 0
          )
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex(prev => 
            prev > 0 ? prev - 1 : filteredReferences.length - 1
          )
          break
        case 'Enter':
          e.preventDefault()
          if (filteredReferences[selectedIndex]) {
            onSelect(filteredReferences[selectedIndex].tag)
          }
          break
        case 'Escape':
          e.preventDefault()
          onClose()
          break
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen, filteredReferences, selectedIndex, onSelect, onClose])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        onClose()
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <div
      ref={dropdownRef}
      className="absolute z-50 bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-48 overflow-y-auto min-w-64"
      style={{
        top: position.top,
        left: position.left,
      }}
    >
      {isLoading ? (
        <div className="p-3 text-center">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-purple-400 mx-auto"></div>
          <p className="text-gray-400 text-xs mt-1">Loading references...</p>
        </div>
      ) : filteredReferences.length === 0 ? (
        <div className="p-3 text-center">
          <Tag className="w-4 h-4 text-gray-500 mx-auto mb-1" />
          <p className="text-gray-400 text-xs">
            {searchTerm ? `No references match "${searchTerm}"` : 'No references found'}
          </p>
          <p className="text-gray-500 text-xs mt-1">
            Use the References panel to add some!
          </p>
        </div>
      ) : (
        <div className="py-1">
          {filteredReferences.map((reference, index) => (
            <div
              key={reference.id}
              className={`flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors ${
                index === selectedIndex
                  ? 'bg-purple-600 text-white'
                  : 'text-gray-300 hover:bg-gray-700'
              }`}
              onClick={() => onSelect(reference.tag)}
            >
              <div className="w-8 h-8 rounded overflow-hidden flex-shrink-0">
                <img
                  src={reference.image_url}
                  alt={reference.tag}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement
                    target.style.display = 'none'
                    const parent = target.parentElement
                    if (parent) {
                      parent.innerHTML = `
                        <div class="w-full h-full bg-gray-600 flex items-center justify-center">
                          <svg class="w-3 h-3 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                            <path d="M4 4h16v16H4V4zm2 2v12h12V6H6zm3 4l2 2.5L14 9l4 5H6l3-4z"/>
                          </svg>
                        </div>
                      `
                    }
                  }}
                />
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-mono text-sm">
                  @{reference.tag}
                </div>
                {reference.display_name && (
                  <div className="text-xs opacity-75 truncate">
                    {reference.display_name}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
      
      {!isLoading && filteredReferences.length > 0 && (
        <div className="border-t border-gray-700 px-3 py-2 text-xs text-gray-500">
          Use ↑↓ to navigate, Enter to select, Esc to close
        </div>
      )}
    </div>
  )
}