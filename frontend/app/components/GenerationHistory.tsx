"use client"
import { useState } from 'react'
import { History, Wand2, CheckCircle, XCircle, Clock } from 'lucide-react'
import type { GenerationHistoryProps, HistoryItem } from '../types'

export default function GenerationHistory({ refreshTrigger }: GenerationHistoryProps) {
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [userId] = useState(() => `user_${Math.random().toString(36).substr(2, 9)}`)

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (diffInSeconds < 60) return 'Just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
    return `${Math.floor(diffInSeconds / 86400)}d ago`
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <History className="w-5 h-5 text-gray-600" />
        Recent Generations
      </h3>

      {loading ? (
        <div className="space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
              <div className="h-3 bg-gray-200 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : history.length === 0 ? (
        <div className="text-center py-8">
          <Wand2 className="w-12 h-12 text-gray-300 mx-auto mb-4" />
          <p className="text-gray-500">No generations yet</p>
          <p className="text-sm text-gray-400">Your history will appear here</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {history.map((item) => (
            <div
              key={item.generation_id}
              className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50 transition-colors cursor-pointer"
              onClick={() => item.output_url && window.open(item.output_url, '_blank')}
            >
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 mt-1">
                  {item.success === 'success' ? (
                    <CheckCircle className="w-4 h-4 text-green-600" />
                  ) : (
                    <XCircle className="w-4 h-4 text-red-600" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-900 line-clamp-2 mb-1">
                    {item.prompt}
                  </p>
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span className="bg-gray-100 px-2 py-1 rounded">
                      {item.model_used?.replace(/_/g, ' ')}
                    </span>
                    {item.execution_time && (
                      <div className="flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        {(item.execution_time / 1000).toFixed(1)}s
                      </div>
                    )}
                    <span>{formatTimeAgo(item.created_at)}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
} 