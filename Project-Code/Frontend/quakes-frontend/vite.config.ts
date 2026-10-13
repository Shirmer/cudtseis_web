import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// 本地开发/预览时 /api 默认代理到线上 GeoCamera 后端（仅用于获取发布信息等只读接口）。
// 生产环境由 Nginx 将 /api 代理到本机 8080 的 Java 后端。
const apiProxy = {
  '/api': {
    target: process.env.VITE_API_PROXY || 'http://8.137.48.168',
    changeOrigin: true,
  },
}

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: apiProxy,
  },
  preview: {
    host: '0.0.0.0',
    port: 4173,
    proxy: apiProxy,
  },
})
