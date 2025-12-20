import { useEffect, useState } from "react";
import { Box, Button, MenuItem, Select, TextField, Typography, Alert, Stack } from "@mui/material";
import dayjs from "dayjs";

export default function MLModelTrainer() {
  const [stations, setStations] = useState<any[]>([]);
  const [models, setModels] = useState<string[]>([]);
  const [station, setStation] = useState("");
  const [model, setModel] = useState("");
  const [dateFrom, setDateFrom] = useState(dayjs().subtract(30, "day").format("YYYY-MM-DD"));
  const [dateTo, setDateTo] = useState(dayjs().format("YYYY-MM-DD"));
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/meteocat/stations")
        .then(res => res.json())
        .then(setStations);
    fetch("/api/v1/ml/models")
        .then(res => res.json())
        .then(data => setModels(Array.isArray(data.models) ? data.models : []))
        .catch(() => setModels([]));
    }, []);

  const handleTrain = async () => {
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const resp = await fetch("/api/v1/ml/train", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          station_code: station,
          date_from: dateFrom,
          date_to: dateTo,
          target_variable: "Precipitation",
          model_name: model,
        }),
      });
      const data = await resp.json();
      if (resp.ok) {
        setResult(data.model_path || "Model trained successfully!");
      } else {
        setError(data.detail || "Training failed");
      }
    } catch (e) {
      setError("Network or server error");
    }
    setLoading(false);
  };

  return (
    <Box sx={{ p: 3, maxWidth: 500 }}>
      <Typography variant="h6" gutterBottom>Train Precipitation ML Model (On demand)</Typography>
      <Stack spacing={2}>
        <TextField
          select
          label="Station"
          value={station}
          onChange={e => setStation(e.target.value)}
          fullWidth
        >
          {stations.map(st => (
            <MenuItem key={st.codi} value={st.codi}>
              {st.nom} ({st.codi})
            </MenuItem>
          ))}
        </TextField>
        <TextField
          select
          label="Model"
          value={model}
          onChange={e => setModel(e.target.value)}
          fullWidth
        >
          {models.map(m => (
            <MenuItem key={m} value={m}>{m}</MenuItem>
          ))}
        </TextField>
        <TextField
          label="Date From"
          type="date"
          value={dateFrom}
          onChange={e => setDateFrom(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Date To"
          type="date"
          value={dateTo}
          onChange={e => setDateTo(e.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <Button
          variant="contained"
          onClick={handleTrain}
          disabled={!station || !model || loading}
        >
          {loading ? "Training..." : "Train Model"}
        </Button>
        {result && <Alert severity="success">{result}</Alert>}
        {error && <Alert severity="error">{error}</Alert>}
      </Stack>
    </Box>
  );
}