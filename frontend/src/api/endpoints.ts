import { apiFetch } from "./client";
import type { ActivityOut, Me, TokenOut, EventIn } from "./types";

/** Auth */
export async function register(email: string, password: string) {
  return apiFetch<Me>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password })
  });
}

export async function login(email: string, password: string) {
  // /auth/token expects application/x-www-form-urlencoded (OAuth2PasswordRequestForm)
  const body = new URLSearchParams();
  body.set("username", email);
  body.set("password", password);

  return apiFetch<TokenOut>("/auth/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: body.toString()
  });
}

export async function me(token: string) {
  return apiFetch<Me>("/auth/me", { method: "GET", token });
}

/** Recs */
export async function getRecommendations(token: string, lat: number, lon: number, radiusKm = 8, horizonHours = 4, limit = 20) {
  const qs = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_km: String(radiusKm),
    horizon_hours: String(horizonHours),
    limit: String(limit)
  });
  return apiFetch<ActivityOut[]>(`/recommendations?${qs.toString()}`, { method: "GET", token });
}

/** Events */
export async function postEvent(token: string, ev: EventIn) {
  return apiFetch<{ ok: boolean }>("/events", {
    method: "POST",
    token,
    body: JSON.stringify(ev)
  });
}

/** Health + admin ops */
export async function health() {
  return apiFetch<{ ok: boolean; model_loaded: boolean }>("/health", { method: "GET" });
}

export async function reloadModel(token: string) {
  return apiFetch<{ ok: boolean; model_loaded: boolean }>("/model/reload", { method: "POST", token });
}
