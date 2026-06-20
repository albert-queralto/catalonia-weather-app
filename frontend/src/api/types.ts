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
  is_active: boolean;
  is_verified: boolean;

  notification_preferences: boolean;
  favorite_comarques: string[];

  alert_subscribe_current_location: boolean;
  alert_current_comarca?: string | null;
  alert_meteor_types: string[];
  alert_min_severity: number;
};

export type TokenOut = {
  access_token: string;
  token_type: "bearer";
};

export interface GeoJSONPoint {
  type: "Point";
  coordinates: [number, number]; // [lon, lat]
}

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
  recommendation_label?: string | null;
  recommendation_group?: string | null;

  best_start?: string | null;
  best_end?: string | null;

  base_score?: number | null;

  alert_severity?: number;
  alert_meteors?: string[];

  air_quality_score?: number | null;
  air_quality_pm2_5?: number | null;
  air_quality_pm10?: number | null;
  air_quality_no2?: number | null;
  air_quality_ozone?: number | null;
  air_quality_uv_index?: number | null;
  
  request_id?: string | null;
  position?: number | null;
  weather_temp_c?: number | null;
  weather_precip_prob?: number | null;
  weather_wind_kmh?: number | null;
  weather_is_day?: number | null;

  location: GeoJSONPoint;
  created_at?: string;
  validated: boolean;
  rating?: number | null;
};

export type EventIn = {
  activity_id: string;
  event_type: "view" | "click" | "save" | "complete" | "dismiss" | "rate";
  ts?: string;

  request_id?: string | null;
  position?: number | null;

  user_lat?: number | null;
  user_lon?: number | null;

  weather_temp_c?: number | null;
  weather_precip_prob?: number | null;
  weather_wind_kmh?: number | null;
  weather_is_day?: number | null;
  rating?: number | null;
};


export type AlertComarcaOut = {
  code: string;
  name: string;
  severity: number;
  threshold?: string | null;
};

export type AffectedActivityOut = {
  id: string;
  name: string;
  category: string;
  indoor: boolean;
};

export type AlertActionCard = {
  id: string;
  meteor: string;
  severity: number;
  severity_label: string;
  starts_at: string;
  ends_at: string;
  affected_comarques: AlertComarcaOut[];
  recommended_action: string;
  recommender_effect: string;
  affected_recommended_activities: AffectedActivityOut[];
};

export type AlertTimelineSlot = {
  label: string;
  starts_at: string;
  ends_at: string;
  max_severity: number;
  cards: AlertActionCard[];
};

export type StationSummaryOut = {
  codi: string;
  nom?: string | null;
  latitud?: number | null;
  longitud?: number | null;
  altitud?: number | null;
  comarca?: string | null;
};

export type StationVariableSummaryOut = {
  codi: number;
  nom: string;
  unitat: string;
  acronim: string;
  tipus: string;
  decimals: number;
};

export type StationValuePointOut = {
  time: string;
  value: number;
};

export type DailyStationStatOut = {
  date: string;
  min_value?: number | null;
  max_value?: number | null;
  avg_value?: number | null;
  count: number;
  expected_count: number;
  missing_count: number;
  missing_pct: number;
};

export type MissingIntervalOut = {
  starts_at: string;
  ends_at: string;
  gap_hours: number;
};

export type NearbyStationComparisonOut = {
  codi: string;
  nom: string;
  distance_km: number;
  avg_value?: number | null;
  delta_vs_selected?: number | null;
};

export type SameDayLastYearOut = {
  current_date: string;
  current_avg?: number | null;
  last_year_date: string;
  last_year_avg?: number | null;
  delta?: number | null;
};

export type WeekHistoricalAverageOut = {
  current_week_start: string;
  current_week_end: string;
  current_avg?: number | null;
  historical_avg?: number | null;
  delta?: number | null;
  years_used: number;
};

export type MicroclimateInsightOut = {
  reference_station_code: string;
  reference_station_name: string;
  daypart: string;
  avg_delta?: number | null;
  sample_count: number;
  text: string;
};

export type StationExplorerOut = {
  station: StationSummaryOut;
  variable: StationVariableSummaryOut;
  points: StationValuePointOut[];
  daily_stats: DailyStationStatOut[];
  missing_intervals: MissingIntervalOut[];
  nearby_comparison: NearbyStationComparisonOut[];
  today_vs_same_day_last_year?: SameDayLastYearOut | null;
  this_week_vs_historical_average?: WeekHistoricalAverageOut | null;
  microclimate_insights: MicroclimateInsightOut[];
};

export type ForecastAccuracyPointOut = {
  time: string;
  observed: number;
  forecast: number;
  error: number;
  absolute_error: number;
};

export type ForecastAccuracySummaryOut = {
  provider: string;
  station_code: string;
  metric: "temperature" | "precipitation" | "wind";
  lead_hours: number;
  sample_count: number;
  mae?: number | null;
  rmse?: number | null;
  bias?: number | null;
  points: ForecastAccuracyPointOut[];
};