import React, { useEffect, useMemo, useRef, useState } from "react";
import maplibregl from "maplibre-gl";
import { useAuth } from "../auth/AuthContext";
import { getRecommendations, postEvent } from "../api/endpoints";
import { TextField, Button, Box } from '@mui/material';
import type { ActivityOut } from "../api/types";

function osmRasterStyle() {
  return {
    version: 8,
    sources: {
      osm: {
        type: "raster",
        tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors"
      }
    },
    layers: [{ id: "osm", type: "raster", source: "osm" }]
  } as any;
}

export default function RecommenderHome() {
  const { token, user } = useAuth();
  const [lat, setLat] = useState<number>(41.3851); // default Barcelona-ish
  const [lon, setLon] = useState<number>(2.1734);
  const [radiusKm, setRadiusKm] = useState(8); // default 8 km
  const [recs, setRecs] = useState<ActivityOut[]>([]);
  const [status, setStatus] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [horizonHours, setHorizonHours] = useState(4);
  const [limit, setLimit] = useState(20);

  const mapRef = useRef<HTMLDivElement | null>(null);
  const mapObj = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);

  const center = useMemo(() => [lon, lat] as [number, number], [lon, lat]);

  useEffect(() => {
    if (!mapRef.current || mapObj.current) return;

    const map = new maplibregl.Map({
      container: mapRef.current,
      style: osmRasterStyle(),
      center,
      zoom: 11
    });

    map.addControl(new maplibregl.NavigationControl(), "top-right");
    mapObj.current = map;

    return () => {
      map.remove();
      mapObj.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (mapObj.current) mapObj.current.setCenter(center);
  }, [center]);

  function clearMarkers() {
    for (const m of markers.current) m.remove();
    markers.current = [];
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
      setRecs(data);
      setStatus(`Got ${data.length} recommendations.`);
      renderMarkers(data);
      // impressions (“view”) ideally logged server-side in /recommendations
    } catch (e: any) {
      setStatus(e?.message ?? "Failed to fetch recommendations");
    } finally {
      setBusy(false);
    }
  }

  function renderMarkers(data: ActivityOut[]) {
    if (!mapObj.current) return;
    clearMarkers();

    // Note: your backend response does not include lat/lon. If you want markers,
    // add lat/lon to ActivityOut from backend. For now, we only mark the user.
    const userMarker = new maplibregl.Marker({ color: "#111" })
      .setLngLat([lon, lat])
      .setPopup(new maplibregl.Popup().setText("You are here"))
      .addTo(mapObj.current);

    markers.current.push(userMarker);
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
                {/*<span>score: {Number(r.score).toFixed(3)}</span>*/}
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
            Note: to show activity markers, include activity lat/lon in the backend response (extend ActivityOut).
          </div>
        </div>
      </div>
    </div>
  );
}
