<template>
  <div id="app" class="min-h-screen flex flex-col bg-background text-foreground">
    <nav class="bg-slate-800 dark:bg-[rgb(21,21,23)] text-white py-4 shadow-md border-b border-slate-700 dark:border-[hsl(240,5%,18%)]">
      <div class="max-w-7xl mx-auto px-4 sm:px-8 flex justify-between items-center gap-4 flex-wrap">
        <router-link to="/" class="text-2xl font-semibold hover:opacity-80 transition-opacity cursor-pointer no-underline">
          RSS
        </router-link>
        <div class="flex gap-2 items-center flex-shrink-0 w-full sm:w-auto">
          <Select
            id="feed-sort"
            name="feedSort"
            v-model="sortBy"
            class="w-full sm:w-[140px] min-w-0"
          >
            <option value="title">按标题排序</option>
            <option value="created_at">按添加时间</option>
          </Select>
          <Select
            id="feed-selector"
            name="feedId"
            v-model="selectedFeedId"
            class="w-full sm:w-[200px] min-w-0"
          >
            <option value="">全部源</option>
            <option v-for="feed in sortedFeeds" :key="feed.id" :value="feed.id">
              {{ feed.title || feed.url }}
            </option>
          </Select>
          <ThemeToggle />
        </div>
      </div>
    </nav>
    <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-8 py-8">
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
import ThemeToggle from '@/components/ThemeToggle.vue'
import { useTheme } from '@/composables/useTheme'

// 初始化主题
useTheme()

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
/* 导航栏中的 Select 组件样式 */
nav :deep(select) {
  background-color: rgb(51 65 85) !important; /* slate-700 */
  color: white !important;
  border-color: rgb(71 85 105) !important; /* slate-600 */
  max-width: 100%;
  box-sizing: border-box;
}

nav :deep(select:hover) {
  background-color: rgb(71 85 105) !important; /* slate-600 */
}

nav :deep(select:focus) {
  outline: none;
  box-shadow: 0 0 0 2px rgb(100 116 139) !important; /* slate-500 */
}

/* option 标签样式（部分浏览器支持有限） */
nav :deep(select option) {
  background-color: rgb(51 65 85) !important; /* slate-700 */
  color: white !important;
}

/* 深色主题下的导航栏样式 - OneDark Pro 风格 */
.dark nav :deep(select) {
  background-color: hsl(240, 5%, 15%) !important; /* 与 secondary 一致 */
  color: hsl(220, 13%, 71%) !important; /* 与 foreground 一致 */
  border-color: hsl(240, 5%, 18%) !important; /* 与 border 一致 */
}

.dark nav :deep(select:hover) {
  background-color: hsl(240, 5%, 18%) !important;
}

.dark nav :deep(select:focus) {
  box-shadow: 0 0 0 2px hsl(207, 82%, 66%) !important; /* primary 颜色 */
}

.dark nav :deep(select option) {
  background-color: hsl(240, 5%, 15%) !important;
  color: hsl(220, 13%, 71%) !important;
}
</style>
