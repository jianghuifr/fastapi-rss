import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'
// @vue-flow/background 样式可能不需要单独导入，或者包结构不同
// import '@vue-flow/background/dist/style.css'

const app = createApp(App)
app.use(router)
app.mount('#app')
