import React, { useEffect, useState } from "react";
import { Box, Typography, Paper, Stack, Button, TextField, Alert, MenuItem, Select, InputLabel, FormControl } from "@mui/material";
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

type ActivityEditForm = {
  name: string;
  category: string;
  tags: string[];
  indoor: boolean;
  covered: boolean;
  price_level: number;
  difficulty: number;
  duration_minutes: number;
  location: { type: string; coordinates: [number, number] };
};

delete (L.Icon.Default.prototype as any)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

export default function AllActivitiesPage() {
  const [activities, setActivities] = useState<Activity[]>([]);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<ActivityEditForm | null>(null);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [categories, setCategories] = useState<string[]>([]);

  const fetchActivities = () => {
    setError("");
    fetch("/api/v1/activities")
      .then(res => res.json())
      .then(setActivities)
      .catch(e => setError("Failed to fetch activities"));
  };

  const fetchCategories = () => {
    fetch("/api/v1/categories")
      .then(res => res.json())
      .then(setCategories)
      .catch(() => setCategories([]));
  };

  useEffect(() => {
    fetchActivities();
    fetchCategories();
  }, []);

  const handleDelete = async (id: string) => {
    if (window.confirm("Delete this activity?")) {
      setError(""); setMessage("");
      try {
        const res = await fetch(`/api/v1/activities/${id}`, { method: "DELETE" });
        if (!res.ok) throw new Error("Failed to delete activity");
        setMessage("Activity deleted!");
        fetchActivities();
      } catch (e: any) {
        setError(e.message);
      }
    }
  };

  const handleEditClick = (activity: Activity) => {
    setEditingId(activity.id);
    setEditForm({
      name: activity.name,
      category: activity.category,
      tags: activity.tags,
      indoor: activity.indoor,
      covered: activity.covered,
      price_level: activity.price_level,
      difficulty: activity.difficulty,
      duration_minutes: activity.duration_minutes,
      location: activity.location,
    });
  };

  const handleEditChange = (field: keyof ActivityEditForm, value: any) => {
    setEditForm(f => f ? { ...f, [field]: value } : f);
  };

  const handleUpdate = async (id: string) => {
    if (!editForm) return;
    setError(""); setMessage("");
    try {
      const payload = {
        ...editForm,
        location: {
          type: "Point",
          coordinates: [
            editForm.location.coordinates[0], // lng
            editForm.location.coordinates[1], // lat
          ],
        },
      };
      const res = await fetch(`/api/v1/activities/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) throw new Error("Failed to update activity");
      setMessage("Activity updated!");
      setEditingId(null);
      setEditForm(null);
      fetchActivities();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const handleValidate = async (id: string) => {
    setError(""); setMessage("");
    try {
      const res = await fetch(`/api/v1/activities/validate/${id}`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to validate activity");
      setMessage("Activity validated!");
      setActivities(acts => acts.map(a => a.id === id ? { ...a, validated: true } : a));
    } catch (e: any) {
      setError(e.message);
    }
  };

  return (
    <Box sx={{ maxWidth: 900, mx: "auto", mt: 4 }}>
      <Typography variant="h5" gutterBottom>All Activities</Typography>
      {message && <Alert severity="success">{message}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      <Stack spacing={2} sx={{ mt: 2 }}>
        {activities.length === 0 && <Typography>No activities found.</Typography>}
        {activities.map(a => (
          <Paper key={a.id} sx={{ p: 2, opacity: a.validated ? 1 : 0.6 }}>
            {editingId === a.id && editForm ? (
              <Box>
                <TextField
                  label="Name"
                  value={editForm.name}
                  onChange={e => handleEditChange("name", e.target.value)}
                  fullWidth
                  sx={{ mb: 1 }}
                />
                <FormControl fullWidth sx={{ mb: 1 }}>
                  <InputLabel id="category-label">Category</InputLabel>
                  <Select
                    labelId="category-label"
                    value={editForm.category}
                    label="Category"
                    onChange={e => handleEditChange("category", e.target.value)}
                  >
                    {categories.map(cat => (
                      <MenuItem key={cat} value={cat}>{cat}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <TextField
                  label="Tags (comma separated)"
                  value={editForm.tags.join(", ")}
                  onChange={e => handleEditChange("tags", e.target.value.split(",").map(t => t.trim()))}
                  fullWidth
                  sx={{ mb: 1 }}
                />
                <TextField
                  label="Price Level"
                  type="number"
                  value={editForm.price_level}
                  onChange={e => handleEditChange("price_level", Number(e.target.value))}
                  sx={{ mb: 1 }}
                />
                <TextField
                  label="Difficulty"
                  type="number"
                  value={editForm.difficulty}
                  onChange={e => handleEditChange("difficulty", Number(e.target.value))}
                  sx={{ mb: 1 }}
                />
                <TextField
                  label="Duration (min)"
                  type="number"
                  value={editForm.duration_minutes}
                  onChange={e => handleEditChange("duration_minutes", Number(e.target.value))}
                  sx={{ mb: 1 }}
                />
                {/* You can add more fields as needed */}
                <Button variant="contained" color="primary" onClick={() => handleUpdate(a.id)} sx={{ mr: 1 }}>
                  Save
                </Button>
                <Button variant="outlined" onClick={() => { setEditingId(null); setEditForm(null); }}>
                  Cancel
                </Button>
              </Box>
            ) : (
              <>
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
                <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
                  <Button variant="outlined" color="error" onClick={() => handleDelete(a.id)}>
                    Delete
                  </Button>
                  <Button variant="outlined" onClick={() => handleEditClick(a)}>
                    Update
                  </Button>
                  {!a.validated && (
                    <Button variant="contained" color="success" onClick={() => handleValidate(a.id)}>
                      Validate
                    </Button>
                  )}
                </Stack>
              </>
            )}
          </Paper>
        ))}
      </Stack>
    </Box>
  );
}