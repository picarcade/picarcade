/**
 * User management utilities for PicArcade
 * Handles persistent user identification for generation history
 */

const USER_ID_KEY = 'picarcade_user_id';

/**
 * Generate a persistent user ID that survives page refreshes
 * Uses localStorage to maintain user identity across sessions
 */
export function getOrCreateUserId(): string {
  // Check if we're in a browser environment
  if (typeof window === 'undefined') {
    // SSR fallback - generate temporary ID
    return `temp_user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  try {
    // Check if we already have a stored user ID
    let storedUserId = localStorage.getItem(USER_ID_KEY);
    
    if (!storedUserId) {
      // Generate a new unique user ID
      const timestamp = Date.now();
      const randomPart = Math.random().toString(36).substr(2, 9);
      storedUserId = `user_${timestamp}_${randomPart}`;
      
      // Store it in localStorage for persistence
      localStorage.setItem(USER_ID_KEY, storedUserId);
      
      console.log('🆔 Generated new user ID:', storedUserId);
    } else {
      console.log('🔄 Using existing user ID:', storedUserId);
    }
    
    return storedUserId;
  } catch (error) {
    // Fallback if localStorage is not available
    console.warn('localStorage not available, using temporary ID');
    return `temp_user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }
}

/**
 * Clear the current user ID (useful for testing or user logout)
 */
export function clearUserId(): void {
  if (typeof window !== 'undefined') {
    try {
      localStorage.removeItem(USER_ID_KEY);
      console.log('🗑️ User ID cleared');
    } catch (error) {
      console.warn('Failed to clear user ID:', error);
    }
  }
}

/**
 * Get the current user ID without creating a new one
 */
export function getCurrentUserId(): string | null {
  if (typeof window === 'undefined') {
    return null;
  }
  
  try {
    return localStorage.getItem(USER_ID_KEY);
  } catch (error) {
    return null;
  }
}

/**
 * Check if user has an existing ID (useful for determining if they're a returning user)
 */
export function isReturningUser(): boolean {
  return getCurrentUserId() !== null;
} 