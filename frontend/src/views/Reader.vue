<template>
  <div class="reader-page">
    <div class="page-header">
      <h2>RSS阅读器</h2>
      <div class="header-actions">
        <select v-model="selectedFeedId" class="select" @change="loadItems">
          <option value="">全部源</option>
          <option v-for="feed in feeds" :key="feed.id" :value="feed.id">
            {{ feed.title || feed.url }}
          </option>
        </select>
        <button @click="loadItems" class="btn btn-primary">刷新</button>
      </div>
    </div>

    <div v-if="loading" class="loading">
      加载中...
    </div>

    <div v-else-if="items.length === 0" class="empty-state">
      <p>暂无RSS条目</p>
      <p class="empty-hint">前往管理页面添加RSS源</p>
    </div>

    <div v-else class="items-list">
      <div
        v-for="item in items"
        :key="item.id"
        class="item-card"
        @click="openItem(item)"
      >
        <div class="item-header">
          <h3 class="item-title">{{ item.title || '无标题' }}</h3>
          <div class="item-meta">
            <span class="item-feed">{{ getFeedName(item.feed_id) }}</span>
            <span class="item-time">{{ formatDate(item.published || item.created_at) }}</span>
          </div>
        </div>
        <p v-if="item.description" class="item-description" v-html="truncateDescription(item.description)"></p>
        <div class="item-footer">
          <a
            :href="item.link"
            target="_blank"
            rel="noopener noreferrer"
            @click.stop
            class="item-link"
          >
            阅读原文 →
          </a>
          <span v-if="item.author" class="item-author">作者: {{ item.author }}</span>
        </div>
      </div>
    </div>

    <div v-if="total > items.length" class="pagination">
      <button
        @click="loadMore"
        class="btn btn-primary"
        :disabled="loadingMore"
      >
        {{ loadingMore ? '加载中...' : `加载更多 (${items.length}/${total})` }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { itemsApi, feedsApi } from '../api'
import { format } from 'date-fns'

const items = ref([])
const feeds = ref([])
const loading = ref(false)
const loadingMore = ref(false)
const selectedFeedId = ref('')
const total = ref(0)
const pageSize = 50
const currentPage = ref(0)

const formatDate = (date) => {
  if (!date) return '未知'
  return format(new Date(date), 'yyyy-MM-dd HH:mm')
}

const truncateDescription = (html) => {
  if (!html) return ''
  // 简单的HTML标签移除和截断
  const text = html.replace(/<[^>]*>/g, '').trim()
  return text.length > 200 ? text.substring(0, 200) + '...' : text
}

const getFeedName = (feedId) => {
  const feed = feeds.value.find(f => f.id === feedId)
  return feed ? (feed.title || feed.url) : `源 #${feedId}`
}

const loadFeeds = async () => {
  try {
    const res = await feedsApi.list()
    feeds.value = res.data.feeds
  } catch (error) {
    console.error('Failed to load feeds:', error)
  }
}

const loadItems = async (reset = true) => {
  if (reset) {
    currentPage.value = 0
    items.value = []
  }

  loading.value = reset
  loadingMore.value = !reset

  try {
    const params = {
      limit: pageSize,
      offset: currentPage.value * pageSize
    }
    if (selectedFeedId.value) {
      params.feed_id = selectedFeedId.value
    }

    const res = await itemsApi.list(params)
    if (reset) {
      items.value = res.data.items
    } else {
      items.value.push(...res.data.items)
    }
    total.value = res.data.total
    currentPage.value++
  } catch (error) {
    console.error('Failed to load items:', error)
    alert('加载失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  loadItems(false)
}

const openItem = (item) => {
  window.open(item.link, '_blank', 'noopener,noreferrer')
}

onMounted(() => {
  loadFeeds()
  loadItems()
})
</script>

<style scoped>
.reader-page {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 1rem;
}

.page-header h2 {
  font-size: 2rem;
  color: #2c3e50;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.select {
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 0.9rem;
  background: white;
  cursor: pointer;
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

.loading {
  text-align: center;
  padding: 3rem;
  color: #7f8c8d;
  font-size: 1.1rem;
}

.empty-state {
  text-align: center;
  padding: 4rem 2rem;
  color: #95a5a6;
}

.empty-state p {
  margin: 0.5rem 0;
  font-size: 1.1rem;
}

.empty-hint {
  font-size: 0.9rem;
  color: #bdc3c7;
}

.items-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.item-card {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  cursor: pointer;
  transition: all 0.2s;
}

.item-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.15);
  transform: translateY(-2px);
}

.item-header {
  margin-bottom: 1rem;
}

.item-title {
  font-size: 1.3rem;
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
  line-height: 1.4;
}

.item-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #7f8c8d;
  flex-wrap: wrap;
}

.item-feed {
  background: #ecf0f1;
  padding: 0.25rem 0.75rem;
  border-radius: 12px;
}

.item-time {
  color: #95a5a6;
}

.item-description {
  color: #34495e;
  line-height: 1.6;
  margin: 1rem 0;
  max-height: 4.8em;
  overflow: hidden;
}

.item-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #ecf0f1;
}

.item-link {
  color: #3498db;
  text-decoration: none;
  font-weight: 500;
  transition: color 0.2s;
}

.item-link:hover {
  color: #2980b9;
}

.item-author {
  font-size: 0.85rem;
  color: #95a5a6;
}

.pagination {
  text-align: center;
  padding: 2rem 0;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: stretch;
  }

  .header-actions {
    width: 100%;
  }

  .select {
    flex: 1;
  }

  .item-card {
    padding: 1rem;
  }

  .item-title {
    font-size: 1.1rem;
  }
}
</style>
