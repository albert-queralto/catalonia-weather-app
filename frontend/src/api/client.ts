export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export async function getJSON<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(API_BASE + path)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null) url.searchParams.set(k, String(v))
    })
  }
  const resp = await fetch(url.toString())
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(`HTTP ${resp.status}: ${text}`)
  }
  return (await resp.json()) as T
}
