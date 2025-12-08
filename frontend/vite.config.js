import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from "path"

export default defineConfig({
  plugins: [react()],
  // You need this section for shadcn/ui
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: '0.0.0.0', // This is fine
    port: 3000,      // This is fine
    proxy: {
      '/api': {
        target: 'http://localhost:8000', // This is also fine
        changeOrigin: true,
      }
    }
  }
})
