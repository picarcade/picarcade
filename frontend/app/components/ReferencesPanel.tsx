'use client'

import React, { useState, useEffect } from 'react'
import { X, Plus, Tag, Search, Trash2, Upload, Image as ImageIcon, Edit3 } from 'lucide-react'
import { getUserReferences, createReference, deleteReference, updateReference } from '../lib/api'
import type { Reference } from '../types'

interface ReferencesPanelProps {
  isOpen: boolean
  onClose: () => void
  userId: string
  onReferenceSelect?: (tag: string) => void
}

const CATEGORIES = [
  { name: 'all', color: '#6b7280', label: 'All' },
  { name: 'characters', color: '#8b5cf6', label: 'Characters' },
  { name: 'locations', color: '#10b981', label: 'Locations' },
  { name: 'objects', color: '#f59e0b', label: 'Objects' },
  { name: 'styles', color: '#ef4444', label: 'Styles' },
  { name: 'general', color: '#6366f1', label: 'General' }
]

export default function ReferencesPanel({ isOpen, onClose, userId, onReferenceSelect }: ReferencesPanelProps) {
  const [references, setReferences] = useState<Reference[]>([])
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingReference, setEditingReference] = useState<Reference | null>(null)
  const [newReference, setNewReference] = useState({
    tag: '',
    imageUrl: '',
    displayName: '',
    description: '',
    category: 'general'
  })

  useEffect(() => {
    if (isOpen && userId) {
      loadReferences()
    }
  }, [isOpen, userId, selectedCategory])

  const loadReferences = async () => {
    setIsLoading(true)
    try {
      const data = await getUserReferences(userId, selectedCategory)
      setReferences(data)
    } catch (error) {
      console.error('Failed to load references:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreateReference = async () => {
    if (!newReference.tag || !newReference.imageUrl) {
      alert('Tag and image URL are required')
      return
    }

    try {
      await createReference(
        userId,
        newReference.tag,
        newReference.imageUrl,
        newReference.displayName || undefined,
        newReference.description || undefined,
        newReference.category
      )
      
      setNewReference({
        tag: '',
        imageUrl: '',
        displayName: '',
        description: '',
        category: 'general'
      })
      setShowAddForm(false)
      loadReferences()
    } catch (error) {
      console.error('Failed to create reference:', error)
      alert('Failed to create reference. Tag might already exist.')
    }
  }

  const handleDeleteReference = async (tag: string) => {
    if (!confirm(`Delete reference @${tag}?`)) return

    try {
      await deleteReference(userId, tag)
      loadReferences()
    } catch (error) {
      console.error('Failed to delete reference:', error)
      alert('Failed to delete reference')
    }
  }

  const handleEditReference = (reference: Reference) => {
    // Store the original tag so we can update properly
    setEditingReference({ ...reference, originalTag: reference.tag } as any)
  }

  const handleUpdateReference = async () => {
    if (!editingReference) return

    // Validate tag length if it's being changed
    if (editingReference.tag && editingReference.tag.length < 3) {
      alert('Tag must be at least 3 characters long')
      return
    }

    try {
      const originalTag = (editingReference as any).originalTag || editingReference.tag
      const newTag = editingReference.tag !== originalTag ? editingReference.tag : undefined
      
      await updateReference(
        userId,
        originalTag, // original tag
        newTag, // new tag (only if changed)
        editingReference.display_name || undefined,
        editingReference.description || undefined,
        editingReference.category
      )
      
      setEditingReference(null)
      loadReferences()
    } catch (error) {
      console.error('Failed to update reference:', error)
      alert('Failed to update reference')
    }
  }

  const handleReferenceClick = (tag: string) => {
    if (onReferenceSelect) {
      onReferenceSelect(`@${tag}`)
    }
  }

  const filteredReferences = references.filter(ref => 
    ref.tag.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ref.display_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    ref.description?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-4xl h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <div className="flex items-center gap-2">
            <Tag className="w-5 h-5 text-purple-600" />
            <h2 className="text-xl font-semibold">Tagged Images</h2>
            <span className="text-sm text-gray-500">({filteredReferences.length})</span>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Controls */}
        <div className="p-4 border-b space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search references..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>

          {/* Categories */}
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map(category => (
              <button
                key={category.name}
                onClick={() => setSelectedCategory(category.name)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  selectedCategory === category.name
                    ? 'text-white'
                    : 'text-gray-600 hover:text-gray-800'
                }`}
                style={{
                  backgroundColor: selectedCategory === category.name ? category.color : '#f3f4f6'
                }}
              >
                {category.label}
              </button>
            ))}
          </div>

          {/* Info */}
          <div className="text-sm text-gray-600">
            💡 Tagged images can be referenced in prompts using @tagname
          </div>
        </div>

        {/* Edit Form */}
        {editingReference && (
          <div className="p-4 border-b bg-gray-50">
            <h3 className="text-lg font-medium mb-4">Edit Reference @{editingReference.tag}</h3>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Tag Name <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={editingReference.tag || ''}
                  onChange={(e) => setEditingReference(prev => prev ? { ...prev, tag: e.target.value } : null)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  placeholder="e.g., hero, castle, dragon"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Must be at least 3 characters
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  value={editingReference.display_name || ''}
                  onChange={(e) => setEditingReference(prev => prev ? { ...prev, display_name: e.target.value } : null)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Category
                </label>
                <select
                  value={editingReference.category}
                  onChange={(e) => setEditingReference(prev => prev ? { ...prev, category: e.target.value } : null)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                >
                  {CATEGORIES.slice(1).map(category => (
                    <option key={category.name} value={category.name}>
                      {category.label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Description
                </label>
                <textarea
                  value={editingReference.description || ''}
                  onChange={(e) => setEditingReference(prev => prev ? { ...prev, description: e.target.value } : null)}
                  className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-purple-500"
                  rows={2}
                />
              </div>
            </div>
            <div className="flex gap-2 mt-4">
              <button
                onClick={handleUpdateReference}
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                Save Changes
              </button>
              <button
                onClick={() => setEditingReference(null)}
                className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* References Grid */}
        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-600"></div>
            </div>
          ) : filteredReferences.length === 0 ? (
            <div className="text-center py-12">
              <ImageIcon className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">
                {searchTerm ? 'No tagged images match your search' : 'No tagged images yet'}
              </p>
              <p className="text-sm text-gray-400 mt-2">
                Tag images using the Tag icon on any image to create references
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {filteredReferences.map(reference => (
                <div
                  key={reference.id}
                  className="group relative bg-white border rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => handleReferenceClick(reference.tag)}
                >
                  <div className="aspect-square relative">
                    <img
                      src={reference.image_url}
                      alt={reference.display_name || reference.tag}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement
                        target.src = '/placeholder-image.png'
                      }}
                    />
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all" />
                    
                    {/* Action buttons */}
                    <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleEditReference(reference)
                        }}
                        className="p-1 bg-blue-500 text-white rounded-full hover:bg-blue-600"
                        title="Edit reference"
                      >
                        <Edit3 className="w-3 h-3" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDeleteReference(reference.tag)
                        }}
                        className="p-1 bg-red-500 text-white rounded-full hover:bg-red-600"
                        title="Delete reference"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  </div>
                  
                  <div className="p-3">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-mono text-purple-600">@{reference.tag}</span>
                      <span
                        className="px-2 py-0.5 text-xs rounded-full text-white"
                        style={{ backgroundColor: CATEGORIES.find(c => c.name === reference.category)?.color }}
                      >
                        {CATEGORIES.find(c => c.name === reference.category)?.label}
                      </span>
                    </div>
                    {reference.display_name && (
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {reference.display_name}
                      </p>
                    )}
                    {reference.description && (
                      <p className="text-xs text-gray-500 line-clamp-2 mt-1">
                        {reference.description}
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50">
          <p className="text-sm text-gray-600">
            💡 <strong>Tip:</strong> Click on any reference to add @{filteredReferences[0]?.tag || 'tag'} to your prompt. 
            References automatically use Runway's gen4_image model for best quality.
          </p>
        </div>
      </div>
    </div>
  )
} 