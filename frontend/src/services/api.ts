import axios from 'axios'
import { TriageState } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const api = {
  async uploadLab(file: File): Promise<{ session_id: string; status: string }> {
    const formData = new FormData()
    formData.append('file', file)
    
    const response = await apiClient.post('/api/upload-lab', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    
    return response.data
  },

  async interpretLab(sessionId: string): Promise<any> {
    const response = await apiClient.post(`/api/interpret/${sessionId}`)
    return response.data
  },

  async getState(sessionId: string): Promise<TriageState> {
    const response = await apiClient.get(`/api/state/${sessionId}`)
    return response.data
  },

  async approveSpecialistSearch(sessionId: string): Promise<any> {
    const response = await apiClient.post(`/api/approve-specialist-search/${sessionId}`)
    return response.data
  },

  async saveToFhir(sessionId: string): Promise<any> {
    const response = await apiClient.post(`/api/save-to-fhir/${sessionId}`)
    return response.data
  },

  async chat(sessionId: string, message: string): Promise<{ message: string }> {
    const response = await apiClient.post(`/api/chat/${sessionId}`, { message })
    return response.data
  },
}
