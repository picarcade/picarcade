'use client'

import React, { useState, useEffect } from 'react'
import { X, Tag, Save } from 'lucide-react'
import { createReference, getUserReferences } from '../lib/api'


interface TagImageModalProps {
  isOpen: boolean
  onClose: () => void
  imageUrl: string
  userId: string
  onTagged?: (tag: string) => void
  initialTag?: string
}

export default function TagImageModal({ isOpen, onClose, imageUrl, userId, onTagged, initialTag }: TagImageModalProps) {
  const [tagName, setTagName] = useState(initialTag || '')
  const [isLoading, setIsLoading] = useState(false)
  const [existingTags, setExistingTags] = useState<string[]>([])

  useEffect(() => {
    if (isOpen && userId) {
      loadExistingTags()
    }
  }, [isOpen, userId])

  useEffect(() => {
    setTagName(initialTag || '')
  }, [initialTag])

  const loadExistingTags = async () => {
    try {
      const references = await getUserReferences(userId)
      setExistingTags(references.map(ref => ref.tag.toLowerCase()))
    } catch (error) {
      console.error('Failed to load existing tags:', error)
    }
  }

  const generateUniqueTag = (baseTag: string): string => {
    const cleanTag = baseTag.toLowerCase().replace(/[^a-z0-9]/g, '').substring(0, 20)
    
    if (!existingTags.includes(cleanTag)) {
      return cleanTag
    }

    let counter = 1
    let uniqueTag = `${cleanTag}${counter}`
    
    while (existingTags.includes(uniqueTag)) {
      counter++
      uniqueTag = `${cleanTag}${counter}`
    }
    
    return uniqueTag
  }

  const handleSave = async () => {
    if (!tagName.trim()) {
      alert('Tag name is required')
      return
    }

    if (tagName.trim().length < 3) {
      alert('Tag name must be at least 3 characters long')
      return
    }

    setIsLoading(true)
    try {
      const uniqueTag = generateUniqueTag(tagName)
      
      await createReference(
        userId,
        uniqueTag,
        imageUrl,
        tagName, // Use tagName as display name
        undefined, // No description
        'general' // Default category
      )
      
      if (onTagged) {
        onTagged(uniqueTag)
      }
      
      // Reset form
      setTagName('')
      onClose()
    } catch (error) {
      console.error('Failed to tag image:', error)
      alert('Failed to tag image. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleClose = () => {
    setTagName('')
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Tag className="w-5 h-5 text-purple-600" />
            <h2 className="text-lg font-semibold">{initialTag ? 'Edit Tag' : 'Tag Image'}</h2>
          </div>
          <button
            onClick={handleClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
            disabled={isLoading}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Image Preview */}
          <div className="relative">
            <img
              src={imageUrl}
              alt="Image to tag"
              className="w-full h-32 object-cover rounded-lg border"
              onError={(e) => {
                const target = e.target as HTMLImageElement
                target.style.display = 'none'
                const parent = target.parentElement
                if (parent) {
                  parent.innerHTML = `
                    <div class="w-full h-full bg-gray-200 flex items-center justify-center">
                      <svg class="w-8 h-8 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M4 4h16v16H4V4zm2 2v12h12V6H6zm3 4l2 2.5L14 9l4 5H6l3-4z"/>
                      </svg>
                    </div>
                  `
                }
              }}
            />
          </div>

          {/* Tag Name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Name <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={tagName}
              onChange={(e) => setTagName(e.target.value)}
              placeholder="e.g., hero, castle, dragon"
              className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
              disabled={isLoading}
            />
            <p className="text-xs text-gray-500 mt-1">
              Must be at least 3 characters. Will be auto-adjusted if name exists (e.g., hero → hero1, hero2)
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex gap-3 p-4 border-t">
          <button
            onClick={handleClose}
            className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
            disabled={isLoading}
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={!tagName.trim() || isLoading}
            className="flex-1 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-colors"
          >
            {isLoading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <Save className="w-4 h-4" />
                {initialTag ? 'Update Tag' : 'Tag Image'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
} 