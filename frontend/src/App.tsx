import { useEffect, useMemo, useState } from 'react'
import WeatherMap from './components/WeatherMap'
import ComarquesMap from './components/ComarquesMap' // <-- Add this import
import { getJSON, API_BASE } from './api/client'
import type { ComarcaForecastResponse, ComarcaOut, ForecastResponse, RadarTimestamps } from './api/types'

const DEFAULT_CENTER = { lat: 41.3851, lon: 2.1734 } // Barcelona

export default function App() {
  const [center, setCenter] = useState(DEFAULT_CENTER)
  const [forecast, setForecast] = useState<ForecastResponse | null>(null)

  const [comarca, setComarca] = useState<ComarcaOut | null>(null)
  const [comarcaForecast, setComarcaForecast] = useState<ComarcaForecastResponse | null>(null)

  const [radar, setRadar] = useState<RadarTimestamps | null>(null)
  const [radarTs, setRadarTs] = useState<number | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Load radar timestamps once
    getJSON<RadarTimestamps>(`/v1/radar/timestamps`)
      .then((data) => {
        setRadar(data)
        const t = normalizeTimestamps(data)[0]
        if (t) setRadarTs(t)
      })
      .catch(() => {
        // radar optional
      })
  }, [])

  const radarTileTemplate = useMemo(() => {
    if (!radarTs) return null
    // Backend proxies tiles; keep provider swap transparent to the frontend
    return `${API_BASE}/v1/radar/tiles/${radarTs}/{z}/{x}/{y}.png`
  }, [radarTs])

  async function refreshAll(lat: number, lon: number) {
    setLoading(true)
    setError(null)
    setForecast(null)
    setComarca(null)
    setComarcaForecast(null)

    try {
      // 1) Point forecast (baseline)
      const f = await getJSON<ForecastResponse>(`/v1/forecast?lat=${lat}&lon=${lon}&tz=Europe/Madrid&source=auto`)
      setForecast(f)

      // 2) Comarca lookup + comarca forecast (Catalunya enhancement)
      const c = await getJSON<ComarcaOut | null>(`/v1/comarcas/lookup?lat=${lat}&lon=${lon}`)
      setComarca(c)

      try {
        const cf = await getJSON<ComarcaForecastResponse>(`/v1/forecast/comarca/lookup?lat=${lat}&lon=${lon}&tz=Europe/Madrid`)
        setComarcaForecast(cf)
      } catch {
        // no comarca forecast available (e.g., point outside loaded geometries)
        setComarcaForecast(null)
      }
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load data.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    refreshAll(center.lat, center.lon)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div style={{ fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif', padding: 16 }}>
      <h2 style={{ marginTop: 0 }}>Catalunya Weather (skeleton)</h2>
      <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 16 }}>
        <div>
          <ComarquesMap />
          <div style={{ marginTop: 8, fontSize: 13, color: '#444' }}>
            Click on the map to refresh. Current center: {center.lat.toFixed(4)}, {center.lon.toFixed(4)}
          </div>
          <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
            Tip: run <code>python scripts/load_comarcas.py</code> to load sample comarca polygons (PostGIS) and enable comarca lookup.
          </div>
        </div>

        <div style={{ border: '1px solid #eee', borderRadius: 12, padding: 12 }}>
          {loading && <div>Loading…</div>}
          {error && <div style={{ color: 'crimson' }}>{error}</div>}

          <h3 style={{ marginTop: 0 }}>Point forecast</h3>
          {!forecast && !loading && <div style={{ fontSize: 14, color: '#666' }}>No forecast loaded.</div>}
          {forecast && (
            <div style={{ fontSize: 14 }}>
              <div>
                Provider: <b>{forecast.provider}</b>
              </div>
              <div>Updated: {new Date(forecast.updated_at).toLocaleString()}</div>
              <div style={{ marginTop: 8 }}>
                <b>Current</b>
                <div>Temp: {forecast.current?.temperature_c !== undefined ? `${forecast.current?.temperature_c.toFixed(1)} °C` : 'n/a'}</div>
                <div>Wind gust: {forecast.current?.wind_gust_m_s !== undefined ? `${forecast.current?.wind_gust_m_s.toFixed(1)} m/s` : 'n/a'}</div>
              </div>

              <div style={{ marginTop: 10 }}>
                <b>Next hours</b>
                <ul style={{ paddingLeft: 16, margin: '6px 0' }}>
                  {forecast.hourly.slice(0, 6).map((h) => (
                    <li key={h.time}>
                      {new Date(h.time).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}:{' '}
                      {h.temperature_c !== undefined ? `${h.temperature_c.toFixed(1)} °C` : 'n/a'}{' '}
                      {h.precipitation_mm !== undefined ? `(${h.precipitation_mm.toFixed(1)} mm)` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}

          <hr style={{ margin: '12px 0' }} />

          <h3 style={{ marginTop: 0 }}>Comarca forecast (Meteocat)</h3>
          {!comarca && <div style={{ fontSize: 14, color: '#666' }}>Comarca: not found (or not loaded).</div>}
          {comarca && (
            <div style={{ fontSize: 14 }}>
              Comarca: <b>{comarca.name}</b> ({comarca.code})
            </div>
          )}
          {!comarcaForecast && comarca && (
            <div style={{ fontSize: 13, color: '#666', marginTop: 6 }}>
              No comarca forecast available yet (configure METEOCAT endpoint or keep sample mode).
            </div>
          )}
          {!comarcaForecast && !comarca && (
            <div style={{ fontSize: 13, color: '#666', marginTop: 6 }}>
              Load comarca geometries into PostGIS to enable lookup.
            </div>
          )}
          {comarcaForecast && (
            <div style={{ fontSize: 14, marginTop: 8 }}>
              <div>Provider: <b>{comarcaForecast.provider}</b></div>
              <div>Updated: {new Date(comarcaForecast.updated_at).toLocaleString()}</div>
              <ul style={{ paddingLeft: 16, margin: '6px 0' }}>
                {comarcaForecast.daily.slice(0, 5).map((d) => (
                  <li key={d.date}>
                    {new Date(d.date).toLocaleDateString()} —{' '}
                    {d.temperature_min_c !== undefined ? `${d.temperature_min_c.toFixed(0)}°` : 'n/a'} /{' '}
                    {d.temperature_max_c !== undefined ? `${d.temperature_max_c.toFixed(0)}°` : 'n/a'}
                    {d.precipitation_probability_pct !== undefined ? ` — POP ${d.precipitation_probability_pct}%` : ''}
                    {d.summary ? ` — ${d.summary}` : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <hr style={{ margin: '12px 0' }} />

          <h3 style={{ marginTop: 0 }}>Radar</h3>
          {!radar && <div style={{ fontSize: 14, color: '#666' }}>Radar timestamps not loaded.</div>}
          {radar && (
            <div style={{ fontSize: 14 }}>
              <div>Provider: {radar.provider}</div>
              <div style={{ marginTop: 8 }}>
                <label>
                  Frame:{' '}
                  <select
                    value={radarTs ?? ''}
                    onChange={(e) => setRadarTs(Number(e.target.value))}
                    style={{ width: '100%' }}
                  >
                    {normalizeTimestamps(radar).slice(0, 30).map((t) => (
                      <option key={t} value={t}>
                        {new Date(t * 1000).toLocaleString()}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div style={{ marginTop: 6, fontSize: 12, color: '#666' }}>
                Radar is rendered as a raster overlay via backend-proxied tiles.
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function normalizeTimestamps(data: RadarTimestamps): number[] {
  const raw = data.timestamps ?? []
  const out: number[] = []
  for (const item of raw) {
    if (typeof item === 'number') out.push(item)
    else if (typeof (item as any).time === 'number') out.push((item as any).time)
  }
  return out.sort((a, b) => b - a)
}