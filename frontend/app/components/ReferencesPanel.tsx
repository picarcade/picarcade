'use client'

import React, { useState, useEffect, useRef } from 'react'
import { X, Tag, Search, Trash2, Upload, Image as ImageIcon, Edit3, Camera } from 'lucide-react'
import { getUserReferences, createReference, deleteReference, updateReference, uploadImage } from '../lib/api'
import type { Reference } from '../types'
import ShareButton from './ShareButton'

interface ReferencesPanelProps {
  isOpen: boolean
  onClose: () => void
  userId: string
  onReferenceSelect?: (tag: string) => void
}



export default function ReferencesPanel({ isOpen, onClose, userId, onReferenceSelect }: ReferencesPanelProps) {
  const [references, setReferences] = useState<Reference[]>([])
  const [searchTerm, setSearchTerm] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [editingReference, setEditingReference] = useState<Reference | null>(null)
  const [newReference, setNewReference] = useState({
    tag: '',
    imageUrl: ''
  })
  
  // New state for upload and camera functionality
  const [isUploading, setIsUploading] = useState(false)
  const [showCamera, setShowCamera] = useState(false)
  const [stream, setStream] = useState<MediaStream | null>(null)
  
  const fileInputRef = useRef<HTMLInputElement>(null)
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (isOpen && userId) {
      loadReferences()
    }
  }, [isOpen, userId])

  const loadReferences = async () => {
    setIsLoading(true)
    try {
      const data = await getUserReferences(userId)
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
        undefined, // no display name
        undefined, // no description
        'general' // default category
      )
      
      setNewReference({
        tag: '',
        imageUrl: ''
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
    setEditingReference({ ...reference, originalTag: reference.tag } as Reference & { originalTag: string })
  }

  const handleUpdateReference = async () => {
    if (!editingReference) return

    // Validate tag length if it's being changed
    if (editingReference.tag && editingReference.tag.length < 3) {
      alert('Tag must be at least 3 characters long')
      return
    }

    try {
      const originalTag = (editingReference as Reference & { originalTag?: string }).originalTag || editingReference.tag
      const newTag = editingReference.tag !== originalTag ? editingReference.tag : undefined
      
      await updateReference(
        userId,
        originalTag, // original tag
        newTag, // new tag (only if changed)
        undefined, // no display name
        undefined, // no description
        'general' // default category
      )
      
      setEditingReference(null)
      loadReferences()
    } catch (error) {
      console.error('Failed to update reference:', error)
      alert('Failed to update reference')
    }
  }

  // Upload image function
  const handleImageUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsUploading(true)
    try {
      const uploadResult = await uploadImage(file, `reference_${Date.now()}`)
      setNewReference(prev => ({
        ...prev,
        imageUrl: uploadResult.public_url
      }))
      setShowAddForm(true)
    } catch (error) {
      console.error('Failed to upload image:', error)
      alert('Failed to upload image')
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  // Camera functions
  const startCamera = async () => {
    try {
      // Check if navigator.mediaDevices is available
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error('Camera API not supported in this browser')
      }

      // Check if we're in a secure context (HTTPS required for camera access)
      if (!window.isSecureContext) {
        throw new Error('Camera access requires HTTPS. Please use https:// or localhost')
      }

      console.log('Requesting camera access...')
      const mediaStream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 }
        } 
      })
      
      console.log('Camera access granted, setting up stream...')
      setStream(mediaStream)
      setShowCamera(true)
      
      // Wait a bit for the modal to render before setting video source
      setTimeout(() => {
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream
          videoRef.current.onloadedmetadata = () => {
            console.log('Video metadata loaded, camera ready')
          }
        }
      }, 100)
      
    } catch (error) {
      console.error('Failed to access camera:', error)
      
      let errorMessage = 'Failed to access camera. '
      
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError') {
          errorMessage += 'Please allow camera access and try again.'
        } else if (error.name === 'NotFoundError') {
          errorMessage += 'No camera found on this device.'
        } else if (error.name === 'NotSupportedError') {
          errorMessage += 'Camera not supported in this browser.'
        } else if (error.name === 'NotReadableError') {
          errorMessage += 'Camera is already in use by another application.'
        } else if (error.message.includes('HTTPS')) {
          errorMessage += 'Camera access requires HTTPS. Please use https:// or localhost.'
        } else {
          errorMessage += 'Please ensure camera permissions are granted and try again.'
        }
      } else {
        errorMessage += 'Please ensure camera permissions are granted and try again.'
      }
      
      alert(errorMessage)
    }
  }

  const stopCamera = () => {
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      setStream(null)
    }
    setShowCamera(false)
  }

  const capturePhoto = async () => {
    if (!videoRef.current || !canvasRef.current) return

    const canvas = canvasRef.current
    const video = videoRef.current
    const context = canvas.getContext('2d')
    
    if (!context) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    context.drawImage(video, 0, 0)

    // Convert canvas to blob
    canvas.toBlob(async (blob) => {
      if (!blob) return

      setIsUploading(true)
      try {
        const file = new File([blob], `selfie_${Date.now()}.jpg`, { type: 'image/jpeg' })
        const uploadResult = await uploadImage(file, `selfie_${Date.now()}`)
        
        setNewReference(prev => ({
          ...prev,
          imageUrl: uploadResult.public_url
        }))
        setShowAddForm(true)
        stopCamera()
      } catch (error) {
        console.error('Failed to upload selfie:', error)
        alert('Failed to upload selfie')
      } finally {
        setIsUploading(false)
      }
    }, 'image/jpeg', 0.8)
  }

  // Cleanup camera stream when component unmounts or closes
  React.useEffect(() => {
    if (!isOpen && stream) {
      stopCamera()
    }
  }, [isOpen, stream])

  const handleReferenceClick = (tag: string) => {
    if (onReferenceSelect) {
      onReferenceSelect(`@${tag}`)
    }
  }

  const filteredReferences = references.filter(ref => 
    ref.tag.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-gray-800 rounded-2xl w-full max-w-4xl max-h-[80vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          <div className="flex items-center gap-2">
            <Tag className="w-6 h-6 text-purple-400" />
            <h2 className="text-xl font-semibold text-white">Tagged Images</h2>
            <span className="text-sm text-gray-400">({filteredReferences.length})</span>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-400" />
          </button>
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between p-6 border-b border-gray-700">
          {/* Search */}
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-500" />
            <input
              type="text"
              placeholder="Search tagged images..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
            />
          </div>

          {/* Action Icons */}
          <div className="flex items-center gap-1 ml-4">
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={isUploading}
              className="p-1 hover:bg-gray-700 rounded-lg transition-colors relative"
              title={isUploading ? 'Uploading...' : 'Upload image'}
            >
              <Upload className="w-5 h-5 text-purple-400 hover:text-purple-300" />
            </button>
            <button
              onClick={() => {
                console.log('Camera button clicked in ReferencesPanel')
                startCamera()
              }}
              disabled={isUploading || showCamera}
              className="p-1 hover:bg-gray-700 rounded-lg transition-colors relative"
              title="Take selfie"
            >
              <Camera className="w-5 h-5 text-green-400 hover:text-green-300" />
            </button>
          </div>
        </div>

        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          onChange={handleImageUpload}
          className="hidden"
        />

        {/* Camera Modal */}
        {showCamera && (
          <div className="absolute inset-0 bg-black/90 flex items-center justify-center z-10 rounded-2xl">
            <div className="bg-gray-800 p-6 rounded-lg max-w-md w-full mx-4">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Take a Selfie</h3>
                <button
                  onClick={stopCamera}
                  className="p-1 hover:bg-gray-700 rounded transition-colors"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>
              
              <div className="space-y-4">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  className="w-full h-64 bg-gray-900 rounded-lg object-cover"
                />
                
                <div className="flex gap-2">
                  <button
                    onClick={capturePhoto}
                    disabled={isUploading}
                    className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {isUploading ? 'Processing...' : 'Capture Photo'}
                  </button>
                  <button
                    onClick={stopCamera}
                    className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Hidden canvas for photo capture */}
        <canvas ref={canvasRef} className="hidden" />

        {/* Add Form */}
        {showAddForm && (
          <div className="p-6 border-b border-gray-700 bg-gray-900">
            <h3 className="text-lg font-medium mb-4 text-white">Add New Reference</h3>
            
            <div className="space-y-4">
              {/* Image preview */}
              {newReference.imageUrl && (
                <div>
                  <img
                    src={newReference.imageUrl}
                    alt="Preview"
                    className="w-32 h-32 object-cover rounded-lg border border-gray-600 mx-auto"
                  />
                </div>
              )}
              
              {/* Tag Name */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Tag Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={newReference.tag}
                  onChange={(e) => setNewReference(prev => ({ ...prev, tag: e.target.value }))}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-purple-500"
                  placeholder="e.g., hero, castle, dragon"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Must be at least 3 characters
                </p>
              </div>
            </div>
            
            <div className="flex gap-2 mt-4">
              <button
                onClick={handleCreateReference}
                disabled={!newReference.tag || !newReference.imageUrl}
                className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Create Reference
              </button>
              <button
                onClick={() => {
                  setShowAddForm(false)
                  setNewReference({
                    tag: '',
                    imageUrl: ''
                  })
                }}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-500 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Edit Form */}
        {editingReference && (
          <div className="p-6 border-b border-gray-700 bg-gray-900">
            <h3 className="text-lg font-medium mb-4 text-white">Edit Reference @{editingReference.tag}</h3>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-1">
                  Tag Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={editingReference.tag || ''}
                  onChange={(e) => setEditingReference(prev => prev ? { ...prev, tag: e.target.value } : null)}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:ring-2 focus:ring-purple-500"
                  placeholder="e.g., hero, castle, dragon"
                />
                <p className="text-xs text-gray-400 mt-1">
                  Must be at least 3 characters
                </p>
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
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-500 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
            </div>
          ) : filteredReferences.length === 0 ? (
            <div className="text-center py-12">
              <ImageIcon className="w-12 h-12 text-gray-500 mx-auto mb-4" />
              <p className="text-gray-300">
                {searchTerm ? 'No tagged images match your search' : 'No tagged images yet'}
              </p>
              <p className="text-sm text-gray-500 mt-2">
                Use the Upload or Take Selfie buttons above to add your first reference
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {filteredReferences.map(reference => (
                <div
                  key={reference.id}
                  className="group relative bg-gray-700 border border-gray-600 rounded-lg overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
                  onClick={() => handleReferenceClick(reference.tag)}
                >
                  <div className="aspect-square relative">
                    <img
                      src={reference.image_url}
                      alt={reference.display_name || reference.tag}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        const target = e.target as HTMLImageElement
                        target.style.display = 'none'
                        const parent = target.parentElement
                        if (parent) {
                          parent.innerHTML = `
                            <div class="w-full h-full bg-gray-600 flex items-center justify-center">
                              <svg class="w-8 h-8 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                                <path d="M4 4h16v16H4V4zm2 2v12h12V6H6zm3 4l2 2.5L14 9l4 5H6l3-4z"/>
                              </svg>
                            </div>
                          `
                        }
                      }}
                    />
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-20 transition-all" />
                    
                    {/* Action buttons */}
                    <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <ShareButton 
                        url={reference.image_url}
                        title={`Check out this reference image: @${reference.tag}`}
                        isVideo={false}
                        size="sm"
                      />
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
                    <div className="flex items-center justify-center">
                      <span className="text-sm font-mono text-purple-400">@{reference.tag}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-700 p-4">
          <div className="flex items-center justify-center">
            <p className="text-gray-400 text-sm">
              Click on any reference to add it to your prompt. Upload images or take selfies to create new references.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
} 