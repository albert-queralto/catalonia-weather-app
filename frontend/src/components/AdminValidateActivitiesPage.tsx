import React, { useEffect, useState } from "react";
import { Box, Button, Typography, Paper, Stack, Alert } from "@mui/material";

type Activity = {
  id: string;
  name: string;
  category: string;
  tags: string;
  indoor: boolean;
  covered: boolean;
  price_level: number;
  difficulty: number;
  duration_minutes: number;
  location: string;
  created_at: string;
  validated: boolean;
};

export default function AdminValidateActivitiesPage() {
  const [pending, setPending] = useState<Activity[]>([]);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function fetchPending() {
    setError("");
    try {
      const res = await fetch("/api/v1/activities/pending");
      if (!res.ok) throw new Error("Failed to fetch pending activities");
      setPending(await res.json());
    } catch (e: any) {
      setError(e.message);
    }
  }

  useEffect(() => { fetchPending(); }, []);

  async function handleValidate(id: string) {
    setError(""); setMessage("");
    try {
      const res = await fetch(`/api/v1/activities/validate/${id}`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to validate activity");
      setMessage("Activity validated!");
      setPending(pending => pending.filter(a => a.id !== id));
    } catch (e: any) {
      setError(e.message);
    }
  }

  return (
    <Box sx={{ maxWidth: 800, mx: "auto", mt: 4 }}>
      <Typography variant="h5" gutterBottom>Pending Activity Suggestions</Typography>
      {message && <Alert severity="success">{message}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      <Stack spacing={2} sx={{ mt: 2 }}>
        {pending.length === 0 && <Typography>No pending activities.</Typography>}
        {pending.map(a => (
          <Paper key={a.id} sx={{ p: 2 }}>
            <Typography variant="h6">{a.name}</Typography>
            <Typography>Category: {a.category}</Typography>
            <Typography>Tags: {a.tags}</Typography>
            <Typography>Indoor: {a.indoor ? "Yes" : "No"}, Covered: {a.covered ? "Yes" : "No"}</Typography>
            <Typography>Price Level: {a.price_level}, Difficulty: {a.difficulty}, Duration: {a.duration_minutes} min</Typography>
            <Typography>Location: {a.location}</Typography>
            <Typography>Created: {a.created_at}</Typography>
            <Button variant="contained" color="success" onClick={() => handleValidate(a.id)}>
              Validate
            </Button>
          </Paper>
        ))}
      </Stack>
    </Box>
  );
}