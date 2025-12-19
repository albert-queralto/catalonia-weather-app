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
