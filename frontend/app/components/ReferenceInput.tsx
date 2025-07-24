'use client'

import React, { useState, useRef, useCallback } from 'react'
import ReferenceDropdown from './ReferenceDropdown'

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
  
  const inputRef = useRef<HTMLInputElement>(null)

  // Get cursor position for positioning dropdown
  const getCursorPosition = useCallback(() => {
    if (!inputRef.current) return 0
    return inputRef.current.selectionStart || 0
  }, [])

  // Calculate dropdown position (relative to the container since using absolute positioning)
  const calculateDropdownPosition = useCallback(() => {
    if (!inputRef.current) {
      return { top: 0, left: 0 }
    }

    const input = inputRef.current
    
    // Since dropdown is now absolutely positioned relative to the container,
    // we just need to position it below the input height + padding
    return {
      top: input.offsetHeight + 4, // Position below input with 4px gap
      left: 0, // Align with left edge of container
    }
  }, [])

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
        setDropdownPosition(calculateDropdownPosition())
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

  // Return the base className
  const getStyledClassName = () => {
    return className || ''
  }





  return (
    <div className="relative flex-1">
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
        className={`w-full ${getStyledClassName()}`}
        {...props}
      />

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