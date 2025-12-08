// Use relative path so Vite proxy handles it (cookies work correctly on same origin)
const API_V1 = '/api/v1'

export const API_ENDPOINTS = {
  // Auth endpoints
  SEND_MAGIC_LINK: `${API_V1}/auth/send-magic-link`,
  AUTHENTICATE: `${API_V1}/auth/authenticate`,
  LOGOUT: `${API_V1}/auth/logout`,
  ME: `${API_V1}/auth/me`,
  DEV_LOGIN: `${API_V1}/auth/dev-login`,

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

export { API_V1 }
