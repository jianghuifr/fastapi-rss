<template>
  <div class="admin-page">
    <div class="page-header">
      <h2>管理面板</h2>
      <button @click="triggerUpdateAll" class="btn btn-primary" :disabled="updating">
        {{ updating ? '更新中...' : '更新所有RSS源' }}
      </button>
    </div>

    <div class="admin-grid">
      <!-- RSS源列表 -->
      <div class="panel">
        <h3>RSS源列表</h3>
        <div class="feed-form">
          <input
            v-model="newFeedUrl"
            type="url"
            placeholder="输入RSS源URL，例如: https://www.ruanyifeng.com/blog/atom.xml"
            class="input"
            @keyup.enter="addFeed"
          />
          <button @click="addFeed" class="btn btn-primary" :disabled="adding">
            {{ adding ? '添加中...' : '添加' }}
          </button>
        </div>
        <div class="feeds-list">
          <div
            v-for="feed in feeds"
            :key="feed.id"
            class="feed-card"
            :class="{ 'feed-active': selectedFeedId === feed.id }"
            @click="selectFeed(feed.id)"
          >
            <div class="feed-header">
              <h4>{{ feed.title || '未命名源' }}</h4>
              <div class="feed-actions">
                <button @click.stop="updateFeed(feed.id)" class="btn-icon" title="更新">
                  🔄
                </button>
                <button @click.stop="deleteFeed(feed.id)" class="btn-icon btn-danger" title="删除">
                  🗑️
                </button>
              </div>
            </div>
            <p class="feed-url">{{ feed.url }}</p>
            <div class="feed-meta">
              <span>最后更新: {{ formatDate(feed.last_updated) }}</span>
              <span v-if="feedStats[feed.id]">
                条目数: {{ feedStats[feed.id].total_items }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 任务工作流 -->
      <div class="panel">
        <h3>任务工作流</h3>
        <div class="workflow-container">
          <VueFlow
            v-model="nodes"
            v-model:edges="edges"
            :fit-view-on-init="true"
            class="workflow-flow"
          >
            <!-- Background 组件暂时移除，避免构建错误 -->
            <!-- <Background /> -->
            <Controls />
          </VueFlow>
        </div>
        <div class="task-history">
          <h4>任务历史</h4>
          <div v-if="taskHistory.length === 0" class="empty-state">
            暂无任务历史
          </div>
          <div v-for="task in taskHistory" :key="task.id" class="task-item">
            <div class="task-status" :class="`status-${task.status}`">
              {{ getStatusText(task.status) }}
            </div>
            <div class="task-info">
              <div class="task-name">{{ task.name }}</div>
              <div class="task-time">{{ formatDate(task.created_at) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { VueFlow } from '@vue-flow/core'
// Background 组件可能不需要，先注释掉
// import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { feedsApi, tasksApi } from '../api'
import { format } from 'date-fns'

const feeds = ref([])
const newFeedUrl = ref('')
const adding = ref(false)
const updating = ref(false)
const selectedFeedId = ref(null)
const feedStats = ref({})
const taskHistory = ref([])

// Vue Flow 节点和边
const nodes = ref([
  {
    id: '1',
    type: 'input',
    label: '定时触发器',
    position: { x: 100, y: 100 },
    data: { label: '每5分钟触发' }
  },
  {
    id: '2',
    label: '更新所有RSS源',
    position: { x: 300, y: 100 },
    data: { label: 'update_all_feeds_task' }
  },
  {
    id: '3',
    label: '更新单个RSS源',
    position: { x: 500, y: 100 },
    data: { label: 'update_single_feed_task' }
  },
  {
    id: '4',
    type: 'output',
    label: '完成',
    position: { x: 700, y: 100 },
    data: { label: '任务完成' }
  }
])

const edges = ref([
  { id: 'e1-2', source: '1', target: '2' },
  { id: 'e2-3', source: '2', target: '3' },
  { id: 'e3-4', source: '3', target: '4' }
])

let refreshInterval = null

const formatDate = (date) => {
  if (!date) return '未知'
  return format(new Date(date), 'yyyy-MM-dd HH:mm:ss')
}

const getStatusText = (status) => {
  const statusMap = {
    'PENDING': '等待中',
    'STARTED': '运行中',
    'SUCCESS': '成功',
    'FAILURE': '失败',
    'REVOKED': '已取消'
  }
  return statusMap[status] || status
}

const loadFeeds = async () => {
  try {
    const res = await feedsApi.list()
    feeds.value = res.data.feeds
    // 加载每个feed的统计信息
    for (const feed of feeds.value) {
      try {
        const statsRes = await feedsApi.getStats(feed.id)
        feedStats.value[feed.id] = statsRes.data
      } catch (e) {
        console.error(`Failed to load stats for feed ${feed.id}:`, e)
      }
    }
  } catch (error) {
    console.error('Failed to load feeds:', error)
  }
}

const addFeed = async () => {
  if (!newFeedUrl.value.trim()) return
  adding.value = true
  try {
    await feedsApi.create(newFeedUrl.value)
    newFeedUrl.value = ''
    await loadFeeds()
  } catch (error) {
    alert('添加失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    adding.value = false
  }
}

const deleteFeed = async (id) => {
  if (!confirm('确定要删除这个RSS源吗？')) return
  try {
    await feedsApi.delete(id)
    await loadFeeds()
    if (selectedFeedId.value === id) {
      selectedFeedId.value = null
    }
  } catch (error) {
    alert('删除失败: ' + (error.response?.data?.detail || error.message))
  }
}

const updateFeed = async (id) => {
  try {
    await feedsApi.updateAsync(id)
    alert('已触发更新任务')
    await loadFeeds()
  } catch (error) {
    alert('更新失败: ' + (error.response?.data?.detail || error.message))
  }
}

const selectFeed = (id) => {
  selectedFeedId.value = id
}

const triggerUpdateAll = async () => {
  updating.value = true
  try {
    const res = await tasksApi.triggerUpdateAll()
    alert('已触发更新所有RSS源任务')
    // 可以在这里添加任务到历史记录
    taskHistory.value.unshift({
      id: res.data.task_id,
      name: '更新所有RSS源',
      status: 'PENDING',
      created_at: new Date().toISOString()
    })
  } catch (error) {
    alert('触发失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    updating.value = false
  }
}

const refreshTaskStatus = async () => {
  // 刷新任务状态
  for (const task of taskHistory.value) {
    if (task.status === 'PENDING' || task.status === 'STARTED') {
      try {
        const res = await tasksApi.get(task.id)
        task.status = res.data.status
      } catch (e) {
        console.error('Failed to refresh task status:', e)
      }
    }
  }
}

onMounted(() => {
  loadFeeds()
  // 每5秒刷新一次任务状态
  refreshInterval = setInterval(refreshTaskStatus, 5000)
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
</script>

<style scoped>
.admin-page {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h2 {
  font-size: 2rem;
  color: #2c3e50;
}

.admin-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.panel {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.panel h3 {
  margin-bottom: 1rem;
  color: #2c3e50;
}

.feed-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.input {
  flex: 1;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.2s;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.feeds-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  max-height: 600px;
  overflow-y: auto;
}

.feed-card {
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.2s;
}

.feed-card:hover {
  border-color: #3498db;
  box-shadow: 0 2px 8px rgba(52, 152, 219, 0.2);
}

.feed-card.feed-active {
  border-color: #3498db;
  background: #ebf5fb;
}

.feed-header {
  display: flex;
  justify-content: space-between;
  align-items: start;
  margin-bottom: 0.5rem;
}

.feed-header h4 {
  flex: 1;
  margin: 0;
  color: #2c3e50;
}

.feed-actions {
  display: flex;
  gap: 0.5rem;
}

.btn-icon {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: background 0.2s;
}

.btn-icon:hover {
  background: rgba(0,0,0,0.1);
}

.btn-danger:hover {
  background: rgba(231, 76, 60, 0.2);
}

.feed-url {
  color: #7f8c8d;
  font-size: 0.85rem;
  margin: 0.5rem 0;
  word-break: break-all;
}

.feed-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #95a5a6;
}

.workflow-container {
  height: 400px;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  margin-bottom: 1.5rem;
}

.workflow-flow {
  width: 100%;
  height: 100%;
}

.task-history {
  max-height: 300px;
  overflow-y: auto;
}

.task-history h4 {
  margin-bottom: 1rem;
  color: #2c3e50;
}

.empty-state {
  text-align: center;
  color: #95a5a6;
  padding: 2rem;
}

.task-item {
  display: flex;
  gap: 1rem;
  padding: 0.75rem;
  border-bottom: 1px solid #e0e0e0;
  align-items: center;
}

.task-status {
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  white-space: nowrap;
}

.status-PENDING {
  background: #f39c12;
  color: white;
}

.status-STARTED {
  background: #3498db;
  color: white;
}

.status-SUCCESS {
  background: #27ae60;
  color: white;
}

.status-FAILURE {
  background: #e74c3c;
  color: white;
}

.status-REVOKED {
  background: #95a5a6;
  color: white;
}

.task-info {
  flex: 1;
}

.task-name {
  font-weight: 500;
  color: #2c3e50;
}

.task-time {
  font-size: 0.85rem;
  color: #95a5a6;
  margin-top: 0.25rem;
}

@media (max-width: 1024px) {
  .admin-grid {
    grid-template-columns: 1fr;
  }
}
</style>
