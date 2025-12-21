import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 30000
})

// RSS源相关
export const feedsApi = {
  list: () => api.get('/feeds'),
  get: (id) => api.get(`/feeds/${id}`),
  create: (url) => api.post('/feeds', { url }),
  delete: (id) => api.delete(`/feeds/${id}`),
  update: (id) => api.post(`/feeds/${id}/update`),
  updateAsync: (id) => api.post(`/feeds/${id}/update-async`),
  getItems: (id, params) => api.get(`/feeds/${id}/items`, { params }),
  getStats: (id) => api.get(`/feeds/${id}/stats`)
}

// RSS条目相关
export const itemsApi = {
  list: (params) => api.get('/items', { params }),
  get: (id) => api.get(`/items/${id}`)
}

// 任务相关
export const tasksApi = {
  get: (taskId) => api.get(`/tasks/${taskId}`),
  list: (params) => api.get('/tasks', { params }),
  triggerUpdateAll: () => api.post('/tasks/update-all')
}

export default api
