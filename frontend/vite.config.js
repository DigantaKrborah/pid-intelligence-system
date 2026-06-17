import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Vite config — https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    port: 5173,
    // host: true  makes Vite listen on 0.0.0.0 (all network interfaces),
    // not just localhost. This lets other computers on the LAN open the app.
    host: true,

    // Dev-mode proxy: any request to /api/* is forwarded to the FastAPI backend.
    // This means the frontend never needs to know the backend's IP in dev mode —
    // both servers appear to the browser as the same origin, avoiding CORS issues.
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,   // rewrites the Host header to match the target
      },
    },
  },
})
