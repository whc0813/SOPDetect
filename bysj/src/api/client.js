const API_BASE_URL = process.env.VUE_APP_API_BASE_URL || 'http://localhost:8000'

async function parseJsonSafe(response) {
  try {
    return await response.json()
  } catch {
    return null
  }
}

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, options)
  const payload = await parseJsonSafe(response)
  if (!response.ok || payload?.success === false) {
    throw new Error(payload?.detail || payload?.message || `请求失败: ${response.status}`)
  }
  return payload
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
