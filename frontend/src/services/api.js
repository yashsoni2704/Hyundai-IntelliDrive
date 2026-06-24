/**
 * HTTP client for all backend API calls.
 *
 * API_BASE = '/api' in dev — Vite proxy forwards to http://127.0.0.1:8000 (see vite.config.js).
 * JWT token stored in localStorage; sent as Authorization: Bearer header when logged in.
 *
 * Main functions:
 *   sendChatMessage — POST /chat (FAQ search + context)
 *   startChatSession / endChatSession — session lifecycle
 *   fetchRecentExchanges — sidebar last 5 Q&As
 *   fetchAdminChatLogs — admin paginated monitor
 */

// Dev: Vite proxy /api → backend. Production (Render): VITE_API_URL="" → same-origin /chat, /auth, etc.
const API_BASE = import.meta.env.VITE_API_URL ?? '/api'

function getToken() {
  return localStorage.getItem('hyundai_auth_token')
}

function authHeaders() {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

function parseApiError(data, status) {
  if (status === 404) {
    return 'API route not found. Restart the backend: cd backend && python -m uvicorn app:app --port 8000'
  }
  if (typeof data.detail === 'string') {
    return data.detail
  }
  if (status === 503) {
    return 'Knowledge base is initializing. Please wait a moment and try again. This usually takes 2-5 minutes on first startup.'
  }
  if (data.detail?.message) {
    return data.detail.message
  }
  if (Array.isArray(data.detail)) {
    return data.detail.map((e) => e.msg).join(', ')
  }
  if (status === 502 || status === 504) {
    return 'Backend server is not running. Run start_backend.bat, then try again.'
  }
  if (status >= 500) {
    return 'Backend server error. Make sure start_backend.bat is running on port 8000.'
  }
  return 'Request failed'
}

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders(),
        ...options.headers,
      },
    })
  } catch {
    throw new Error(
      'Cannot reach the backend server. Run start_backend.bat (or: cd backend && python -m uvicorn app:app --port 8000), then try again.'
    )
  }

  const raw = await response.text()
  let data = {}
  if (raw) {
    try {
      data = JSON.parse(raw)
    } catch {
      if (!response.ok) {
        throw new Error(
          response.status === 502 || response.status === 504
            ? 'Backend server is not running. Run start_backend.bat, then try again.'
            : `Server error (${response.status})`
        )
      }
    }
  }

  if (!response.ok) {
    const err = new Error(parseApiError(data, response.status))
    err.status = response.status
    err.data = data
    throw err
  }

  return data
}

export async function sendChatMessage(message, usedSuggestionIds = [], sessionId = null) {
  return request('/chat', {
    method: 'POST',
    body: JSON.stringify({
      message,
      used_suggestion_ids: usedSuggestionIds,
      session_id: sessionId,
    }),
  })
}

export async function fetchStats() {
  return request('/stats')
}

export async function checkBackendHealth() {
  return request('/health')
}

// --- Auth ---

export async function registerUser({ email, password, full_name }) {
  return request('/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      email: email.trim().toLowerCase(),
      password,
      full_name: full_name.trim(),
    }),
  })
}

export async function verifyRegisterOtp({ email, otp }) {
  return request('/auth/verify-register-otp', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim().toLowerCase(), otp }),
  })
}

export async function loginUser({ email, password }) {
  return request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim().toLowerCase(), password }),
  })
}

export async function loginAdmin({ username, password }) {
  return request('/auth/admin-login', {
    method: 'POST',
    body: JSON.stringify({ username: username.trim(), password }),
  })
}

export async function verifyLoginOtp({ email, otp }) {
  return request('/auth/verify-login-otp', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim().toLowerCase(), otp }),
  })
}

export async function forgotPassword({ email }) {
  return request('/auth/forgot-password', {
    method: 'POST',
    body: JSON.stringify({ email: email.trim().toLowerCase() }),
  })
}

export async function resetPassword({ email, otp, new_password }) {
  return request('/auth/reset-password', {
    method: 'POST',
    body: JSON.stringify({
      email: email.trim().toLowerCase(),
      otp,
      new_password,
    }),
  })
}

export async function fetchMe() {
  return request('/auth/me')
}

// --- Bookings ---

export async function fetchBookingDates() {
  return request('/bookings/dates')
}

export async function fetchSlotsForDate(date) {
  return request(`/bookings/slots?date=${encodeURIComponent(date)}`)
}

export async function createBooking({ date, time_slot, vehicle_model }) {
  return request('/bookings', {
    method: 'POST',
    body: JSON.stringify({ date, time_slot, vehicle_model }),
  })
}

export async function fetchMyBookings() {
  return request('/bookings/my')
}

// --- Admin ---

export async function fetchAdminBookings() {
  return request('/admin/bookings')
}

export async function createAdminBooking(payload) {
  return request('/admin/bookings', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function updateAdminBooking(id, payload) {
  return request(`/admin/bookings/${encodeURIComponent(id)}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export async function deleteAdminBooking(id) {
  return request(`/admin/bookings/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  })
}

export async function fetchAdminDates() {
  return request('/admin/dates')
}

export async function fetchAdminSlots(date) {
  return request(`/admin/slots?date=${encodeURIComponent(date)}`)
}

export async function fetchAdminChatLogs({ page = 1, perPage = 10, email = '' } = {}) {
  const params = new URLSearchParams({ page: String(page), per_page: String(perPage) })
  if (email.trim()) params.set('email', email.trim().toLowerCase())
  return request(`/admin/chat-logs?${params.toString()}`)
}

// --- Chat session ---

export async function startChatSession() {
  return request('/chat/session/start', { method: 'POST' })
}

export async function endChatSession(sessionId) {
  return request('/chat/session/end', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}

export async function fetchSessionMessages(sessionId) {
  return request(`/chat/session/${encodeURIComponent(sessionId)}/messages`)
}

export async function fetchRecentExchanges(sessionId = null) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
  return request(`/chat/recent${query}`)
}

export { getToken }
