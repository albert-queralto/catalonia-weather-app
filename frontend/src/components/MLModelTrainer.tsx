import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  IconButton,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import RefreshIcon from "@mui/icons-material/Refresh";
import dayjs from "dayjs";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

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

type TrainedModel = {
  id: string;
  active?: boolean;
  station_code?: string;
  station_name?: string;
  variable_code?: number;
  variable_name?: string;
  model_name?: string;
  date_from?: string;
  date_to?: string;
  rows?: number;
  training_rows?: number;
  evaluation_rows?: number;
  evaluation?: string;
  trained_at?: string;
  modified_at?: string;
  size_bytes?: number;
  metrics?: Record<string, number | null>;
  load_error?: string;
  feature_order?: string[];
};

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "-";
  return Math.abs(value) >= 100 ? value.toFixed(1) : value.toFixed(3);
}

function formatBytes(value: number | undefined): string {
  if (!value) return "-";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDateTime(value: string | undefined): string {
  return value ? dayjs(value).format("YYYY-MM-DD HH:mm") : "-";
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
  const [trainedModels, setTrainedModels] = useState<TrainedModel[]>([]);
  const [selectedModel, setSelectedModel] = useState<TrainedModel | null>(null);
  const [modelManagementBusy, setModelManagementBusy] = useState(false);
  const [modelManagementStatus, setModelManagementStatus] = useState<string | null>(null);
  const [modelManagementError, setModelManagementError] = useState<string | null>(null);

  const recommenderBase = useMemo(() => (import.meta as any).env?.VITE_API_BASE_URL ?? '', []);
  const authToken = getAuthToken();
  const [recHealth, setRecHealth] = useState<{ ok: boolean; model_loaded: boolean } | null>(null);
  const [recStatus, setRecStatus] = useState<string | null>(null);
  const [recError, setRecError] = useState<string | null>(null);
  const [recBusy, setRecBusy] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE_URL}/meteocat/stations`)
      .then(res => res.json())
      .then(setStations);

    fetch(`${API_BASE_URL}/ml/models`)
      .then(res => res.json())
      .then(data => setModels(Array.isArray(data.models) ? data.models : []))
      .catch(() => setModels([]));

    refreshTrainedModels();
    // Also fetch recommender health
    refreshRecommenderHealth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTrain = async () => {
    setLoading(true);
    setResult(null);
    setError(null);
    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

      const resp = await fetch(`${API_BASE_URL}/ml/train`, {
        method: "POST",
        headers,
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
        await refreshTrainedModels();
      } else {
        setError(data.detail || "Training failed");
      }
    } catch (e) {
      setError("Network or server error");
    }
    setLoading(false);
  };

  async function refreshTrainedModels() {
    setModelManagementError(null);
    try {
      const data = await fetchJson(`${API_BASE_URL}/ml/trained-models`);
      setTrainedModels(Array.isArray(data.models) ? data.models : []);
      setSelectedModel(current => {
        if (!current) return null;
        return (data.models || []).find((item: TrainedModel) => item.id === current.id) || null;
      });
    } catch (e: any) {
      setModelManagementError(e.message ?? "Could not load trained models");
    }
  }

  async function inspectModel(modelId: string) {
    setModelManagementBusy(true);
    setModelManagementError(null);
    try {
      const data = await fetchJson(`${API_BASE_URL}/ml/trained-models/${modelId}`);
      setSelectedModel(data);
    } catch (e: any) {
      setModelManagementError(e.message ?? "Could not load model details");
    } finally {
      setModelManagementBusy(false);
    }
  }

  async function activateModel(modelId: string) {
    setModelManagementBusy(true);
    setModelManagementError(null);
    setModelManagementStatus(null);
    try {
      const headers: Record<string, string> = {};
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

      const active = await fetchJson(`${API_BASE_URL}/ml/trained-models/${modelId}/activate`, {
        method: "POST",
        headers,
      });
      setSelectedModel(active);
      setModelManagementStatus("Model activated.");
      await refreshTrainedModels();
    } catch (e: any) {
      setModelManagementError(e.message ?? "Could not activate model");
    } finally {
      setModelManagementBusy(false);
    }
  }

  async function deleteModel(modelId: string) {
    if (!window.confirm(`Delete ${modelId}?`)) return;

    setModelManagementBusy(true);
    setModelManagementError(null);
    setModelManagementStatus(null);
    try {
      const headers: Record<string, string> = {};
      if (authToken) headers["Authorization"] = `Bearer ${authToken}`;

      await fetchJson(`${API_BASE_URL}/ml/trained-models/${modelId}`, {
        method: "DELETE",
        headers,
      });
      setModelManagementStatus("Model deleted.");
      setSelectedModel(current => (current?.id === modelId ? null : current));
      await refreshTrainedModels();
    } catch (e: any) {
      setModelManagementError(e.message ?? "Could not delete model");
    } finally {
      setModelManagementBusy(false);
    }
  }

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
    <Box sx={{ p: 3, maxWidth: 1180 }}>
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

      <Box sx={{ p: 2, border: "1px solid", borderColor: "divider", borderRadius: 2, mb: 3 }}>
        <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={2} sx={{ mb: 1 }}>
          <Typography variant="subtitle1">
            Trained station models
          </Typography>
          <Tooltip title="Refresh models">
            <span>
              <IconButton onClick={refreshTrainedModels} disabled={modelManagementBusy}>
                <RefreshIcon />
              </IconButton>
            </span>
          </Tooltip>
        </Stack>

        {modelManagementStatus && <Alert severity="success" sx={{ mb: 2 }}>{modelManagementStatus}</Alert>}
        {modelManagementError && <Alert severity="error" sx={{ mb: 2 }}>{modelManagementError}</Alert>}

        <Box sx={{ overflowX: "auto" }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Status</TableCell>
                <TableCell>Station</TableCell>
                <TableCell>Variable</TableCell>
                <TableCell>Model</TableCell>
                <TableCell>Window</TableCell>
                <TableCell align="right">Rows</TableCell>
                <TableCell align="right">MAE</TableCell>
                <TableCell align="right">RMSE</TableCell>
                <TableCell align="right">Size</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {trainedModels.length === 0 && (
                <TableRow>
                  <TableCell colSpan={10}>
                    <Typography variant="body2" sx={{ opacity: 0.75 }}>
                      No trained station models yet.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}

              {trainedModels.map(item => (
                <TableRow key={item.id} hover selected={selectedModel?.id === item.id}>
                  <TableCell>
                    {item.load_error ? (
                      <Chip size="small" label="Error" color="error" />
                    ) : item.active ? (
                      <Chip size="small" label="Active" color="success" />
                    ) : (
                      <Chip size="small" label="Saved" variant="outlined" />
                    )}
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{item.station_name || item.station_code || "-"}</Typography>
                    <Typography variant="caption" sx={{ opacity: 0.7 }}>{item.station_code || "-"}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{item.variable_name || "-"}</Typography>
                    <Typography variant="caption" sx={{ opacity: 0.7 }}>{item.variable_code ?? "-"}</Typography>
                  </TableCell>
                  <TableCell>{item.model_name || "-"}</TableCell>
                  <TableCell>
                    <Typography variant="body2">{item.date_from || "-"} to {item.date_to || "-"}</Typography>
                    <Typography variant="caption" sx={{ opacity: 0.7 }}>{formatDateTime(item.trained_at)}</Typography>
                  </TableCell>
                  <TableCell align="right">{item.rows ?? item.training_rows ?? "-"}</TableCell>
                  <TableCell align="right">{formatNumber(item.metrics?.mae)}</TableCell>
                  <TableCell align="right">{formatNumber(item.metrics?.rmse)}</TableCell>
                  <TableCell align="right">{formatBytes(item.size_bytes)}</TableCell>
                  <TableCell align="right">
                    <Tooltip title="Inspect model">
                      <span>
                        <IconButton size="small" onClick={() => inspectModel(item.id)} disabled={modelManagementBusy}>
                          <InfoOutlinedIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                    <Tooltip title="Activate model">
                      <span>
                        <IconButton
                          size="small"
                          onClick={() => activateModel(item.id)}
                          disabled={modelManagementBusy || !!item.active || !!item.load_error}
                        >
                          <CheckCircleOutlineIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                    <Tooltip title="Delete model">
                      <span>
                        <IconButton size="small" onClick={() => deleteModel(item.id)} disabled={modelManagementBusy}>
                          <DeleteOutlineIcon fontSize="small" />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Box>

        {selectedModel && (
          <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid", borderColor: "divider" }}>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }}>
              <Box sx={{ flex: 1, minWidth: 0 }}>
                <Typography variant="subtitle2" noWrap>{selectedModel.id}</Typography>
                <Typography variant="body2" sx={{ opacity: 0.8 }}>
                  {selectedModel.station_name || selectedModel.station_code || "-"} · {selectedModel.variable_name || selectedModel.variable_code || "-"}
                </Typography>
              </Box>
              <Chip size="small" label={`Evaluation: ${selectedModel.evaluation || "-"}`} />
              <Chip size="small" label={`Features: ${selectedModel.feature_order?.length ?? 0}`} />
              <Chip size="small" label={`R2: ${formatNumber(selectedModel.metrics?.r2)}`} />
            </Stack>
          </Box>
        )}
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
            <div>cd backend</div>
            <div>python -m venv .venv && source .venv/bin/activate</div>
            <div>pip install -r requirements.txt</div>
            <div>export DATABASE_URL="postgresql+psycopg2://weather:weather@postgres:5432/weather"</div>
            <div>export MODEL_OUT="../models/recommender.joblib"</div>
            <div>python -m app.services.recommender.train_from_db</div>
          </Box>

          <Typography variant="caption" sx={{ opacity: 0.75 }}>
            Note: “Reload” expects the backend container to see the updated model file path (e.g., via a mounted volume).
          </Typography>
        </Stack>
      </Box>
    </Box>
  );
}
