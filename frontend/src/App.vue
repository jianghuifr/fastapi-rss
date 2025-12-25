<template>
  <div id="app" class="min-h-screen flex flex-col">
    <nav class="bg-slate-800 text-white py-4 shadow-md">
      <div class="max-w-7xl mx-auto px-8 flex justify-between items-center gap-4 flex-wrap">
        <router-link to="/reader" class="text-2xl font-semibold hover:opacity-80 transition-opacity cursor-pointer no-underline">
          RSS
        </router-link>
        <div class="flex gap-2 items-center flex-shrink-0">
          <Select
            id="feed-sort"
            name="feedSort"
            v-model="sortBy"
            class="w-[140px]"
          >
            <option value="title">按标题排序</option>
            <option value="created_at">按添加时间</option>
          </Select>
          <Select
            id="feed-selector"
            name="feedId"
            v-model="selectedFeedId"
            class="w-[200px]"
          >
            <option value="">全部源</option>
            <option v-for="feed in sortedFeeds" :key="feed.id" :value="feed.id">
              {{ feed.title || feed.url }}
            </option>
          </Select>
        </div>
      </div>
    </nav>
    <main class="flex-1 max-w-7xl w-full mx-auto px-8 py-8">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, provide, watch } from 'vue'
import { useRoute } from 'vue-router'
import { feedsApi } from './api'
import Select from '@/components/ui/select.vue'

const route = useRoute()

// 共享状态
const feeds = ref([])
const selectedFeedId = ref('')
const sortBy = ref('title')

// 从路由参数中获取feed_id
if (route.query.feed_id) {
  selectedFeedId.value = route.query.feed_id.toString()
}

// 排序后的 feeds 列表
const sortedFeeds = computed(() => {
  const feedsList = [...feeds.value]
  if (sortBy.value === 'title') {
    // 按标题排序（中文按拼音，英文按字母）
    return feedsList.sort((a, b) => {
      const titleA = (a.title || a.url || '').toLowerCase()
      const titleB = (b.title || b.url || '').toLowerCase()
      return titleA.localeCompare(titleB, 'zh-CN', { numeric: true })
    })
  } else if (sortBy.value === 'created_at') {
    // 按添加时间正序排序（最旧的在前，最新的在后）
    return feedsList.sort((a, b) => {
      const timeA = a.created_at ? new Date(a.created_at).getTime() : 0
      const timeB = b.created_at ? new Date(b.created_at).getTime() : 0
      return timeA - timeB
    })
  }
  return feedsList
})

// 加载 feeds 列表
const loadFeeds = async () => {
  try {
    const res = await feedsApi.list()
    feeds.value = res.data.feeds
  } catch (error) {
    console.error('Failed to load feeds:', error)
  }
}

// 监听路由变化
watch(() => route.query.feed_id, (newFeedId) => {
  if (newFeedId) {
    selectedFeedId.value = newFeedId.toString()
  }
})

// 提供状态给子组件
provide('selectedFeedId', selectedFeedId)
provide('sortBy', sortBy)
provide('feeds', feeds)
provide('sortedFeeds', sortedFeeds)

// 初始化加载 feeds
loadFeeds()
</script>

<style scoped>
/* 导航栏中的 Select 组件深色主题样式 */
nav :deep(select) {
  background-color: rgb(51 65 85) !important; /* slate-700 */
  color: white !important;
  border-color: rgb(71 85 105) !important; /* slate-600 */
}

nav :deep(select:hover) {
  background-color: rgb(71 85 105) !important; /* slate-600 */
}

nav :deep(select:focus) {
  outline: none;
  ring-color: rgb(100 116 139) !important; /* slate-500 */
}

/* option 标签样式（部分浏览器支持有限） */
nav :deep(select option) {
  background-color: rgb(51 65 85) !important; /* slate-700 */
  color: white !important;
}
</style>
