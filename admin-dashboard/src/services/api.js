import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8002/api'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor to add auth token
api.interceptors.request.use(
  config => {
    const token = localStorage.getItem('authToken')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// Response interceptor to handle errors
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('authToken')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authService = {
  login: (credentials) => api.post('/auth/login', credentials),
  logout: () => api.post('/auth/logout')
}

export const followersService = {
  getAll: () => api.get('/followers'),
  getById: (id) => api.get(`/followers/${id}`),
  create: (data) => api.post('/followers', data),
  update: (id, data) => api.put(`/followers/${id}`, data),
  delete: (id) => api.delete(`/followers/${id}`),
  getPnL: (id) => api.get(`/pnl/follower/${id}`)
}

export const logsService = {
  getAll: (params) => api.get('/logs', { params }),
  getByFollower: (followerId) => api.get(`/logs/follower/${followerId}`)
}

export const settingsService = {
  get: () => api.get('/settings'),
  update: (data) => api.put('/settings', data)
}

export default api