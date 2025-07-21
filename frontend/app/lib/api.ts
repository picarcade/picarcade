import axios from 'axios'
import type { GenerationRequest, GenerationResponse, HistoryItem, UploadResponse, Reference } from '../types'
import { apiHelpers } from './supabase'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 
  (process.env.NODE_ENV === 'production' 
    ? 'https://picarcade.onrender.com' 
    : 'http://localhost:8000')

// Create axios instance with interceptors for authentication
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for generation requests
})

// Add request interceptor to include auth headers
api.interceptors.request.use(async (config) => {
  try {
    // Skip auth headers for upload endpoints to avoid interfering with multipart form data
    if (config.url?.includes('/uploads/')) {
      console.log('[Auth] Skipping auth headers for upload endpoint')
      return config
    }
    
    console.log('[Auth Debug] Getting auth headers for request:', config.url)
    const authHeaders = await apiHelpers.getAuthHeader()
    console.log('[Auth Debug] Auth headers received:', {
      hasAuthorization: !!authHeaders.Authorization,
      authType: authHeaders.Authorization ? authHeaders.Authorization.substring(0, 20) + '...' : 'none',
      fullHeaders: Object.keys(authHeaders)
    })
    
    Object.assign(config.headers, authHeaders)
    console.log('[Auth Debug] Final request headers:', Object.keys(config.headers || {}))
  } catch (error) {
    console.warn('Failed to get auth headers:', error)
  }
  return config
})

// Add response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Handle unauthorized - could redirect to login or refresh token
      console.warn('Unauthorized request - user may need to sign in')
    }
    return Promise.reject(error)
  }
)

export const generateContent = async (request: GenerationRequest): Promise<GenerationResponse> => {
  try {
    const response = await api.post('/api/v1/generation/generate', request)
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

export const getUserHistory = async (userId: string, limit: number = 20): Promise<HistoryItem[]> => {
  try {
    const response = await api.get(`/api/v1/generation/history/${userId}?limit=${limit}`)
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

export const uploadImage = async (
  file: File, 
  userId?: string, 
  resizeMax: number = 2048
): Promise<UploadResponse> => {
  try {
    const formData = new FormData()
    formData.append('file', file)
    if (userId) {
      formData.append('user_id', userId)
    }
    formData.append('resize_max', resizeMax.toString())

    console.log('[Upload] Uploading file:', file.name, 'Size:', file.size, 'Type:', file.type)
    console.log('[Upload] FormData entries:', Array.from(formData.entries()).map(([key, value]) => 
      key === 'file' ? [key, `File: ${(value as File).name}`] : [key, value]
    ))
    console.log('[Upload] DEBUG: FormData constructed at', new Date().toISOString())

    const response = await api.post('/api/v1/uploads/image', formData, {
      headers: {
        // Don't set Content-Type - let axios set it automatically with boundary
      },
    })
    return response.data
  } catch (error) {
    console.error('[Upload] Error details:', error)
    if (axios.isAxiosError(error)) {
      console.error('[Upload] Response data:', error.response?.data)
      console.error('[Upload] Response status:', error.response?.status)
      console.error('[Upload] Full response:', error.response)
      
      // Log validation errors in detail
      if (error.response?.data?.detail && Array.isArray(error.response.data.detail)) {
        console.error('[Upload] Validation errors:')
        error.response.data.detail.forEach((err: any, i: number) => {
          console.error(`[Upload]   ${i + 1}. ${err.type}: ${err.msg} at ${err.loc?.join('.')}`)
        })
      }
      
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

// Authentication API functions
export const authAPI = {
  async login(email: string, password: string) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/auth/login`, {
        email,
        password
      })
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || error.message)
      }
      throw error
    }
  },

  async register(email: string, password: string, metadata?: any) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/auth/register`, {
        email,
        password,
        metadata
      })
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || error.message)
      }
      throw error
    }
  },

  async refreshToken(refreshToken: string) {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/v1/auth/refresh`, {
        refresh_token: refreshToken
      })
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || error.message)
      }
      throw error
    }
  },

  async logout() {
    try {
      const response = await api.post('/api/v1/auth/logout')
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || error.message)
      }
      throw error
    }
  },

  async getCurrentUser() {
    try {
      const response = await api.get('/api/v1/auth/me')
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || error.message)
      }
      throw error
    }
  },

  async validateToken() {
    try {
      const response = await api.get('/api/v1/auth/validate')
      return response.data
    } catch (error) {
      if (axios.isAxiosError(error)) {
        throw new Error(error.response?.data?.detail || error.message)
      }
      throw error
    }
  }
}

// References API functions
export const createReference = async (
  userId: string,
  tag: string,
  imageUrl: string,
  displayName?: string,
  description?: string,
  category: string = 'general'
): Promise<Reference> => {
  try {
    const response = await api.post(`/api/v1/references/?user_id=${userId}`, {
      tag,
      image_url: imageUrl,
      display_name: displayName,
      description,
      category
    })
    return response.data.reference
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

export const getUserReferences = async (userId: string, category?: string): Promise<Reference[]> => {
  try {
    const params = new URLSearchParams({ user_id: userId })
    if (category && category !== 'all') {
      params.append('category', category)
    }
    
    const response = await api.get(`/api/v1/references/?${params.toString()}`)
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

export const deleteReference = async (userId: string, tag: string): Promise<void> => {
  try {
    await api.delete(`/api/v1/references/${tag}?user_id=${userId}`)
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

export const updateReference = async (
  userId: string,
  oldTag: string,
  newTag?: string,
  displayName?: string,
  description?: string,
  category?: string
): Promise<Reference> => {
  try {
    const response = await api.put(`/api/v1/references/${oldTag}?user_id=${userId}`, {
      new_tag: newTag,
      display_name: displayName,
      description,
      category
    })
    return response.data.reference
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

export const checkReferencesInPrompt = async (prompt: string): Promise<{
  has_references: boolean;
  mentions: string[];
  count: number;
}> => {
  try {
    const response = await api.get(`/api/v1/references/check/${encodeURIComponent(prompt)}`)
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}

export const setWorkingImage = async (sessionId: string, imageUrl: string, userId: string): Promise<any> => {
  try {
    const response = await api.post('/api/v1/generation/session/set-working-image', {
      session_id: sessionId,
      image_url: imageUrl,
      user_id: userId
    })
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
}