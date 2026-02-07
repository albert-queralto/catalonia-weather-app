import React, { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import { useAuth } from "../auth/AuthContext";
import { getRecommendations, postEvent } from "../api/endpoints";
import { TextField, Button } from '@mui/material';
import type { ActivityOut } from "../api/types";
import 'leaflet/dist/leaflet.css';

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

  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapObj = useRef<L.Map | null>(null);
  const markers = useRef<L.Marker[]>([]);
  const userMarkerRef = useRef<L.Marker | null>(null);

  const center = useMemo(() => [lat, lon] as [number, number], [lat, lon]);

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
    if (!token || !user) return;
    setBusy(true);
    setStatus("Fetching recommendations…");
    try {
      const data = await getRecommendations(token, lat, lon, radiusKm, horizonHours, limit);
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
          .bindPopup(`<b>${activity.name}</b><br/>${activity.category}`);
        markers.current.push(marker);
      }
    });
  }

  async function sendEvent(activity: ActivityOut, event_type: "click" | "save" | "dismiss") {
    if (!token || !user) return;
    try {
      await postEvent(token, {
        user_id: user.id,
        activity_id: activity.id,
        event_type,
        request_id: activity.request_id ?? null,
        user_lat: lat,
        user_lon: lon
      });
      setStatus(`Event sent: ${event_type} (${activity.name})`);
    } catch (e: any) {
      setStatus(e?.message ?? "Failed to send event");
    }
  }

  return (
    <div style={{ padding: 16 }}>
      <h2>Activity Recommendations</h2>

      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", alignItems: "end" }}>
        <TextField
          label="Latitude"
          type="number"
          value={lat}
          onChange={e => setLat(Number(e.target.value))}
          size="small"
          style={{ marginBottom: 16 }}
        />
        <TextField
          label="Longitude"
          type="number"
          value={lon}
          onChange={e => setLon(Number(e.target.value))}
          size="small"
          style={{ marginBottom: 16 }}
        />
        <TextField
          label="Radius (km)"
          type="number"
          value={radiusKm}
          onChange={e => setRadiusKm(Number(e.target.value))}
          size="small"
          style={{ marginBottom: 16 }}
        />
        <TextField
          label="Horizon (hours)"
          type="number"
          value={horizonHours}
          onChange={e => setHorizonHours(Number(e.target.value))}
          size="small"
          style={{ marginBottom: 16 }}
        />
        <TextField
          label="Limit"
          type="number"
          value={limit}
          onChange={e => setLimit(Number(e.target.value))}
          size="small"
          style={{ marginBottom: 16 }}
        />
        <Button variant="outlined" onClick={useGeolocation} sx={{ mr: 1 }}>
          Use my location
        </Button>
        <Button variant="contained" color="primary" onClick={fetchRecs} disabled={busy}>
          {busy ? "Loading…" : "Get recommendations"}
        </Button>
      </div>

      <div style={{ marginTop: 10, opacity: 0.8 }}>{status}</div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 16 }}>
        <div>
          {recs.map((r) => (
            <div key={r.id} style={{ border: "1px solid #eee", borderRadius: 8, padding: 12, marginBottom: 10 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
                <b>{r.name}</b>
              </div>
              <div style={{ marginTop: 6 }}>
                {r.category} • {r.indoor ? "indoor" : "outdoor"} • {r.distance_km.toFixed(2)} km
              </div>
              <div style={{ marginTop: 6, fontSize: 13, opacity: 0.9 }}>
                {r.reason}
              </div>
              <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
                <Button
                  variant="outlined"
                  size="small"
                  onClick={() => sendEvent(r, "click")}
                >
                  Click
                </Button>
                <Button
                  variant="contained"
                  color="success"
                  size="small"
                  onClick={() => sendEvent(r, "save")}
                >
                  Save
                </Button>
                <Button
                  variant="outlined"
                  color="error"
                  size="small"
                  onClick={() => sendEvent(r, "dismiss")}
                >
                  Dismiss
                </Button>
              </div>
            </div>
          ))}
        </div>

        <div>
          <div style={{ border: "1px solid #eee", borderRadius: 8, overflow: "hidden" }}>
            <div ref={mapRef} style={{ height: 520 }} />
          </div>
          <div style={{ marginTop: 8, fontSize: 12, opacity: 0.7 }}>
            Click the map to select latitude and longitude.<br />
            Activity markers are shown if location is available.<br />
          </div>
        </div>
      </div>
    </div>
  );
}