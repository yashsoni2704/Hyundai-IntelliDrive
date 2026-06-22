import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const BACKEND_HOST = process.env.BACKEND_HOST || '127.0.0.1'
const BACKEND_PORT = process.env.BACKEND_PORT || '8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: `http://${BACKEND_HOST}:${BACKEND_PORT}`,
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
