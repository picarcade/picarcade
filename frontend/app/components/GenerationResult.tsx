"use client"
import { useState } from 'react'
import { CheckCircle, XCircle, Eye, Copy, Save, Clock } from 'lucide-react'
import Image from 'next/image'
import type { GenerationResultProps } from '../types'

export default function GenerationResult({ result, isGenerating }: GenerationResultProps) {
  const [imageLoaded, setImageLoaded] = useState(false)

  if (isGenerating) {
    return (
      <div className="bg-white rounded-xl shadow-lg p-6">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 border-2 border-purple-600 border-t-transparent rounded-full animate-spin" />
          <h3 className="text-xl font-semibold text-gray-900">Generating Content...</h3>
        </div>
        {/* Animated Placeholder */}
        <div className="space-y-3">
          <div className="h-4 bg-gray-200 rounded animate-pulse" />
          <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4" />
          <div className="h-64 bg-gray-200 rounded animate-pulse" />
        </div>
        <div className="mt-4 text-sm text-gray-600">
          ✨ AI is creating your content with intelligent model selection...
        </div>
      </div>
    )
  }

  if (!result) return null

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <div className="flex items-center gap-3 mb-4">
        {result.success ? (
          <CheckCircle className="w-8 h-8 text-green-600" />
        ) : (
          <XCircle className="w-8 h-8 text-red-600" />
        )}
        <h3 className="text-xl font-semibold text-gray-900">
          {result.success ? 'Generation Complete!' : 'Generation Failed'}
        </h3>
      </div>

      {result.success && result.output_url ? (
        <div className="space-y-4">
          {/* Generated Content */}
          <div className="relative bg-gray-100 rounded-lg overflow-hidden">
            {result.output_url.includes('.mp4') || result.output_url.includes('video') ? (
              <video
                src={result.output_url}
                controls
                className="w-full h-auto max-h-96 object-contain"
              >
                Your browser does not support video playback.
              </video>
            ) : (
              <div className="relative">
                <Image
                  src={result.output_url}
                  alt="Generated content"
                  width={800}
                  height={600}
                  className="w-full h-auto max-h-96 object-contain"
                  onLoad={() => setImageLoaded(true)}
                />
                {!imageLoaded && (
                  <div className="absolute inset-0 bg-gray-200 animate-pulse flex items-center justify-center">
                    <Eye className="w-8 h-8 text-gray-400" />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => window.open(result.output_url, '_blank')}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
            >
              <Eye className="w-4 h-4" />
              View Full Size
            </button>
            <button
              onClick={() => navigator.clipboard.writeText(result.output_url!)}
              className="flex items-center gap-2 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
            >
              <Copy className="w-4 h-4" />
              Copy URL
            </button>
            <button
              onClick={() => {/* Future: Save to references */}}
              className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
            >
              <Save className="w-4 h-4" />
              Save
            </button>
          </div>

          {/* Metadata */}
          <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Model Used:</span>
              <span className="font-medium">{result.model_used}</span>
            </div>
            {result.execution_time && (
              <div className="flex justify-between">
                <span className="text-gray-600">Generation Time:</span>
                <span className="font-medium flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {result.execution_time.toFixed(1)}s
                </span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-gray-600">Generation ID:</span>
              <span className="font-mono text-xs">{result.generation_id}</span>
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-red-800">
            {result.error_message || 'An unknown error occurred during generation.'}
          </p>
        </div>
      )}
    </div>
  )
} 