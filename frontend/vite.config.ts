/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      // Proxy ALL /api requests to RiskCast V2 backend
      '/api': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      // Health check
      '/health': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      // Metrics
      '/metrics': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
      // Reconcile
      '/reconcile': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: false,
  },
})
