import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

function parsePort(value: string | undefined, fallback: number): number {
  const port = Number(value)
  return Number.isFinite(port) ? port : fallback
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const proxyTarget = env.VITE_PROXY_TARGET || 'http://127.0.0.1:8001'
  const host = env.FRONTEND_HOST || '127.0.0.1'
  const port = parsePort(env.FRONTEND_PORT, 5173)

  return {
    plugins: [vue()],
    server: {
      host,
      port,
      strictPort: true,
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
        '/rag-api': {
          target: 'http://127.0.0.1:8010',
          changeOrigin: true,
        },
      },
    },
  }
})
