import React, { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { useAuth } from "../auth/AuthContext";
import { getRecommendations, postEvent } from "../api/endpoints";
import { Button, Checkbox, Chip, FormControlLabel, IconButton, TextField, Tooltip } from "@mui/material";
import AirIcon from "@mui/icons-material/Air";
import BookmarkBorderIcon from "@mui/icons-material/BookmarkBorder";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ExploreIcon from "@mui/icons-material/Explore";
import MyLocationIcon from "@mui/icons-material/MyLocation";
import NotInterestedIcon from "@mui/icons-material/NotInterested";
import PlaceIcon from "@mui/icons-material/Place";
import StarBorderIcon from "@mui/icons-material/StarBorder";
import ThunderstormIcon from "@mui/icons-material/Thunderstorm";
import TravelExploreIcon from "@mui/icons-material/TravelExplore";
import VisibilityIcon from "@mui/icons-material/Visibility";
import type { ActivityOut } from "../api/types";
import 'leaflet/dist/leaflet.css';
import AlertActionCards from "./AlertActionCards";
import AlertsTimeline from "./AlertsTimeline";

export default function RecommenderHome() {
  const { token, user } = useAuth();
  const [lat, setLat] = useState<number>(41.3851);
  const [lon, setLon] = useState<number>(2.1734);
  const [radiusKm, setRadiusKm] = useState(8);
  const [recs, setRecs] = useState<ActivityOut[]>([]);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [horizonHours, setHorizonHours] = useState(4);
  const [limit, setLimit] = useState(20);
  const [planningHours, setPlanningHours] = useState(48);
  const [sensitiveToAirQuality, setSensitiveToAirQuality] = useState(false);

  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapObj = useRef<L.Map | null>(null);
  const markers = useRef<L.Marker[]>([]);
  const userMarkerRef = useRef<L.Marker | null>(null);

  const center = useMemo(() => [lat, lon] as [number, number], [lat, lon]);

  const groupedRecs = useMemo(() => {
  const groups: Record<string, ActivityOut[]> = {};

  for (const rec of recs) {
    const group = rec.recommendation_group || "Good options";
    groups[group] = groups[group] || [];
    groups[group].push(rec);
  }

  return groups;
}, [recs]);

function formatBestWindow(activity: ActivityOut) {
  if (!activity.best_start) return null;

  const start = new Date(activity.best_start);
  const end = activity.best_end ? new Date(activity.best_end) : null;

  const startText = start.toLocaleString([], {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });

  const endText = end
    ? end.toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return endText ? `${startText}–${endText}` : startText;
}

  useEffect(() => {
    if (!mapRef.current || mapObj.current) return;

    const map = L.map(mapRef.current).setView(center, 11);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    map.on('click', (e: L.LeafletMouseEvent) => {
      setLat(e.latlng.lat);
      setLon(e.latlng.lng);
      setStatus(`Selected location: ${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`);
    });

    mapObj.current = map;

    return () => {
      map.remove();
      mapObj.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (mapObj.current) {
      mapObj.current.setView(center, mapObj.current.getZoom());
      renderMarkers(recs);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [center, recs]);

  function clearMarkers() {
    for (const m of markers.current) m.remove();
    markers.current = [];
    if (userMarkerRef.current) {
      userMarkerRef.current.remove();
      userMarkerRef.current = null;
    }
  }

  async function useGeolocation() {
    setStatus("Getting geolocation…");
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude);
        setLon(pos.coords.longitude);
        setStatus("Location updated.");
      },
      (err) => setStatus(`Geolocation error: ${err.message}`)
    );
  }

  async function fetchRecs() {
    if (!token) return;
    setBusy(true);
    setStatus("Fetching recommendations…");
    try {
      const data = await getRecommendations(
        token,
        lat,
        lon,
        radiusKm,
        horizonHours,
        limit,
        planningHours,
        sensitiveToAirQuality
      );
      console.log("Received recommendations:", data);
      setRecs(data);
      setStatus(`Got ${data.length} recommendations.`);
    } catch (e: any) {
      setStatus(e?.message ?? "Failed to fetch recommendations");
    } finally {
      setBusy(false);
    }
  }

  // Define custom icons
  const userIcon = L.icon({
    iconUrl: 'https://unpkg.com/leaflet@1.9.3/dist/images/marker-icon.png', // default blue
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowUrl: 'https://unpkg.com/leaflet@1.9.3/dist/images/marker-shadow.png',
  });

  const activityIcon = L.icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png', // red marker
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowUrl: 'https://unpkg.com/leaflet@1.9.3/dist/images/marker-shadow.png',
  });

  function renderMarkers(data: ActivityOut[]) {
    if (!mapObj.current) return;
    clearMarkers();

    // User marker
    const userMarker = L.marker([lat, lon], { icon: userIcon })
      .addTo(mapObj.current)
      .bindPopup("You are here");
    userMarkerRef.current = userMarker;

    // Activity markers
    data.forEach(activity => {
      console.log("Rendering marker for activity:", activity);
      if (
        activity.location &&
        Array.isArray(activity.location.coordinates) &&
        activity.location.coordinates.length === 2
      ) {
        // GeoJSON: [lon, lat], Leaflet: [lat, lon]
        const [lon, lat] = activity.location.coordinates;
        const marker = L.marker([lat, lon], {
          icon: activityIcon
        })
          .addTo(mapObj.current)
          .bindPopup(
            `<b>${activity.name}</b><br/>${activity.category}<br/>${activity.recommendation_label ?? ""}`
          );
        markers.current.push(marker);
      }
    });
  }

  async function sendEvent(
    activity: ActivityOut,
    event_type: "click" | "save" | "complete" | "dismiss" | "rate",
    rating?: number,
    dismiss_reason?: string
  ) {
    if (!token || !user) return;
    try {
      await postEvent(token, {
        activity_id: activity.id,
        event_type,
        request_id: activity.request_id ?? null,
        position: activity.position ?? null,
        user_lat: lat,
        user_lon: lon,
        weather_temp_c: activity.weather_temp_c ?? null,
        weather_precip_prob: activity.weather_precip_prob ?? null,
        weather_wind_kmh: activity.weather_wind_kmh ?? null,
        weather_is_day: activity.weather_is_day ?? null,
        rating,
        apparent_temp_c: activity.apparent_temp_c ?? null,
        uv_index: activity.uv_index ?? activity.air_quality_uv_index ?? null,
        air_quality_score: activity.air_quality_score ?? null,
        air_quality_label: activity.air_quality_label ?? null,
        ozone: activity.ozone ?? activity.air_quality_ozone ?? null,
        alert_severity: activity.alert_severity ?? null,
        weather_condition: activity.weather_condition ?? null,

        ranking_strategy: activity.ranking_strategy ?? null,
        model_score: activity.base_score ?? null,
        model_confidence: activity.model_confidence ?? null,
        exploration_bucket: activity.exploration_bucket ?? null,

        dismiss_reason: dismiss_reason ?? null,
      });
      setStatus(
        event_type === "rate"
          ? `Rated ${activity.name} with ${rating} stars`
          : `Event sent: ${event_type} (${activity.name})`
      );
    } catch (e: any) {
      setStatus(e?.message ?? "Failed to send event");
    }
  }

  function RatingButtons({ activity }: { activity: ActivityOut }) {
    return (
      <div className="rating-controls">
        <span className="rating-controls__label">Rate</span>
        {[1, 2, 3, 4, 5].map((star) => (
          <Tooltip key={star} title={`Rate ${star} star${star === 1 ? "" : "s"}`}>
            <IconButton
              aria-label={`Rate ${activity.name} ${star} star${star === 1 ? "" : "s"}`}
              size="small"
              color="primary"
              onClick={() => sendEvent(activity, "rate", star)}
            >
              <StarBorderIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        ))}
      </div>
    );
  }

  function activityIsOutdoor(activity: ActivityOut) {
    return !activity.indoor;
  }

  function activityMeta(activity: ActivityOut) {
    return `${activity.category} | ${activity.indoor ? "indoor" : "outdoor"} | ${activity.distance_km.toFixed(2)} km`;
  }

  return (
    <div className="weather-workspace">
      <section className="weather-page-header" aria-labelledby="recommender-title">
        <p className="weather-page-header__eyebrow">Weather-aware planner</p>
        <h1 id="recommender-title">Activity Recommendations</h1>
        <p>
          Find nearby options with local forecast timing, air quality sensitivity, and active
          warnings considered together.
        </p>
        <div className="weather-page-header__status" role="status" aria-live="polite">
          {status || "Ready from Barcelona coordinates. Select the map or tune the filters."}
        </div>
      </section>

      <section className="recommendation-tools" aria-label="Recommendation controls">
        <div className="control-panel">
          <div className="control-panel__header">
            <div>
              <h2>Search Conditions</h2>
              <p>Adjust the location, range, and planning window for the next recommendation run.</p>
            </div>
            <Chip
              icon={<ExploreIcon />}
              label={`${radiusKm} km radius`}
              color="secondary"
              variant="outlined"
            />
          </div>

          <div className="control-panel__grid">
            <TextField
              label="Latitude"
              type="number"
              value={lat}
              onChange={e => setLat(Number(e.target.value))}
              size="small"
              fullWidth
            />
            <TextField
              label="Longitude"
              type="number"
              value={lon}
              onChange={e => setLon(Number(e.target.value))}
              size="small"
              fullWidth
            />
            <TextField
              label="Radius (km)"
              type="number"
              value={radiusKm}
              onChange={e => setRadiusKm(Number(e.target.value))}
              size="small"
              fullWidth
            />
            <TextField
              label="Horizon (hours)"
              type="number"
              value={horizonHours}
              onChange={e => setHorizonHours(Number(e.target.value))}
              size="small"
              fullWidth
            />
            <TextField
              label="Limit"
              type="number"
              value={limit}
              onChange={e => setLimit(Number(e.target.value))}
              size="small"
              fullWidth
            />
            <TextField
              label="Plan over (hours)"
              type="number"
              value={planningHours}
              onChange={e => setPlanningHours(Number(e.target.value))}
              size="small"
              fullWidth
            />
          </div>

          <div className="control-panel__actions">
            <FormControlLabel
              control={
                <Checkbox
                  checked={sensitiveToAirQuality}
                  onChange={e => setSensitiveToAirQuality(e.target.checked)}
                />
              }
              label="Sensitive to air quality"
            />
            <Button variant="outlined" startIcon={<MyLocationIcon />} onClick={useGeolocation}>
              Use my location
            </Button>
            <Button
              variant="contained"
              color="primary"
              startIcon={<TravelExploreIcon />}
              onClick={fetchRecs}
              disabled={busy}
            >
              {busy ? "Loading..." : "Get recommendations"}
            </Button>
          </div>
        </div>

        <div className="alert-stream">
          <AlertActionCards lat={lat} lon={lon} radiusKm={radiusKm} />
          <AlertsTimeline lat={lat} lon={lon} radiusKm={radiusKm} />
        </div>
      </section>

      <section className="recommendation-layout" aria-label="Recommendations and map">
        <div className="recommendation-column">
          {Object.keys(groupedRecs).length === 0 ? (
            <div className="empty-state">
              <h2>No recommendations loaded yet</h2>
              <p>Run a search to see activity options ranked for this place and forecast window.</p>
            </div>
          ) : (
            Object.entries(groupedRecs).map(([group, items]) => (
              <section key={group} className="recommendation-group">
                <h2 className="recommendation-group__title">
                  {group}
                  <span>{items.length} option{items.length === 1 ? "" : "s"}</span>
                </h2>

                {items.map((r) => {
                  const bestWindow = formatBestWindow(r);

                  return (
                    <article key={r.id} className="activity-card">
                      <div className="activity-card__topline">
                        <h3 className="activity-card__name">{r.name}</h3>
                        <span className="activity-card__rank">
                          {r.position != null ? `#${r.position}` : "Unranked"}
                        </span>
                      </div>

                      <div className="activity-card__chips">
                        {r.recommendation_label && (
                          <Chip label={r.recommendation_label} size="small" color="primary" />
                        )}

                        {bestWindow && (
                          <Chip label={bestWindow} size="small" variant="outlined" color="secondary" />
                        )}

                        {activityIsOutdoor(r) && (
                          <Chip
                            icon={<ThunderstormIcon />}
                            label="Weather alerts"
                            size="small"
                            color="warning"
                            variant="outlined"
                          />
                        )}

                        {sensitiveToAirQuality && activityIsOutdoor(r) && (
                          <Chip
                            icon={<AirIcon />}
                            label="Air quality"
                            size="small"
                            color="secondary"
                            variant="outlined"
                          />
                        )}
                      </div>

                      <div className="activity-card__meta">
                        {activityMeta(r)}
                      </div>

                      <div className="activity-card__reason">
                        {r.reason}
                      </div>

                      <div className="activity-card__actions">
                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<VisibilityIcon />}
                          onClick={() => sendEvent(r, "click")}
                        >
                          View
                        </Button>

                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<BookmarkBorderIcon />}
                          onClick={() => sendEvent(r, "save")}
                        >
                          Save
                        </Button>

                        <Button
                          size="small"
                          variant="outlined"
                          startIcon={<CheckCircleOutlineIcon />}
                          onClick={() => sendEvent(r, "complete")}
                        >
                          Completed
                        </Button>

                        <Button
                          size="small"
                          variant="outlined"
                          color="warning"
                          startIcon={<ThunderstormIcon />}
                          onClick={() => sendEvent(r, "dismiss", undefined, "bad_weather")}
                        >
                          Bad weather
                        </Button>

                        <Button
                          size="small"
                          variant="outlined"
                          color="inherit"
                          startIcon={<NotInterestedIcon />}
                          onClick={() => sendEvent(r, "dismiss", undefined, "not_interested")}
                        >
                          Not interested
                        </Button>

                        <Button
                          size="small"
                          variant="outlined"
                          color="inherit"
                          startIcon={<PlaceIcon />}
                          onClick={() => sendEvent(r, "dismiss", undefined, "too_far")}
                        >
                          Too far
                        </Button>
                      </div>

                      <RatingButtons activity={r} />
                    </article>
                  );
                })}
              </section>
            ))
          )}
        </div>

        <aside className="map-panel" aria-label="Location map">
          <div className="map-panel__surface">
            <div className="map-panel__header">
              <div>
                <h2>Selected Area</h2>
                <p>
                  {lat.toFixed(5)}, {lon.toFixed(5)}
                </p>
              </div>
              <Chip icon={<PlaceIcon />} label="Map picker" size="small" color="secondary" />
            </div>

            <div className="map-frame">
              <div ref={mapRef} />
            </div>

            <p className="map-panel__hint">
              Click the map to select latitude and longitude. Activity markers appear when
              location data is available.
            </p>
          </div>
        </aside>
      </section>
    </div>
  );
}
