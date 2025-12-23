export type ForecastResponse = {
  provider: 'open_meteo' | 'meteocat'
  lat: number
  lon: number
  timezone: string
  updated_at: string
  current?: {
    time: string
    temperature_c?: number
    wind_speed_m_s?: number
    wind_gust_m_s?: number
    precipitation_mm?: number
    weather_code?: number
  } | null
  hourly: Array<{
    time: string
    temperature_c?: number
    precipitation_mm?: number
    wind_speed_m_s?: number
    wind_gust_m_s?: number
    weather_code?: number
  }>
  daily: Array<{
    date: string
    temperature_max_c?: number
    temperature_min_c?: number
    precipitation_sum_mm?: number
    wind_gust_max_m_s?: number
  }>
}

export type ComarcaOut = {
  code: string
  name: string
}

export type ComarcaForecastResponse = {
  provider: 'meteocat'
  comarca_code: string
  comarca_name: string
  timezone: string
  updated_at: string
  daily: Array<{
    date: string
    temperature_max_c?: number
    temperature_min_c?: number
    precipitation_probability_pct?: number
    precipitation_sum_mm?: number
    wind_gust_max_m_s?: number
    summary?: string
  }>
}

export type RadarTimestamps = {
  updated_at: string
  provider: string
  timestamps: Array<{ time: number } | number>
}


export interface AvisAfectacio {
  dia: string;
  llindar: string | null;
  auxiliar: boolean;
  perill: number;
  idComarca: number;
  nivell: number;
}

export interface Periode {
  nom: string;
  afectacions: AvisAfectacio[] | null;
}

export interface Evolucio {
  dia: string;
  comentari: string | null;
  representatiu: number;
  llindar1: string | null;
  llindar2: string | null;
  distribucioGeografica: string | null;
  periodes: Periode[];
}

export interface Avis {
  tipus: string;
  dataEmisio: string;
  dataInici: string;
  dataFi: string;
  evolucions: Evolucio[];
}

export interface Meteor {
  nom: string;
}

export interface Estat {
  nom: string;
  data: string | null;
}

export interface EpisodiObert {
  estat: Estat;
  meteor: Meteor;
  avisos: Avis[];
}

export type Role = "user" | "admin";

export type Me = {
  id: string;
  email: string;
  role: Role;
};

export type TokenOut = {
  access_token: string;
  token_type: "bearer";
};

export type ActivityOut = {
  id: string;
  name: string;
  category: string;
  tags: string[];
  indoor: boolean;
  covered: boolean;
  price_level: number;
  difficulty: number;
  duration_minutes: number;
  distance_km: number;
  score: number;
  reason: string;
  request_id?: string | null;
};

export type EventIn = {
  user_id: string;
  activity_id: string;
  event_type: "view" | "click" | "save" | "complete" | "dismiss";
  ts?: string;

  request_id?: string | null;
  position?: number | null;

  user_lat?: number | null;
  user_lon?: number | null;

  weather_temp_c?: number | null;
  weather_precip_prob?: number | null;
  weather_wind_kmh?: number | null;
  weather_is_day?: number | null;
};
