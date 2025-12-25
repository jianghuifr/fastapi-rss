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
  getStats: (id) => api.get(`/feeds/${id}/stats`),
  exportOpml: async () => {
    const response = await api.get('/feeds/export/opml', {
      responseType: 'blob'
    })
    // 创建下载链接
    const url = window.URL.createObjectURL(new Blob([response.data]))
    const link = document.createElement('a')
    link.href = url
    const contentDisposition = response.headers['content-disposition']
    const filename = contentDisposition
      ? contentDisposition.split('filename=')[1]?.replace(/"/g, '') || 'rss_feeds.opml'
      : 'rss_feeds.opml'
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
  },
  importOpml: async (file) => {
    // 直接将文件传递给后端，不做任何处理
    const formData = new FormData()
    formData.append('file', file)
    // 不设置 Content-Type，让浏览器自动设置（包含 boundary）
    const response = await api.post('/feeds/import/opml', formData)
    return response.data
  }
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
