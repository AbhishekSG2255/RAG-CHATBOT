import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
  timeout: 60000,
})

export const startProcessing  = ()         => api.post('/process/')
export const getStatus        = ()         => api.get('/status/')
export const sendChat         = (query, history=[]) => api.post('/chat/', { query, history })
export const getPersona       = ()         => api.get('/persona/')
export const getTopics        = (page=1, search='') =>
  api.get('/topics/', { params: { page, page_size: 25, search } })
export const getCheckpoints   = (page=1)   => api.get('/checkpoints/', { params: { page, page_size: 25 } })
export const getStats         = ()         => api.get('/stats/')

export default api
