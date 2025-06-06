import axios from 'axios'
import type { GenerationRequest, GenerationResponse, HistoryItem, UploadResponse } from '../types'

const API_BASE_URL = process.env.NODE_ENV === 'production' 
  ? 'https://your-api-domain.com' 
  : 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for generation requests
})

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

    const response = await api.post('/api/v1/uploads/image', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return response.data
  } catch (error) {
    if (axios.isAxiosError(error)) {
      throw new Error(error.response?.data?.detail || error.message)
    }
    throw error
  }
} 