'use client'

import React, { useState, useEffect, useRef, useCallback } from 'react'
import ReferenceDropdown from './ReferenceDropdown'
import { getUserReferences } from '../lib/api'
import type { Reference } from '../types'

interface ReferenceInputProps {
  value: string
  onChange: (value: string) => void
  onKeyPress?: (e: React.KeyboardEvent) => void
  placeholder?: string
  disabled?: boolean
  userId: string
  className?: string
  // Add any other input props you need
  type?: string
}

export default function ReferenceInput({
  value,
  onChange,
  onKeyPress,
  placeholder,
  disabled,
  userId,
  className,
  type = "text",
  ...props
}: ReferenceInputProps) {
  const [showDropdown, setShowDropdown] = useState(false)
  const [dropdownPosition, setDropdownPosition] = useState({ top: 0, left: 0 })
  const [searchTerm, setSearchTerm] = useState('')
  const [currentMentionStart, setCurrentMentionStart] = useState(-1)
  const [cursorPosition, setCursorPosition] = useState(0)
  const [validReferences, setValidReferences] = useState<Set<string>>(new Set())
  
  const inputRef = useRef<HTMLInputElement>(null)
  const hiddenSpanRef = useRef<HTMLSpanElement>(null)

  // Load all references to validate mentions
  useEffect(() => {
    if (userId) {
      loadValidReferences()
    }
  }, [userId])

  const loadValidReferences = async () => {
    try {
      const references = await getUserReferences(userId)
      setValidReferences(new Set(references.map(ref => ref.tag)))
    } catch (error) {
      console.error('Failed to load references for validation:', error)
    }
  }

  // Get cursor position for positioning dropdown
  const getCursorPosition = useCallback(() => {
    if (!inputRef.current) return 0
    return inputRef.current.selectionStart || 0
  }, [])

  // Calculate dropdown position
  const calculateDropdownPosition = useCallback((atPosition: number) => {
    if (!inputRef.current || !hiddenSpanRef.current) {
      return { top: 0, left: 0 }
    }

    const input = inputRef.current
    const inputRect = input.getBoundingClientRect()
    
    // Create a temporary span to measure text width up to the @ symbol
    const textBeforeAt = value.substring(0, atPosition)
    hiddenSpanRef.current.textContent = textBeforeAt
    
    const textWidth = hiddenSpanRef.current.offsetWidth
    
    return {
      top: inputRect.bottom + window.scrollY + 4,
      left: inputRect.left + window.scrollX + textWidth + 12 // Add padding offset
    }
  }, [value])

  // Check for @ mention at current cursor position
  const checkForMention = useCallback((text: string, position: number) => {
    // Look backwards from cursor to find @
    let atIndex = -1
    for (let i = position - 1; i >= 0; i--) {
      if (text[i] === '@') {
        atIndex = i
        break
      }
      if (text[i] === ' ' || text[i] === '\n') {
        break
      }
    }

    if (atIndex === -1) {
      return null
    }

    // Check if there's a space or newline before @ (or it's at the beginning)
    if (atIndex > 0 && text[atIndex - 1] !== ' ' && text[atIndex - 1] !== '\n') {
      return null
    }

    // Get the word after @
    const afterAt = text.substring(atIndex + 1, position)
    
    // Make sure we're still in the same word (no spaces)
    if (afterAt.includes(' ') || afterAt.includes('\n')) {
      return null
    }

    return {
      start: atIndex,
      searchTerm: afterAt
    }
  }, [])

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    onChange(newValue)
    
    // Use setTimeout to get the cursor position after the input value is updated
    setTimeout(() => {
      const newCursorPosition = getCursorPosition()
      setCursorPosition(newCursorPosition)

      // Check for mention at cursor position
      const mention = checkForMention(newValue, newCursorPosition)
      
      if (mention) {
        setCurrentMentionStart(mention.start)
        setSearchTerm(mention.searchTerm)
        setDropdownPosition(calculateDropdownPosition(mention.start))
        setShowDropdown(true)
      } else {
        setShowDropdown(false)
        setCurrentMentionStart(-1)
        setSearchTerm('')
      }
    }, 0)
  }

  // Handle dropdown selection
  const handleReferenceSelect = (tag: string) => {
    if (currentMentionStart === -1) return

    const beforeMention = value.substring(0, currentMentionStart)
    const afterCursor = value.substring(cursorPosition)
    const newValue = beforeMention + `@${tag} ` + afterCursor
    
    onChange(newValue)
    setShowDropdown(false)
    setCurrentMentionStart(-1)
    setSearchTerm('')

    // Set cursor position after the mention
    setTimeout(() => {
      if (inputRef.current) {
        const newPosition = beforeMention.length + tag.length + 2
        inputRef.current.setSelectionRange(newPosition, newPosition)
        inputRef.current.focus()
      }
    }, 0)
  }

  // Handle key press events
  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    // Don't interfere with dropdown navigation
    if (showDropdown && ['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(e.key)) {
      return
    }

    setCursorPosition(getCursorPosition())
    
    if (onKeyPress) {
      onKeyPress(e)
    }
  }

  // Handle cursor movement
  const handleCursorMove = () => {
    const newPosition = getCursorPosition()
    setCursorPosition(newPosition)

    // Check if we're still in a mention
    if (showDropdown) {
      const mention = checkForMention(value, newPosition)
      if (!mention || mention.start !== currentMentionStart) {
        setShowDropdown(false)
        setCurrentMentionStart(-1)
        setSearchTerm('')
      } else {
        setSearchTerm(mention.searchTerm)
      }
    }
  }

  // Add custom styling for @ mentions
  const getStyledClassName = () => {
    let styledClassName = className || ''
    
    // Check if there are valid @ mentions in the text
    const mentionRegex = /@(\w+)/g
    let hasValidMentions = false
    let match
    
    while ((match = mentionRegex.exec(value)) !== null) {
      if (validReferences.has(match[1])) {
        hasValidMentions = true
        break
      }
    }
    
    // Add a CSS class that can be used to style @ mentions
    if (hasValidMentions) {
      styledClassName += ' has-references'
    }
    
    return styledClassName
  }

  // Count valid references in the text
  const getValidReferenceCount = () => {
    const mentionRegex = /@(\w+)/g
    let count = 0
    let match
    
    while ((match = mentionRegex.exec(value)) !== null) {
      if (validReferences.has(match[1])) {
        count++
      }
    }
    
    return count
  }

  const validReferenceCount = getValidReferenceCount()

  return (
    <div className="relative">
      {/* Hidden span for measuring text width */}
      <span
        ref={hiddenSpanRef}
        className="absolute invisible whitespace-pre text-lg"
      />

      {/* Actual input */}
      <input
        ref={inputRef}
        type={type}
        value={value}
        onChange={handleInputChange}
        onKeyDown={handleKeyPress}
        onSelect={handleCursorMove}
        onClick={handleCursorMove}
        placeholder={placeholder}
        disabled={disabled}
        className={getStyledClassName()}
        {...props}
      />

      {/* Reference indicator */}
      {validReferenceCount > 0 && (
        <div className="absolute right-2 top-1/2 transform -translate-y-1/2 flex items-center gap-1 pointer-events-none">
          <div className="w-2 h-2 bg-purple-400 rounded-full"></div>
          <span className="text-xs text-purple-400 font-medium">
            {validReferenceCount} ref{validReferenceCount !== 1 ? 's' : ''}
          </span>
        </div>
      )}

      {/* Reference dropdown */}
      <ReferenceDropdown
        isOpen={showDropdown}
        searchTerm={searchTerm}
        onSelect={handleReferenceSelect}
        onClose={() => {
          setShowDropdown(false)
          setCurrentMentionStart(-1)
          setSearchTerm('')
        }}
        userId={userId}
        position={dropdownPosition}
      />
    </div>
  )
}