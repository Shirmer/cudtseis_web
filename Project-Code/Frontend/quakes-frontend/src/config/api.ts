const configuredBase = (import.meta.env.VITE_API_BASE ?? '/api').trim()

const normalizedBase = configuredBase.replace(/\/+$/, '')

export const API_BASE = normalizedBase || '/api'

export function apiUrl(path: string): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  return `${API_BASE}${normalizedPath}`
}
