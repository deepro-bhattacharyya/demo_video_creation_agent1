import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Forward API calls to the FastAPI backend in development.
      '/videos': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
