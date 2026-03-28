const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000'
const AUTH_STORAGE_KEY = 'authSession'
const AUTH_SYNC_STORAGE_KEY = 'authSessionSyncEvent'
const AUTH_SESSION_ERROR_CODE = 'AUTH_SESSION_EXPIRED'

async function parseJsonSafe(response) {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export function getAuthSession() {
  try {
    const raw = sessionStorage.getItem(AUTH_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function getCurrentUser() {
  return getAuthSession()?.user || null
}

export function getAccessToken() {
  return getAuthSession()?.accessToken || ''
}

export function setAuthSession(payload) {
  if (!payload) return
  sessionStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(payload))
  broadcastAuthSyncEvent('login', {
    accessToken: payload.accessToken || '',
    userId: payload.user?.id || null,
    username: payload.user?.username || ''
  })
}

export function clearAuthSession(options = {}) {
  const { broadcast = true } = options
  const currentUser = getCurrentUser()
  const currentToken = getAccessToken()
  sessionStorage.removeItem(AUTH_STORAGE_KEY)
  sessionStorage.removeItem('currentUser')
  if (broadcast && currentToken) {
    broadcastAuthSyncEvent('logout', {
      accessToken: currentToken,
      userId: currentUser?.id || null,
      username: currentUser?.username || ''
    })
  }
}

function createAuthSessionError(message = '登录已失效，请重新登录') {
  const error = new Error(message)
  error.code = AUTH_SESSION_ERROR_CODE
  return error
}

export function isAuthSessionError(error) {
  return error?.code === AUTH_SESSION_ERROR_CODE
}

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = getAccessToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers
  })
  const payload = await parseJsonSafe(response)

  if (response.status === 401) {
    clearAuthSession()
    if (window.location.pathname !== '/login') {
      window.location.replace('/login')
    }
    throw createAuthSessionError(payload?.detail || payload?.message || '登录已失效，请重新登录')
  }

  if (!response.ok || payload?.success === false) {
    throw new Error(payload?.detail || payload?.message || `请求失败: ${response.status}`)
  }
  return payload
}

export async function fetchAuthorizedMediaBlobUrl(path) {
  const headers = new Headers()
  const token = getAccessToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(toAbsoluteApiUrl(path), {
    method: 'GET',
    headers
  })

  if (response.status === 401) {
    clearAuthSession()
    if (window.location.pathname !== '/login') {
      window.location.replace('/login')
    }
    throw createAuthSessionError('登录已失效，请重新登录')
  }

  if (!response.ok) {
    throw new Error(`媒体加载失败: ${response.status}`)
  }

  const blob = await response.blob()
  return URL.createObjectURL(blob)
}

export function toAbsoluteApiUrl(path) {
  if (!path) return ''
  return path.startsWith('http') ? path : `${API_BASE_URL}${path}`
}

export function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result)
    reader.onerror = () => reject(reader.error || new Error('文件读取失败'))
    reader.readAsDataURL(file)
  })
}

export async function login(payload) {
  return apiRequest('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function fetchCurrentUser() {
  return apiRequest('/api/auth/me')
}

export async function register(payload) {
  return apiRequest('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function logout() {
  return apiRequest('/api/auth/logout', {
    method: 'POST'
  })
}

export async function getConfig() {
  return apiRequest('/api/config')
}

export async function updateConfig(payload) {
  return apiRequest('/api/config', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function listSops() {
  return apiRequest('/api/sops')
}

export async function getSopDetail(sopId) {
  return apiRequest(`/api/sops/${sopId}`)
}

export async function updateSopStepSegmentation(sopId, stepNo, payload) {
  return apiRequest(`/api/sops/${sopId}/steps/${stepNo}/manual-segmentation`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function updateSopStepDemoVideo(sopId, stepNo, payload) {
  return apiRequest(`/api/sops/${sopId}/steps/${stepNo}/demo-video`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function createSop(payload) {
  return apiRequest('/api/sops', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function removeSop(sopId) {
  return apiRequest(`/api/sops/${sopId}`, { method: 'DELETE' })
}

export async function evaluateSop(sopId, userVideoDataUrl) {
  return apiRequest(`/api/sops/${sopId}/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ userVideoDataUrl })
  })
}

export async function createEvaluationJob(sopId, payload) {
  return apiRequest(`/api/sops/${sopId}/evaluation-jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function listEvaluationJobs(status = '') {
  const query = status ? `?status=${encodeURIComponent(status)}` : ''
  return apiRequest(`/api/evaluation-jobs${query}`)
}

export async function getEvaluationJobDetail(jobId) {
  return apiRequest(`/api/evaluation-jobs/${jobId}`)
}

export async function retryEvaluationJob(jobId) {
  return apiRequest(`/api/evaluation-jobs/${jobId}/retry`, {
    method: 'POST'
  })
}

export async function listHistory() {
  return apiRequest('/api/history')
}

export async function getHistoryDetail(recordId) {
  return apiRequest(`/api/history/${recordId}`)
}

export async function createHistory(payload) {
  return apiRequest('/api/history', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function reviewHistory(recordId, payload) {
  return apiRequest(`/api/history/${recordId}/review`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

export async function getStats() {
  return apiRequest('/api/stats')
}

export async function listUsers() {
  return apiRequest('/api/users')
}

export async function updateUserStatus(userId, payload) {
  return apiRequest(`/api/users/${userId}/status`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
}

function broadcastAuthSyncEvent(type, payload = {}) {
  try {
    localStorage.setItem(
      AUTH_SYNC_STORAGE_KEY,
      JSON.stringify({
        type,
        accessToken: payload.accessToken || '',
        userId: payload.userId || null,
        username: payload.username || '',
        timestamp: Date.now(),
        nonce: Math.random().toString(36).slice(2)
      })
    )
  } catch {
    // Ignore storage write failures to avoid blocking auth flow.
  }
}

export function initializeAuthSessionSync(router) {
  if (typeof window === 'undefined') return

  window.addEventListener('storage', (event) => {
    if (event.key !== AUTH_SYNC_STORAGE_KEY || !event.newValue) return

    let syncEvent = null
    try {
      syncEvent = JSON.parse(event.newValue)
    } catch {
      return
    }

    const currentUser = getCurrentUser()
    const currentToken = getAccessToken()
    if (!currentToken || !currentUser) return

    const incomingToken = syncEvent?.accessToken || ''
    const sameUser = (
      syncEvent?.userId != null && currentUser.id != null
        ? String(syncEvent.userId) === String(currentUser.id)
        : Boolean(syncEvent?.username) && syncEvent.username === currentUser.username
    )

    if (!sameUser) return

    const isRemoteLogin = syncEvent?.type === 'login' && incomingToken && incomingToken !== currentToken
    const isRemoteLogout = syncEvent?.type === 'logout' && incomingToken === currentToken

    if (!isRemoteLogin && !isRemoteLogout) return

    clearAuthSession({ broadcast: false })
    if (router.currentRoute.value.path !== '/login') {
      router.replace('/login')
    }
  })
}
