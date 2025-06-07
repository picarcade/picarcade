"use client"
import { useState } from 'react'
import { Wand2, Zap, Gauge, Crown } from 'lucide-react'
import type { GenerationFormProps } from '../types'
import { getOrCreateUserId } from '../lib/userUtils'

export default function GenerationForm({ 
  onGenerationStart, 
  onGenerationComplete, 
  isGenerating 
}: GenerationFormProps) {
  const [prompt, setPrompt] = useState('')
  const [qualityPriority, setQualityPriority] = useState<'speed' | 'balanced' | 'quality'>('balanced')
  const [userId] = useState(() => getOrCreateUserId())

  const qualityOptions = [
    { 
      value: 'speed', 
      label: 'Speed', 
      icon: Zap, 
      description: 'Fast generation, good quality',
      time: '~15s'
    },
    { 
      value: 'balanced', 
      label: 'Balanced', 
      icon: Gauge, 
      description: 'Optimal speed/quality balance',
      time: '~30s'
    },
    { 
      value: 'quality', 
      label: 'Quality', 
      icon: Crown, 
      description: 'Best quality, slower generation',
      time: '~60s'
    }
  ] as const

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!prompt.trim() || isGenerating) return
    onGenerationStart()
    // You would call generateContent here and then onGenerationComplete
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h2 className="text-2xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
        <Wand2 className="w-6 h-6 text-purple-600" />
        Create Content
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Prompt Input */}
        <div>
          <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-2">
            Describe what you want to create
          </label>
          <textarea
            id="prompt"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="A beautiful sunset over mountains, cinematic quality..."
            className="w-full h-32 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent resize-none"
            disabled={isGenerating}
          />
          <div className="mt-2 flex justify-between text-sm text-gray-500">
            <span>Be specific for better results</span>
            <span>{prompt.length}/500</span>
          </div>
        </div>

        {/* Quality Priority */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-3">
            Quality Priority
          </label>
          <div className="grid grid-cols-3 gap-3">
            {qualityOptions.map(({ value, label, icon: Icon, description, time }) => (
              <button
                key={value}
                type="button"
                onClick={() => setQualityPriority(value)}
                className={`p-4 border-2 rounded-lg transition-all ${
                  qualityPriority === value
                    ? 'border-purple-500 bg-purple-50 text-purple-700'
                    : 'border-gray-200 hover:border-gray-300'
                }`}
                disabled={isGenerating}
              >
                <Icon className="w-6 h-6 mx-auto mb-2" />
                <div className="text-sm font-medium">{label}</div>
                <div className="text-xs text-gray-500 mt-1">{description}</div>
                <div className="text-xs text-purple-600 mt-1">{time}</div>
              </button>
            ))}
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!prompt.trim() || isGenerating}
          className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 px-6 rounded-lg font-medium transition-all hover:from-purple-700 hover:to-pink-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
        >
          {isGenerating ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Wand2 className="w-5 h-5" />
              Generate Content
            </>
          )}
        </button>
      </form>
    </div>
  )
} 