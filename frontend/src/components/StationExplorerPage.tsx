import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import {
  CartesianGrid,
  Line,
  LineChart,
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  getForecastAccuracy,
  getStationExplorer,
  getStations,
  getStationVariables,
} from "../api/endpoints";
import type {
  ForecastAccuracySummaryOut,
  StationExplorerOut,
} from "../api/types";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoIso(days: number) {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

function fmt(value?: number | null, decimals = 1) {
  if (value == null || Number.isNaN(value)) return "—";
  return value.toFixed(decimals);
}

export default function StationExplorerPage() {
  const [stations, setStations] = useState<any[]>([]);
  const [variables, setVariables] = useState<any[]>([]);

  const [stationCode, setStationCode] = useState("");
  const [variableCode, setVariableCode] = useState<number | "">("");

  const [referenceStationCode, setReferenceStationCode] = useState("");

  const [dateFrom, setDateFrom] = useState(daysAgoIso(7));
  const [dateTo, setDateTo] = useState(todayIso());

  const [explorer, setExplorer] = useState<StationExplorerOut | null>(null);
  const [accuracy, setAccuracy] = useState<ForecastAccuracySummaryOut | null>(null);

  const [metric, setMetric] = useState<"temperature" | "precipitation" | "wind">("temperature");
  const [leadHours, setLeadHours] = useState(24);

  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getStations().then(setStations);
  }, []);

  useEffect(() => {
    if (!stationCode) {
      setVariables([]);
      return;
    }

    getStationVariables(stationCode).then(setVariables);
  }, [stationCode]);

  const chartData = useMemo(() => {
    if (!explorer) return [];

    return explorer.points.map(p => ({
      time: new Date(p.time).toLocaleString([], {
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
      }),
      value: p.value,
    }));
  }, [explorer]);

  const dailyData = useMemo(() => {
    if (!explorer) return [];

    return explorer.daily_stats.map(d => ({
      date: d.date,
      min: d.min_value,
      avg: d.avg_value,
      max: d.max_value,
      missing_pct: d.missing_pct,
    }));
  }, [explorer]);

  async function loadExplorer() {
    if (!stationCode || variableCode === "") return;

    setLoading(true);

    try {
      const data = await getStationExplorer({
        stationCode,
        variableCode: Number(variableCode),
        dateFrom,
        dateTo,
        referenceStationCode: referenceStationCode || undefined,
      });

      setExplorer(data);
      setAccuracy(null);
    } finally {
      setLoading(false);
    }
  }

  async function loadAccuracy() {
    if (!stationCode || variableCode === "") return;

    const data = await getForecastAccuracy({
      stationCode,
      variableCode: Number(variableCode),
      metric,
      dateFrom,
      dateTo,
      leadHours,
    });

    setAccuracy(data);
  }

  return (
    <Box sx={{ p: 3, mt: 10 }}>
      <Typography variant="h4" sx={{ mb: 2 }}>
        Meteocat Station Explorer
      </Typography>

      <Card variant="outlined" sx={{ mb: 3 }}>
        <CardContent>
          <Stack direction="row" spacing={2} flexWrap="wrap">
            <FormControl sx={{ minWidth: 280 }}>
              <InputLabel>Station</InputLabel>
              <Select
                value={stationCode}
                label="Station"
                onChange={e => {
                  setStationCode(e.target.value);
                  setVariableCode("");
                }}
              >
                {stations.map(s => (
                  <MenuItem key={s.codi} value={s.codi}>
                    {s.nom} ({s.codi})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl sx={{ minWidth: 280 }}>
              <InputLabel>Variable</InputLabel>
              <Select
                value={variableCode}
                label="Variable"
                onChange={e => setVariableCode(Number(e.target.value))}
                disabled={!stationCode}
              >
                {variables.map(v => (
                  <MenuItem key={v.codi} value={v.codi}>
                    {v.nom} ({v.unitat})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="From"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
            />

            <TextField
              label="To"
              type="date"
              InputLabelProps={{ shrink: true }}
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
            />

            <FormControl sx={{ minWidth: 280 }}>
              <InputLabel>Reference station for microclimate</InputLabel>
              <Select
                value={referenceStationCode}
                label="Reference station for microclimate"
                onChange={e => setReferenceStationCode(e.target.value)}
              >
                <MenuItem value="">None</MenuItem>
                {stations.map(s => (
                  <MenuItem key={s.codi} value={s.codi}>
                    {s.nom} ({s.codi})
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Button
              variant="contained"
              onClick={loadExplorer}
              disabled={!stationCode || variableCode === "" || loading}
            >
              {loading ? "Loading..." : "Load explorer"}
            </Button>
          </Stack>
        </CardContent>
      </Card>

      {!explorer && (
        <Alert severity="info">
          Select a station, variable, and date range to view historical trends.
        </Alert>
      )}

      {explorer && (
        <>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }} flexWrap="wrap">
            <Chip label={`Station: ${explorer.station.nom}`} />
            <Chip label={`Variable: ${explorer.variable.nom}`} />
            <Chip label={`Unit: ${explorer.variable.unitat}`} />
            {explorer.station.comarca && <Chip label={`Comarca: ${explorer.station.comarca}`} />}
            {explorer.station.altitud != null && <Chip label={`Altitude: ${explorer.station.altitud} m`} />}
          </Stack>

          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6">
                Trend
              </Typography>

              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="time" minTickGap={24} />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="value" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6">
                Daily min / average / max
              </Typography>

              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={dailyData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="min" dot={false} />
                  <Line type="monotone" dataKey="avg" dot={false} />
                  <Line type="monotone" dataKey="max" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6">
                Missing data indicators
              </Typography>

              {explorer.daily_stats.some(d => d.missing_pct > 0) ? (
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart data={dailyData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="missing_pct" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <Alert severity="success">No missing data detected for this range.</Alert>
              )}

              {explorer.missing_intervals.length > 0 && (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle2">Large gaps:</Typography>
                  <Stack direction="row" spacing={1} flexWrap="wrap">
                    {explorer.missing_intervals.slice(0, 20).map((gap, idx) => (
                      <Chip
                        key={idx}
                        label={`${new Date(gap.starts_at).toLocaleString()} → ${new Date(gap.ends_at).toLocaleString()} (${gap.gap_hours}h)`}
                        size="small"
                      />
                    ))}
                  </Stack>
                </Box>
              )}
            </CardContent>
          </Card>

          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6">
                Nearby station comparison
              </Typography>

              {explorer.nearby_comparison.length === 0 ? (
                <Alert severity="info">No nearby stations with comparable data.</Alert>
              ) : (
                <Stack spacing={1}>
                  {explorer.nearby_comparison.map(s => (
                    <Box key={s.codi}>
                      <b>{s.nom}</b> — {s.distance_km.toFixed(1)} km away — avg{" "}
                      {fmt(s.avg_value)} {explorer.variable.unitat} — delta{" "}
                      {fmt(s.delta_vs_selected)} {explorer.variable.unitat}
                    </Box>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>

          <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mb: 3 }}>
            <Card variant="outlined" sx={{ minWidth: 300, flex: 1 }}>
              <CardContent>
                <Typography variant="h6">
                  Today vs same day last year
                </Typography>

                {explorer.today_vs_same_day_last_year ? (
                  <Typography>
                    {explorer.today_vs_same_day_last_year.current_date}:{" "}
                    {fmt(explorer.today_vs_same_day_last_year.current_avg)}{" "}
                    {explorer.variable.unitat}
                    <br />
                    {explorer.today_vs_same_day_last_year.last_year_date}:{" "}
                    {fmt(explorer.today_vs_same_day_last_year.last_year_avg)}{" "}
                    {explorer.variable.unitat}
                    <br />
                    Difference: {fmt(explorer.today_vs_same_day_last_year.delta)}{" "}
                    {explorer.variable.unitat}
                  </Typography>
                ) : (
                  <Alert severity="info">Not enough data.</Alert>
                )}
              </CardContent>
            </Card>

            <Card variant="outlined" sx={{ minWidth: 300, flex: 1 }}>
              <CardContent>
                <Typography variant="h6">
                  This week vs historical average
                </Typography>

                {explorer.this_week_vs_historical_average ? (
                  <Typography>
                    Current week avg:{" "}
                    {fmt(explorer.this_week_vs_historical_average.current_avg)}{" "}
                    {explorer.variable.unitat}
                    <br />
                    Historical avg:{" "}
                    {fmt(explorer.this_week_vs_historical_average.historical_avg)}{" "}
                    {explorer.variable.unitat}
                    <br />
                    Difference:{" "}
                    {fmt(explorer.this_week_vs_historical_average.delta)}{" "}
                    {explorer.variable.unitat}
                    <br />
                    Years used: {explorer.this_week_vs_historical_average.years_used}
                  </Typography>
                ) : (
                  <Alert severity="info">Not enough historical data.</Alert>
                )}
              </CardContent>
            </Card>
          </Stack>

          {explorer.microclimate_insights.length > 0 && (
            <Card variant="outlined" sx={{ mb: 3 }}>
              <CardContent>
                <Typography variant="h6">
                  Microclimate insights
                </Typography>

                <Stack spacing={1}>
                  {explorer.microclimate_insights.map(i => (
                    <Alert key={i.daypart} severity={i.sample_count > 0 ? "info" : "warning"}>
                      {i.text}
                    </Alert>
                  ))}
                </Stack>
              </CardContent>
            </Card>
          )}

          <Card variant="outlined" sx={{ mb: 3 }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Forecast accuracy dashboard
              </Typography>

              <Stack direction="row" spacing={2} flexWrap="wrap" sx={{ mb: 2 }}>
                <FormControl sx={{ minWidth: 180 }}>
                  <InputLabel>Metric</InputLabel>
                  <Select
                    value={metric}
                    label="Metric"
                    onChange={e => setMetric(e.target.value as any)}
                  >
                    <MenuItem value="temperature">Temperature</MenuItem>
                    <MenuItem value="precipitation">Precipitation</MenuItem>
                    <MenuItem value="wind">Wind</MenuItem>
                  </Select>
                </FormControl>

                <TextField
                  label="Lead hours"
                  type="number"
                  value={leadHours}
                  onChange={e => setLeadHours(Number(e.target.value))}
                />

                <Button variant="outlined" onClick={loadAccuracy}>
                  Load accuracy
                </Button>
              </Stack>

              {!accuracy && (
                <Alert severity="info">
                  Forecast accuracy needs stored forecast snapshots. Capture forecasts first, then compare them after observations arrive.
                </Alert>
              )}

              {accuracy && accuracy.sample_count === 0 && (
                <Alert severity="warning">
                  No matching forecast/observation pairs found for this range.
                </Alert>
              )}

              {accuracy && accuracy.sample_count > 0 && (
                <>
                  <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
                    <Chip label={`Samples: ${accuracy.sample_count}`} />
                    <Chip label={`MAE: ${fmt(accuracy.mae)}`} />
                    <Chip label={`RMSE: ${fmt(accuracy.rmse)}`} />
                    <Chip label={`Bias: ${fmt(accuracy.bias)}`} />
                  </Stack>

                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart
                      data={accuracy.points.map(p => ({
                        time: new Date(p.time).toLocaleString([], {
                          month: "2-digit",
                          day: "2-digit",
                          hour: "2-digit",
                        }),
                        observed: p.observed,
                        forecast: p.forecast,
                      }))}
                    >
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" minTickGap={24} />
                      <YAxis />
                      <Tooltip />
                      <Line type="monotone" dataKey="observed" dot={false} />
                      <Line type="monotone" dataKey="forecast" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </Box>
  );
}