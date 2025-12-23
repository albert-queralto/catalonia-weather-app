import React, { useEffect, useState } from "react";
import { Box, Typography, Paper, Stack } from "@mui/material";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

type Activity = {
  id: string;
  name: string;
  category: string;
  tags: string[];
  indoor: boolean;
  covered: boolean;
  price_level: number;
  difficulty: number;
  duration_minutes: number;
  location: { type: string; coordinates: [number, number] };
  created_at: string;
  validated: boolean;
};

// Fix default marker icon for Leaflet
delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export default function AllActivitiesPage() {
  const [activities, setActivities] = useState<Activity[]>([]);

  useEffect(() => {
    fetch("/api/v1/activities")
      .then(res => res.json())
      .then(setActivities);
  }, []);

  return (
    <Box sx={{ maxWidth: 900, mx: "auto", mt: 4 }}>
      <Typography variant="h5" gutterBottom>All Activities</Typography>
      <Stack spacing={2} sx={{ mt: 2 }}>
        {activities.length === 0 && <Typography>No activities found.</Typography>}
        {activities.map(a => (
          <Paper key={a.id} sx={{ p: 2, opacity: a.validated ? 1 : 0.6 }}>
            <Typography variant="h6">{a.name}</Typography>
            <Typography>Category: {a.category}</Typography>
            <Typography>Tags: {Array.isArray(a.tags) ? a.tags.join(", ") : a.tags}</Typography>
            <Typography>Indoor: {a.indoor ? "Yes" : "No"}, Covered: {a.covered ? "Yes" : "No"}</Typography>
            <Typography>Price Level: {a.price_level}, Difficulty: {a.difficulty}, Duration: {a.duration_minutes} min</Typography>
            <Box sx={{ my: 2 }}>
              {a.location && a.location.coordinates ? (
                <MapContainer
                  center={[a.location.coordinates[1], a.location.coordinates[0]]}
                  zoom={14}
                  style={{ height: 200, width: "100%", borderRadius: 8 }}
                  scrollWheelZoom={true}
                  dragging={true}
                  doubleClickZoom={true}
                  zoomControl={true}
                  attributionControl={true}
                >
                  <TileLayer
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    attribution="&copy; OpenStreetMap contributors"
                  />
                  <Marker position={[a.location.coordinates[1], a.location.coordinates[0]]} />
                </MapContainer>
              ) : (
                <Typography>Location: N/A</Typography>
              )}
            </Box>
            <Typography>Created: {a.created_at}</Typography>
            <Typography color={a.validated ? "green" : "orange"}>
              {a.validated ? "Validated" : "Pending"}
            </Typography>
          </Paper>
        ))}
      </Stack>
    </Box>
  );
}