import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import { initTheme } from './composables/useTheme'

// 在应用挂载前立即初始化主题，避免闪烁
initTheme()

const app = createApp(App)
app.use(router)
app.mount('#app')
