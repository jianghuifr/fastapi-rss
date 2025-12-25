import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true, // 在 Docker 中使用轮询模式监听文件变化
      interval: 1000, // 轮询间隔（毫秒）
    },
    hmr: {
      host: 'localhost', // HMR 客户端连接的主机
      port: 5173, // HMR 端口
      clientPort: 5173, // 客户端连接的端口
    },
    proxy: {
      '/api': {
        target: process.env.VITE_API_BASE_URL || process.env.API_BASE_URL || 'http://app:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api')
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    commonjsOptions: {
      include: [/node_modules/],
      transformMixedEsModules: true
    }
  }
})
