const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const API_V1 = `${API_BASE_URL}/api/v1`

export const API_ENDPOINTS = {
  // Auth endpoints
  SEND_MAGIC_LINK: `${API_V1}/auth/send-magic-link`,
  AUTHENTICATE: `${API_V1}/auth/authenticate`,
  LOGOUT: `${API_V1}/auth/logout`,
  ME: `${API_V1}/auth/me`,

  // App endpoints
  STATUS: `${API_V1}/status`,
  UPLOAD: `${API_V1}/upload`,
  CHAT: `${API_V1}/chat`,
  CHAT_STREAM: `${API_V1}/chat/stream`,

  // Analytics endpoints
  ANALYTICS_SESSION_START: `${API_V1}/analytics/session/start`,
  ANALYTICS_SESSION_END: `${API_V1}/analytics/session/end`,
  ANALYTICS_EVENT: `${API_V1}/analytics/event`,
  ANALYTICS_FEEDBACK: `${API_V1}/analytics/feedback`,
}

export { API_BASE_URL, API_V1 }
