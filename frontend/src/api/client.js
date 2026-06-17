import axios from 'axios'

/**
 * Axios instance pre-configured for the FastAPI backend.
 * Import this instead of bare `axios` in every API call file.
 *
 *   import client from '../api/client'
 *   const { data } = await client.get('/api/units')
 *
 * How the base URL is chosen:
 *   - In development (npm run dev): VITE_API_URL is not set, so baseURL is ''.
 *     All /api/* requests stay on the same origin and Vite proxies them to
 *     localhost:8000. No IP address configuration needed.
 *   - In production (npm run build): set VITE_API_URL in frontend/.env.production
 *     to http://[SERVER_IP]:8000. The built app sends requests directly there.
 */
const API_BASE = import.meta.env.VITE_API_URL || ''

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor ────────────────────────────────────────────────────────
// Runs before every request — attaches the JWT token stored in localStorage.
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('pid_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// ── Response interceptor ───────────────────────────────────────────────────────
// Runs after every response — if the server returns 401 (expired / invalid token),
// clear stored credentials and send the user to the login page.
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('pid_token')
      localStorage.removeItem('pid_user')
      // Hard redirect — clears React state fully, safest approach
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default client
