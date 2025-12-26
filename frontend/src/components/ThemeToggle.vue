<template>
  <Button
    variant="ghost"
    size="icon"
    @click="toggleTheme"
    :title="themeTitle"
    class="relative"
  >
    <!-- 太阳图标（浅色主题） -->
    <svg
      v-if="effectiveTheme === 'light'"
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="h-5 w-5 transition-all"
    >
      <circle cx="12" cy="12" r="4"></circle>
      <path d="M12 2v2"></path>
      <path d="M12 20v2"></path>
      <path d="m4.93 4.93 1.41 1.41"></path>
      <path d="m17.66 17.66 1.41 1.41"></path>
      <path d="M2 12h2"></path>
      <path d="M20 12h2"></path>
      <path d="m6.34 17.66-1.41 1.41"></path>
      <path d="m19.07 4.93-1.41 1.41"></path>
    </svg>
    <!-- 月亮图标（深色主题） -->
    <svg
      v-else-if="effectiveTheme === 'dark' && theme !== 'system'"
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="h-5 w-5 transition-all"
    >
      <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"></path>
    </svg>
    <!-- 系统图标（明确选择系统主题） -->
    <svg
      v-else-if="theme === 'system'"
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="h-5 w-5 transition-all"
    >
      <rect width="18" height="18" x="3" y="3" rx="2" ry="2"></rect>
      <path d="M8 21h8"></path>
      <path d="M12 3v18"></path>
    </svg>
    <!-- 自动图标（默认，跟随系统但未明确选择） -->
    <svg
      v-else
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="h-5 w-5 transition-all"
    >
      <circle cx="12" cy="12" r="3"></circle>
      <path d="M12 1v6m0 6v6M5.64 5.64l4.24 4.24m4.24 4.24l4.24 4.24M1 12h6m6 0h6M5.64 18.36l4.24-4.24m4.24-4.24l4.24-4.24"></path>
    </svg>
    <span class="sr-only">切换主题</span>
  </Button>
</template>

<script setup>
import { computed } from 'vue'
import { useTheme } from '@/composables/useTheme'
import Button from '@/components/ui/button.vue'

const { theme, setTheme, getSystemTheme } = useTheme()

const effectiveTheme = computed(() => {
  // 如果 theme 为 null 或 'system'，使用系统主题
  if (theme.value === null || theme.value === 'system') {
    return getSystemTheme()
  }
  return theme.value
})

const themeTitle = computed(() => {
  if (theme.value === null || theme.value === 'system') {
    return `系统主题 (${effectiveTheme.value === 'dark' ? '深色' : '浅色'})`
  }
  return theme.value === 'dark' ? '深色主题' : '浅色主题'
})

const toggleTheme = () => {
  // 循环切换: null/system -> light -> dark -> system -> light
  const currentTheme = theme.value
  const currentEffective = effectiveTheme.value
  console.log('[ThemeToggle] 当前主题:', currentTheme, '有效主题:', currentEffective)

  if (currentTheme === null || currentTheme === 'system') {
    console.log('[ThemeToggle] 切换到: light')
    setTheme('light')
  } else if (currentTheme === 'light') {
    console.log('[ThemeToggle] 切换到: dark')
    setTheme('dark')
  } else if (currentTheme === 'dark') {
    console.log('[ThemeToggle] 切换到: system')
    setTheme('system')
  }
}
</script>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}
</style>
