import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Helper methods for all API endpoints
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),
  me: () => api.get('/auth/me'),
  deviceLogin: (deviceKey, deviceId) => api.post('/auth/device/login', { device_key: deviceKey, device_id: deviceId })
}

export const usersAPI = {
  list: (params) => api.get('/users', { params }),
  get: (id) => api.get(`/users/${id}`),
  create: (data) => api.post('/users', data),
  update: (id, data) => api.patch(`/users/${id}`, data),
  delete: (id) => api.delete(`/users/${id}`),
  activate: (id) => api.post(`/users/${id}/activate`),
  deactivate: (id) => api.post(`/users/${id}/deactivate`),
  setExpiry: (id, expiresAt) => api.patch(`/users/${id}/expiry`, { expires_at: expiresAt })
}

export const rolesAPI = {
  list: () => api.get('/roles'),
  get: (id) => api.get(`/roles/${id}`),
  create: (data) => api.post('/roles', data),
  update: (id, data) => api.patch(`/roles/${id}`, data),
  delete: (id) => api.delete(`/roles/${id}`),
  setPermissions: (id, permissions) => api.post(`/roles/${id}/permissions`, { permissions })
}

export const foldersAPI = {
  list: (params) => api.get('/folders', { params }),
  get: (id) => api.get(`/folders/${id}`),
  create: (data) => api.post('/folders', data),
  update: (id, data) => api.patch(`/folders/${id}`, data),
  delete: (id) => api.delete(`/folders/${id}`)
}

export const documentsAPI = {
  list: (params) => api.get('/documents', { params }),
  get: (id) => api.get(`/documents/${id}`),
  create: (data) => api.post('/documents', data),
  update: (id, data) => api.patch(`/documents/${id}`, data),
  delete: (id) => api.delete(`/documents/${id}`),
  restore: (id) => api.post(`/documents/${id}/restore`),
  share: (id, data) => api.post(`/documents/${id}/share`, data),
  versions: (id) => api.get(`/documents/${id}/versions`),
  createVersion: (id, data) => api.post(`/documents/${id}/versions`, data),
  compareVersions: (id, v1, v2) => api.get(`/documents/${id}/versions/${v1}/diff/${v2}`),
  comments: (id) => api.get(`/documents/${id}/comments`),
  createComment: (id, data) => api.post(`/documents/${id}/comments`, data),
  updateComment: (id, commentId, data) => api.patch(`/documents/${id}/comments/${commentId}`, data),
  deleteComment: (id, commentId) => api.delete(`/documents/${id}/comments/${commentId}`),
  download: (id) => api.get(`/documents/${id}/download`, { responseType: 'blob' }),
  rendition: (id, type) => api.get(`/documents/${id}/renditions/${type}`)
}

export const groupsAPI = {
  list: (params) => api.get('/groups', { params }),
  get: (id) => api.get(`/groups/${id}`),
  create: (data) => api.post('/groups', data),
  update: (id, data) => api.patch(`/groups/${id}`, data),
  delete: (id) => api.delete(`/groups/${id}`),
  addMembers: (id, data) => api.post(`/groups/${id}/members`, data),
  removeMember: (id, userId) => api.delete(`/groups/${id}/members/${userId}`),
  associateDocuments: (id, data) => api.post(`/groups/${id}/documents`, data),
  associateFolders: (id, data) => api.post(`/groups/${id}/folders`, data),
  associateTags: (id, data) => api.post(`/groups/${id}/tags`, data),
  reindex: (id) => api.post(`/groups/${id}/reindex`)
}

export const systemConfigAPI = {
  get: () => api.get('/system/config'),
  update: (key, value, description) => api.post('/system/config/update', { key, value, description }),
  updateBulk: (configs) => api.post('/system/config/update-bulk', { configs }),
  getCategories: () => api.get('/system/config/categories')
}

export const uploadsAPI = {
  init: (data) => api.post('/uploads/init', data),
  chunk: (id, chunk, offset) => api.put(`/uploads/${id}/chunk`, chunk, {
    headers: { 'Content-Type': 'application/octet-stream' },
    params: { offset }
  }),
  finalize: (id, data) => api.post(`/uploads/${id}/finalize`, data)
}

export const scanJobsAPI = {
  create: (data) => api.post('/scan-jobs', data),
  finalize: (jobId, data) => api.post(`/scan-jobs/${jobId}/finalize`, data),
  pending: () => api.get('/scan-jobs/pending')
}

export const searchAPI = {
  search: (data) => api.post('/search', data),
  vector: (data) => api.post('/search/vector', data),
  reindex: () => api.post('/search/index/reindex'),
  reindexDocument: (docId) => api.post(`/search/index/reindex/${docId}`)
}

export const chatAPI = {
  chat: (data) => api.post('/chat', data),
  history: (params) => api.get('/chat/history', { params }),
  session: (sessionId) => api.get(`/chat/session/${sessionId}`),
  feedback: (sessionId, data) => api.post(`/chat/session/${sessionId}/feedback`, data),
  handoff: (sessionId, data) => api.post(`/chat/session/${sessionId}/handoff`, data),
  sourceAccess: (sessionId, data) => api.post(`/chat/session/${sessionId}/source-access`, data)
}

export const workflowsAPI = {
  start: (data) => api.post('/workflows', data),
  get: (id) => api.get(`/workflows/${id}`)
}

export const tasksAPI = {
  list: (params) => api.get('/tasks', { params }),
  action: (id, data) => api.post(`/tasks/${id}/action`, data)
}

export const aiAPI = {
  ocr: (data) => api.post('/ai/ocr', data),
  embed: (data) => api.post('/ai/embed', data),
  classify: (data) => api.post('/ai/classify', data),
  qa: (data) => api.post('/ai/qa', data),
  listJobs: (params) => api.get('/ai/jobs', { params }),
  jobStatus: (id) => api.get(`/ai/jobs/${id}`)
}

export const devicesAPI = {
  list: () => api.get('/devices'),
  get: (id) => api.get(`/devices/${id}`),
  create: (data) => api.post('/devices', data),
  update: (id, data) => api.patch(`/devices/${id}`, data),
  delete: (id) => api.delete(`/devices/${id}`),
  issueKey: (id) => api.post(`/devices/${id}/issue-key`),
  ping: (id) => api.post(`/devices/${id}/ping`)
}

export const settingsAPI = {
  retention: {
    list: () => api.get('/settings/retention'),
    create: (data) => api.post('/settings/retention', data),
    update: (id, data) => api.patch(`/settings/retention/${id}`, data),
    delete: (id) => api.delete(`/settings/retention/${id}`)
  },
  providers: {
    get: () => api.get('/settings/providers'),
    update: (data) => api.post('/settings/providers', data)
  },
  chatbot: {
    list: () => api.get('/settings/chatbot'),
    update: (data) => api.post('/settings/chatbot', data)
  },
  llm: {
    get: () => api.get('/settings/llm'),
    update: (data) => api.post('/settings/llm', data)
  }
}

export const reportsAPI = {
  audit: (params) => api.get('/reports/audit', { params }),
  usage: (params) => api.get('/reports/usage', { params }),
  workflow: (params) => api.get('/reports/workflow', { params }),
  quality: (params) => api.get('/reports/quality', { params }),
  exportAudit: (params) => api.post('/audit/export', params, { responseType: 'blob' })
}

export const auditAPI = {
  list: (params) => api.get('/audit', { params }),
  export: (params) => api.post('/audit/export', params, { responseType: 'blob' })
}

export default api
