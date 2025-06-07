"use client"
import { useState, useEffect, useRef } from 'react'
import { History, Wand2, CheckCircle, XCircle, Clock, ChevronLeft, ChevronRight, ExternalLink } from 'lucide-react'
import type { GenerationHistoryProps, HistoryItem } from '../types'
import { getUserHistory } from '../lib/api'

export default function GenerationHistory({ refreshTrigger, userId, onSelectImage }: GenerationHistoryProps) {
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [loading, setLoading] = useState(true)
  const [currentPage, setCurrentPage] = useState(0)
  const carouselRef = useRef<HTMLDivElement>(null)
  const touchStartX = useRef<number>(0)
  const touchEndX = useRef<number>(0)

  const itemsPerPage = 3
  const totalPages = Math.ceil(history.length / itemsPerPage)

  useEffect(() => {
    // Load history when component mounts or refreshTrigger changes
    loadHistory()
  }, [refreshTrigger, userId])

  const loadHistory = async () => {
    setLoading(true)
    try {
      // Use the API utility function to fetch history with correct base URL
      const historyData = await getUserHistory(userId, 50)
      setHistory(historyData)
    } catch (error) {
      console.error('Error loading history:', error)
      setHistory([]) // Set empty array on error
    } finally {
      setLoading(false)
    }
  }

  const formatTimeAgo = (dateString: string) => {
    const date = new Date(dateString)
    const now = new Date()
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

    if (diffInSeconds < 60) return 'Just now'
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`
    return `${Math.floor(diffInSeconds / 86400)}d ago`
  }

  const nextPage = () => {
    if (currentPage < totalPages - 1) {
      setCurrentPage(currentPage + 1)
    }
  }

  const prevPage = () => {
    if (currentPage > 0) {
      setCurrentPage(currentPage - 1)
    }
  }

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX
  }

  const handleTouchMove = (e: React.TouchEvent) => {
    touchEndX.current = e.touches[0].clientX
  }

  const handleTouchEnd = () => {
    const swipeThreshold = 50
    const swipeDistance = touchStartX.current - touchEndX.current

    if (Math.abs(swipeDistance) > swipeThreshold) {
      if (swipeDistance > 0) {
        // Swipe left - next page
        nextPage()
      } else {
        // Swipe right - previous page
        prevPage()
      }
    }
  }

  const getCurrentPageItems = () => {
    const startIndex = currentPage * itemsPerPage
    return history.slice(startIndex, startIndex + itemsPerPage)
  }

  const handleImageClick = (item: HistoryItem) => {
    if (onSelectImage) {
      // Call the callback to select the image for editing
      onSelectImage(item)
    } else if (item.output_url) {
      // Default behavior - open in new tab
      window.open(item.output_url, '_blank')
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center gap-2">
        <History className="w-5 h-5 text-gray-600" />
        Recent Generations
      </h3>

      {loading ? (
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="animate-pulse flex gap-4">
              <div className="w-24 h-24 bg-gray-200 rounded-lg" />
              <div className="flex-1">
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="h-3 bg-gray-200 rounded w-1/2" />
              </div>
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
        <div className="relative">
          {/* Navigation arrows */}
          {totalPages > 1 && (
            <>
              <button
                onClick={prevPage}
                disabled={currentPage === 0}
                className={`absolute left-0 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full transition-colors ${
                  currentPage === 0
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-white shadow-lg text-gray-600 hover:bg-gray-50 hover:text-gray-800'
                }`}
                aria-label="Previous page"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              
              <button
                onClick={nextPage}
                disabled={currentPage === totalPages - 1}
                className={`absolute right-0 top-1/2 -translate-y-1/2 z-10 p-2 rounded-full transition-colors ${
                  currentPage === totalPages - 1
                    ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                    : 'bg-white shadow-lg text-gray-600 hover:bg-gray-50 hover:text-gray-800'
                }`}
                aria-label="Next page"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </>
          )}

          {/* Carousel container */}
          <div
            ref={carouselRef}
            className="mx-8 overflow-hidden" // Add margin for arrow space
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {getCurrentPageItems().map((item) => (
                <div
                  key={item.generation_id}
                  className="group relative bg-gray-50 rounded-lg border border-gray-200 overflow-hidden hover:shadow-md transition-all duration-300 cursor-pointer"
                  onClick={() => handleImageClick(item)}
                >
                  {/* Image thumbnail */}
                  <div className="aspect-square relative overflow-hidden bg-gray-100">
                    {item.output_url ? (
                      <>
                        <img
                          src={item.output_url}
                          alt={item.prompt}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement
                            target.style.display = 'none'
                            target.parentElement?.classList.add('flex', 'items-center', 'justify-center')
                            target.parentElement!.innerHTML = '<div class="w-8 h-8 text-gray-400"><svg fill="currentColor" viewBox="0 0 24 24"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg></div>'
                          }}
                        />
                        {/* Status indicator */}
                        <div className="absolute top-2 left-2">
                          {item.success === 'success' ? (
                            <CheckCircle className="w-4 h-4 text-green-600 bg-white rounded-full" />
                          ) : (
                            <XCircle className="w-4 h-4 text-red-600 bg-white rounded-full" />
                          )}
                        </div>
                        {/* Action icon on hover */}
                        <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity">
                          {onSelectImage ? (
                            <div className="w-6 h-6 bg-blue-500 text-white rounded-full flex items-center justify-center text-xs font-bold">
                              ✓
                            </div>
                          ) : (
                            <ExternalLink className="w-4 h-4 text-white bg-black bg-opacity-50 rounded p-0.5" />
                          )}
                        </div>
                      </>
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-gray-400">
                        <Wand2 className="w-8 h-8" />
                      </div>
                    )}
                  </div>

                  {/* Content overlay */}
                  <div className="p-3">
                    <p className="text-sm text-gray-900 line-clamp-2 mb-2 font-medium">
                      {item.prompt}
                    </p>
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <span className="bg-gray-100 px-2 py-1 rounded truncate max-w-20">
                        {item.model_used?.replace(/_/g, ' ') || 'Unknown'}
                      </span>
                      <div className="flex items-center gap-1">
                        {item.execution_time && (
                          <>
                            <Clock className="w-3 h-3" />
                            <span>{(item.execution_time / 1000).toFixed(1)}s</span>
                          </>
                        )}
                      </div>
                    </div>
                    <div className="text-xs text-gray-400 mt-1">
                      {formatTimeAgo(item.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Page indicators */}
          {totalPages > 1 && (
            <div className="flex justify-center mt-4 gap-1">
              {[...Array(totalPages)].map((_, index) => (
                <button
                  key={index}
                  onClick={() => setCurrentPage(index)}
                  className={`w-2 h-2 rounded-full transition-colors ${
                    currentPage === index ? 'bg-blue-600' : 'bg-gray-300'
                  }`}
                  aria-label={`Go to page ${index + 1}`}
                />
              ))}
            </div>
          )}

          {/* Results summary */}
          <div className="mt-4 text-center text-sm text-gray-500">
            Showing {getCurrentPageItems().length} of {history.length} generations
            {totalPages > 1 && ` (Page ${currentPage + 1} of ${totalPages})`}
          </div>
        </div>
      )}
    </div>
  )
} 