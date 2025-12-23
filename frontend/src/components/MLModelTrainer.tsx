import { useEffect, useMemo, useState } from "react";
import { Box, Button, MenuItem, TextField, Typography, Alert, Stack, Divider } from "@mui/material";
import dayjs from "dayjs";

function getAuthToken(): string | null {
  return (
    localStorage.getItem('auth.token') ||
    localStorage.getItem('token') ||
    localStorage.getItem('access_token')
  );
}

async function fetchJson(url: string, init?: RequestInit): Promise<any> {
  const res = await fetch(url, init);
  const text = await res.text();
  let data: any = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = text;
  }
  if (!res.ok) {
    const msg = (data && (data.detail || data.message)) || `${res.status} ${res.statusText}`;
    throw new Error(msg);
  }
  return data;
}

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

  const recommenderBase = useMemo(() => (import.meta as any).env?.VITE_RECOMMENDER_API_BASE ?? '', []);
  const authToken = getAuthToken();
  const [recHealth, setRecHealth] = useState<{ ok: boolean; model_loaded: boolean } | null>(null);
  const [recStatus, setRecStatus] = useState<string | null>(null);
  const [recError, setRecError] = useState<string | null>(null);
  const [recBusy, setRecBusy] = useState(false);

  useEffect(() => {
    fetch("/api/v1/meteocat/stations")
      .then(res => res.json())
      .then(setStations);

    fetch("/api/v1/ml/models")
      .then(res => res.json())
      .then(data => setModels(Array.isArray(data.models) ? data.models : []))
      .catch(() => setModels([]));

    // Also fetch recommender health
    refreshRecommenderHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  async function refreshRecommenderHealth() {
    setRecError(null);
    setRecStatus("Checking recommender health…");
    try {
      const h = await fetchJson(`${recommenderBase}/health`, { method: "GET" });
      setRecHealth(h);
      setRecStatus("Recommender health OK.");
    } catch (e: any) {
      setRecHealth(null);
      setRecError(e.message ?? "Recommender health check failed");
      setRecStatus(null);
    }
  }

  async function reloadRecommenderModel() {
    setRecError(null);
    setRecStatus(null);
    setRecBusy(true);
    try {
      const headers: Record<string, string> = {};
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

      const r = await fetchJson(`${recommenderBase}/model/reload`, {
        method: "POST",
        headers,
      });
      setRecHealth(r);
      setRecStatus("Recommender model reloaded.");
    } catch (e: any) {
      setRecError(e.message ?? "Recommender reload failed (requires admin).");
    } finally {
      setRecBusy(false);
    }
  }

  return (
    <Box sx={{ p: 3, maxWidth: 700 }}>
      <Typography variant="h6" gutterBottom>
        ML Models
      </Typography>

      <Box sx={{ p: 2, border: "1px solid", borderColor: "divider", borderRadius: 2, mb: 3 }}>
        <Typography variant="subtitle1" gutterBottom>
          Train Precipitation ML Model (On demand)
        </Typography>

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

      <Divider sx={{ my: 2 }} />

      <Box sx={{ p: 2, border: "1px solid", borderColor: "divider", borderRadius: 2 }}>
        <Typography variant="subtitle1" gutterBottom>
          Recommender model operations (admin)
        </Typography>

        <Typography variant="body2" sx={{ opacity: 0.8, mb: 1 }}>
          API base: <b>{recommenderBase || "(same origin)"}</b>
        </Typography>

        <Stack spacing={2}>
          <Box>
            <Button variant="outlined" onClick={refreshRecommenderHealth} disabled={recBusy}>
              Refresh Health
            </Button>
            <Button
              sx={{ ml: 2 }}
              variant="contained"
              onClick={reloadRecommenderModel}
              disabled={recBusy}
            >
              {recBusy ? "Reloading…" : "Reload Recommender Model"}
            </Button>
          </Box>

          {recHealth && (
            <Alert severity="info">
              Health OK: {String(recHealth.ok)} — Model loaded: {String(recHealth.model_loaded)}
            </Alert>
          )}

          {recStatus && <Alert severity="success">{recStatus}</Alert>}
          {recError && <Alert severity="error">{recError}</Alert>}

          <Typography variant="body2" sx={{ mt: 1, opacity: 0.9 }}>
            <b>Training workflow</b>: Run the trainer script (offline/CI), produce <code>models/recommender.joblib</code>,
            then click “Reload Recommender Model”.
          </Typography>

          <Box sx={{ bgcolor: "background.default", borderRadius: 1, p: 1.5, fontFamily: "monospace", fontSize: 13 }}>
            <div>cd ml</div>
            <div>python -m venv .venv && source .venv/bin/activate</div>
            <div>pip install -r requirements.txt</div>
            <div>export PG_URL="postgresql+psycopg2://weather:weather@postgres:5432/activities"</div>
            <div>export MODEL_OUT="../models/recommender.joblib"</div>
            <div>python train_from_db.py</div>
          </Box>

          <Typography variant="caption" sx={{ opacity: 0.75 }}>
            Note: “Reload” expects the backend container to see the updated model file path (e.g., via a mounted volume).
          </Typography>
        </Stack>
      </Box>
    </Box>
  );
}
