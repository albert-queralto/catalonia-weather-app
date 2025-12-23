export const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export type ApiError = { status: number; message: string };

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

async function parseError(res: Response): Promise<ApiError> {
  let msg = `${res.status} ${res.statusText}`;
  try {
    const j = await res.json();
    msg = j?.detail ?? j?.message ?? msg;
  } catch {
    // ignore
  }
  return { status: res.status, message: msg };
}

export async function apiFetch<T>(
  path: string,
  opts: RequestInit & { token?: string } = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const headers = new Headers(opts.headers ?? {});
  headers.set("Accept", "application/json");

  if (opts.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  if (opts.token) {
    headers.set("Authorization", `Bearer ${opts.token}`);
  }

  const res = await fetch(url, { ...opts, headers });

  if (!res.ok) {
    throw await parseError(res);
  }

  // Some endpoints may return empty bodies
  const text = await res.text();
  return (text ? JSON.parse(text) : ({} as T)) as T;
}