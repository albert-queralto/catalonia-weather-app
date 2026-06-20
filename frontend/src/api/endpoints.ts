import { apiFetch } from "./client";
import type {
  ActivityOut,
  Me,
  TokenOut,
  EventIn,
  AlertActionCard,
  AlertTimelineSlot,
  StationExplorerOut,
  ForecastAccuracySummaryOut,
} from "./types";

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
export async function getRecommendations(
  token: string,
  lat: number,
  lon: number,
  radiusKm = 8,
  horizonHours = 4,
  limit = 20,
  planningHours = 48,
  sensitiveToAirQuality = false
) {
  const qs = new URLSearchParams({
    lat: String(lat),
    lon: String(lon),
    radius_km: String(radiusKm),
    horizon_hours: String(horizonHours),
    planning_hours: String(planningHours),
    limit: String(limit),
    sensitive_to_air_quality: String(sensitiveToAirQuality),
  });

  return apiFetch<ActivityOut[]>(
    `/recommendations?${qs.toString()}`,
    {
      method: "GET",
      token,
    }
  );
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


export async function getAlertActionCards(
  token: string,
  lat?: number,
  lon?: number,
  radiusKm = 8,
  days = 2
) {
  const qs = new URLSearchParams({
    radius_km: String(radiusKm),
    days: String(days),
  });

  if (lat != null) qs.set("lat", String(lat));
  if (lon != null) qs.set("lon", String(lon));

  return apiFetch<AlertActionCard[]>(
    `/alerts/action-cards?${qs.toString()}`,
    {
      method: "GET",
      token,
    }
  );
}

export async function getAlertTimeline(
  token: string,
  lat?: number,
  lon?: number,
  radiusKm = 8,
  days = 2
) {
  const qs = new URLSearchParams({
    radius_km: String(radiusKm),
    days: String(days),
  });

  if (lat != null) qs.set("lat", String(lat));
  if (lon != null) qs.set("lon", String(lon));

  return apiFetch<AlertTimelineSlot[]>(
    `/alerts/timeline?${qs.toString()}`,
    {
      method: "GET",
      token,
    }
  );
}

export async function updateProfile(
  token: string,
  payload: Partial<Me> & { password?: string }
) {
  return apiFetch<Me>("/users/me", {
    method: "PUT",
    token,
    body: JSON.stringify(payload),
  });
}

export async function getStations() {
  return apiFetch<any[]>("/meteocat/stations", {
    method: "GET",
  });
}

export async function getStationVariables(stationCode: string) {
  return apiFetch<any[]>(`/meteocat/station/${stationCode}/variables`, {
    method: "GET",
  });
}

export async function getStationExplorer(params: {
  stationCode: string;
  variableCode: number;
  dateFrom: string;
  dateTo: string;
  nearbyRadiusKm?: number;
  referenceStationCode?: string;
}) {
  const qs = new URLSearchParams({
    station_code: params.stationCode,
    variable_code: String(params.variableCode),
    date_from: params.dateFrom,
    date_to: params.dateTo,
    nearby_radius_km: String(params.nearbyRadiusKm ?? 50),
  });

  if (params.referenceStationCode) {
    qs.set("reference_station_code", params.referenceStationCode);
  }

  return apiFetch<StationExplorerOut>(`/stations/explorer?${qs.toString()}`, {
    method: "GET",
  });
}

export async function getForecastAccuracy(params: {
  stationCode: string;
  variableCode: number;
  metric: "temperature" | "precipitation" | "wind";
  dateFrom: string;
  dateTo: string;
  leadHours?: number;
}) {
  const qs = new URLSearchParams({
    station_code: params.stationCode,
    variable_code: String(params.variableCode),
    metric: params.metric,
    date_from: params.dateFrom,
    date_to: params.dateTo,
    lead_hours: String(params.leadHours ?? 24),
  });

  return apiFetch<ForecastAccuracySummaryOut>(
    `/stations/forecast-accuracy?${qs.toString()}`,
    {
      method: "GET",
    }
  );
}

export async function captureForecastSnapshots(limit = 25) {
  return apiFetch<{ status?: string; stations?: number; forecast_rows?: number }>(
    `/stations/forecast-snapshots/capture?limit=${limit}`,
    {
      method: "POST",
    }
  );
}

