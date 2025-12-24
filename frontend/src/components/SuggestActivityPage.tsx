import React, { useState, useEffect } from "react";
import {
  Box,
  Button,
  TextField,
  Typography,
  Alert,
  MenuItem,
  Checkbox,
  FormControlLabel,
  Stack,
} from "@mui/material";
import { MapContainer, TileLayer, Marker, useMapEvents } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

// Fix default marker icon for Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

function LocationPicker({ lat, lon, setLat, setLon }: {
  lat: string, lon: string, setLat: (v: string) => void, setLon: (v: string) => void
}) {
  const position = lat && lon ? [parseFloat(lat), parseFloat(lon)] : [41.3851, 2.1734]; // Barcelona default

  function LocationMarker() {
    useMapEvents({
      click(e) {
        setLat(e.latlng.lat.toString());
        setLon(e.latlng.lng.toString());
      }
    });
    return lat && lon ? <Marker position={position as [number, number]} /> : null;
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Select location on map (click to set)
      </Typography>
      <MapContainer
        center={position as [number, number]}
        zoom={12}
        style={{ height: 250, width: "100%", borderRadius: 8 }}
        scrollWheelZoom={true}
      >
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />
        <LocationMarker />
      </MapContainer>
      <Typography variant="body2" sx={{ mt: 1 }}>
        Latitude: {lat || "—"}, Longitude: {lon || "—"}
      </Typography>
    </Box>
  );
}

export default function SuggestActivityPage() {
  const [categories, setCategories] = useState<string[]>([]);
  const [name, setName] = useState("");
  const [category, setCategory] = useState("");
  const [tags, setTags] = useState<string>("");
  const [indoor, setIndoor] = useState(false);
  const [covered, setCovered] = useState(false);
  const [priceLevel, setPriceLevel] = useState(0);
  const [difficulty, setDifficulty] = useState(0);
  const [durationMinutes, setDurationMinutes] = useState(60);
  const [lat, setLat] = useState("");
  const [lon, setLon] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/v1/categories")
      .then(res => res.json())
      .then(setCategories)
      .catch(() => setCategories([]));
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMessage("");
    setError("");
    try {
      const latitude = parseFloat(lat);
      const longitude = parseFloat(lon);
      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) {
        throw new Error("Latitude and longitude must be set by clicking on the map.");
      }

      const payload = {
        name,
        category,
        tags: tags.split(",").map(t => t.trim()).filter(Boolean),
        indoor,
        covered,
        price_level: priceLevel,
        difficulty,
        duration_minutes: durationMinutes,
        location: {
          type: "Point",
          coordinates: [longitude, latitude],
        },
      };

      const res = await fetch("/api/v1/activities/suggest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Failed to submit activity");
      }
      setMessage("Activity suggestion submitted! Awaiting admin validation.");
      setName(""); setCategory(""); setTags(""); setIndoor(false); setCovered(false);
      setPriceLevel(0); setDifficulty(0); setDurationMinutes(60); setLat(""); setLon("");
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <Box sx={{ maxWidth: 500, mx: "auto", mt: 4, p: 3, bgcolor: "background.paper", borderRadius: 2, boxShadow: 2 }}>
      <Typography variant="h5" gutterBottom>Suggest a New Activity</Typography>
      <form onSubmit={handleSubmit}>
        <Stack spacing={2}>
          <TextField
            label="Activity Name"
            value={name}
            onChange={e => setName(e.target.value)}
            required
          />
          <TextField
            select
            label="Category"
            value={category}
            onChange={e => setCategory(e.target.value)}
            required
          >
            {categories.map(cat => (
              <MenuItem key={cat} value={cat}>{cat}</MenuItem>
            ))}
          </TextField>
          <TextField
            label="Tags (comma separated)"
            value={tags}
            onChange={e => setTags(e.target.value)}
            helperText="E.g. running, outdoor, family"
            required
          />
          <FormControlLabel
            control={<Checkbox checked={indoor} onChange={e => setIndoor(e.target.checked)} />}
            label="Indoor"
          />
          <FormControlLabel
            control={<Checkbox checked={covered} onChange={e => setCovered(e.target.checked)} />}
            label="Covered"
          />
          <TextField
            label="Price Level (0=Free, 1=Low, 2=Medium, 3=High)"
            type="number"
            value={priceLevel}
            onChange={e => setPriceLevel(Number(e.target.value))}
            inputProps={{ min: 0, max: 3 }}
            required
          />
          <TextField
            label="Difficulty (0=Easy, 1=Medium, 2=Hard)"
            type="number"
            value={difficulty}
            onChange={e => setDifficulty(Number(e.target.value))}
            inputProps={{ min: 0, max: 2 }}
            required
          />
          <TextField
            label="Duration (minutes)"
            type="number"
            value={durationMinutes}
            onChange={e => setDurationMinutes(Number(e.target.value))}
            inputProps={{ min: 1 }}
            required
          />
          <LocationPicker lat={lat} lon={lon} setLat={setLat} setLon={setLon} />
          <Button type="submit" variant="contained">Submit Suggestion</Button>
        </Stack>
      </form>
      {message && <Alert severity="success" sx={{ mt: 2 }}>{message}</Alert>}
      {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
    </Box>
  );
}