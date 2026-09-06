import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// 子路径部署: VITE_APP_BASE=/red-chip npm run build (默认根路径, 本地开发无需配置)
const appBase = process.env.VITE_APP_BASE || ''

export default defineConfig({
  plugins: [react()],
  base: appBase || '/',
  define: {
    __APP_BASE__: JSON.stringify(appBase),
  },
  server: {
    port: 5190,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8092',
        changeOrigin: true,
      },
    },
  },
})
