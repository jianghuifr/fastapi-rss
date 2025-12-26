import { ref, watch, onMounted, onUnmounted } from 'vue'

type Theme = 'light' | 'dark' | 'system'

const THEME_STORAGE_KEY = 'rss-reader-theme'

// 立即应用主题（在页面加载时，避免闪烁）
export function initTheme() {
  if (typeof window === 'undefined') return

  const saved = localStorage.getItem(THEME_STORAGE_KEY)
  const theme: Theme | null = saved ? (saved as Theme) : null

  const getSystemTheme = (): 'light' | 'dark' => {
    if (typeof window === 'undefined') return 'light'
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  const root = document.documentElement
  const effectiveTheme = (theme === null || theme === 'system') ? getSystemTheme() : theme

  // 应用主题
  if (effectiveTheme === 'dark') {
    root.classList.add('dark')
  } else {
    root.classList.remove('dark')
  }

  // 开发环境调试信息
  if (import.meta.env.DEV) {
    console.log('[Theme] 初始化主题:', {
      saved: theme,
      system: getSystemTheme(),
      effective: effectiveTheme,
      hasDarkClass: root.classList.contains('dark')
    })
  }
}

export function useTheme() {
  // 如果没有保存的主题，返回 null，表示使用系统默认
  const getInitialTheme = (): Theme | null => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(THEME_STORAGE_KEY)
      return saved ? (saved as Theme) : null
    }
    return null
  }

  const theme = ref<Theme | null>(getInitialTheme())

  const getSystemTheme = (): 'light' | 'dark' => {
    if (typeof window !== 'undefined') {
      return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
    }
    return 'light'
  }

  const applyTheme = (newTheme: Theme | null) => {
    if (typeof window === 'undefined') return

    const root = document.documentElement
    // 如果主题为 null 或 'system'，使用系统主题
    const effectiveTheme = (newTheme === null || newTheme === 'system') ? getSystemTheme() : newTheme

    if (effectiveTheme === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }

    // 开发环境调试信息
    if (import.meta.env.DEV) {
      console.log('[Theme] 应用主题:', {
        theme: newTheme,
        effective: effectiveTheme,
        hasDarkClass: root.classList.contains('dark')
      })
    }
  }

  const setTheme = (newTheme: Theme) => {
    theme.value = newTheme
    if (typeof window !== 'undefined') {
      // 保存用户的选择
      localStorage.setItem(THEME_STORAGE_KEY, newTheme)
    }
    applyTheme(newTheme)
  }

  let mediaQuery: MediaQueryList | null = null
  let handleChange: ((e: MediaQueryListEvent) => void) | null = null

  // 设置系统主题监听器
  const setupSystemThemeListener = () => {
    if (typeof window === 'undefined') return

    // 移除旧的监听器
    if (mediaQuery && handleChange) {
      mediaQuery.removeEventListener('change', handleChange)
    }

    // 如果使用系统主题（null 或 'system'），添加新的监听器
    if (theme.value === null || theme.value === 'system') {
      mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
      handleChange = () => {
        if (theme.value === null || theme.value === 'system') {
          applyTheme(theme.value)
        }
      }
      mediaQuery.addEventListener('change', handleChange)
    }
  }

  // 监听系统主题变化
  onMounted(() => {
    // 初始化应用主题
    applyTheme(theme.value)
    setupSystemThemeListener()
  })

  // 清理监听器
  onUnmounted(() => {
    if (mediaQuery && handleChange) {
      mediaQuery.removeEventListener('change', handleChange)
    }
  })

  // 监听主题变化
  watch(theme, (newTheme) => {
    applyTheme(newTheme)
    setupSystemThemeListener()
  }, { immediate: true })

  return {
    theme,
    setTheme,
    getSystemTheme,
  }
}
