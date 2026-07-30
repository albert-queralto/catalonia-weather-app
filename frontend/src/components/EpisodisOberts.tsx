import { useEffect, useMemo, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import "leaflet/dist/leaflet.css";
import { API_BASE } from "../api/client";
import type { AvisAfectacio, EpisodiObert, Evolucio } from "../api/types";

const LeafletMapContainer = MapContainer as any;
const LeafletTileLayer = TileLayer as any;
const LeafletGeoJSON = GeoJSON as any;

const DAY_LABELS = ["Today", "Tomorrow"];

type PeriodOption = {
  name: string;
  affectedCount: number;
  maxDanger: number;
};

type EnrichedAfectacio = AvisAfectacio & {
  meteor: string;
  avisoType: string;
  avisoStatus: string | null;
  evolution: Evolucio;
  periodName: string;
};

type ComarcaWarningSummary = {
  idComarca: number;
  danger: number;
  level: number;
  warnings: EnrichedAfectacio[];
};

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) return "-";
  return new Date(value).toLocaleString([], {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function dangerColor(danger: number): string {
  const colors: Record<number, string> = {
    1: "#fff7bc",
    2: "#fec44f",
    3: "#fe9929",
    4: "#ec7014",
    5: "#cc4c02",
    6: "#8c2d04",
  };
  return colors[danger] || "#f03b20";
}

function severityLabel(danger: number): string {
  if (danger >= 5) return "Very high";
  if (danger >= 3) return "High";
  if (danger >= 1) return "Moderate";
  return "None";
}

function getComarcaNameMap(geojson: any): Map<number, string> {
  const map = new Map<number, string>();

  for (const feature of geojson?.features || []) {
    const code = Number(feature?.properties?.code);
    const name = feature?.properties?.name;

    if (!Number.isNaN(code) && name) {
      map.set(code, name);
    }
  }

  return map;
}

function getPeriodOptions(episodis: EpisodiObert[]): PeriodOption[] {
  const periods = new Map<string, PeriodOption>();

  for (const episode of episodis) {
    for (const aviso of episode.avisos || []) {
      for (const evolution of aviso.evolucions || []) {
        for (const period of evolution.periodes || []) {
          const option = periods.get(period.nom) || {
            name: period.nom,
            affectedCount: 0,
            maxDanger: 0,
          };

          const affected = period.afectacions || [];
          option.affectedCount += affected.filter(item => item.idComarca !== null).length;
          option.maxDanger = Math.max(
            option.maxDanger,
            ...affected.map(item => Number(item.perill || 0)),
          );
          periods.set(period.nom, option);
        }
      }
    }
  }

  return Array.from(periods.values()).sort((a, b) => a.name.localeCompare(b.name));
}

function getAffectedForPeriod(
  episodis: EpisodiObert[],
  periodName: string | null,
): EnrichedAfectacio[] {
  if (!periodName) return [];

  const affected: EnrichedAfectacio[] = [];

  for (const episode of episodis) {
    for (const aviso of episode.avisos || []) {
      for (const evolution of aviso.evolucions || []) {
        for (const period of evolution.periodes || []) {
          if (period.nom !== periodName) continue;

          for (const item of period.afectacions || []) {
            if (item.idComarca === null) continue;

            affected.push({
              ...item,
              meteor: episode.meteor?.nom || "Weather",
              avisoType: aviso.tipus,
              avisoStatus: aviso.estat,
              evolution,
              periodName: period.nom,
            });
          }
        }
      }
    }
  }

  return affected;
}

function summarizeByComarca(affected: EnrichedAfectacio[]): Map<number, ComarcaWarningSummary> {
  const byComarca = new Map<number, ComarcaWarningSummary>();

  for (const warning of affected) {
    if (warning.idComarca === null) continue;

    const current = byComarca.get(warning.idComarca) || {
      idComarca: warning.idComarca,
      danger: 0,
      level: 0,
      warnings: [],
    };

    current.danger = Math.max(current.danger, Number(warning.perill || 0));
    current.level = Math.max(current.level, Number(warning.nivell || 0));
    current.warnings.push(warning);
    byComarca.set(warning.idComarca, current);
  }

  return byComarca;
}

function firstPeriodWithWarnings(options: PeriodOption[]): string | null {
  return options.find(option => option.affectedCount > 0)?.name || options[0]?.name || null;
}

export default function EpisodisObertsMap() {
  const [dayOffset, setDayOffset] = useState(0);
  const [data, setData] = useState<EpisodiObert[]>([]);
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null);
  const [periods, setPeriods] = useState<PeriodOption[]>([]);
  const [comarcasGeoJson, setComarcasGeoJson] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE}/comarcas/geojson`)
      .then(res => res.json())
      .then(setComarcasGeoJson)
      .catch(() => setComarcasGeoJson(null));
  }, []);

  useEffect(() => {
    const base = new Date();
    base.setHours(0, 0, 0, 0);
    base.setDate(base.getDate() + dayOffset);
    const year = base.getFullYear();
    const month = String(base.getMonth() + 1).padStart(2, "0");
    const day = String(base.getDate()).padStart(2, "0");

    setLoading(true);
    setError(null);

    fetch(`${API_BASE}/meteocat/episodis-oberts?year=${year}&month=${month}&day=${day}`)
      .then(async res => {
        if (!res.ok) {
          const text = await res.text();
          throw new Error(`HTTP ${res.status}: ${text}`);
        }
        return res.json();
      })
      .then((res: EpisodiObert[]) => {
        const nextData = Array.isArray(res) ? res : [];
        const nextPeriods = getPeriodOptions(nextData);

        setData(nextData);
        setPeriods(nextPeriods);
        setSelectedPeriod(firstPeriodWithWarnings(nextPeriods));
      })
      .catch(err => {
        setData([]);
        setPeriods([]);
        setSelectedPeriod(null);
        setError(err.message || "Failed to fetch Meteocat SMP episodes");
      })
      .finally(() => setLoading(false));
  }, [dayOffset]);

  const comarcaNames = useMemo(() => getComarcaNameMap(comarcasGeoJson), [comarcasGeoJson]);
  const affected = useMemo(
    () => getAffectedForPeriod(data, selectedPeriod),
    [data, selectedPeriod],
  );
  const warningsByComarca = useMemo(() => summarizeByComarca(affected), [affected]);
  const totalWarnings = data.reduce(
    (sum, episode) =>
      sum +
      (episode.avisos || []).reduce(
        (avisSum, aviso) =>
          avisSum +
          (aviso.evolucions || []).reduce(
            (evoSum, evolution) =>
              evoSum +
              (evolution.periodes || []).reduce(
                (periodSum, period) => periodSum + (period.afectacions || []).length,
                0,
              ),
            0,
          ),
        0,
      ),
    0,
  );

  function style(feature: any) {
    const code = Number(feature.properties.code);
    const found = warningsByComarca.get(code);

    if (found) {
      return {
        fillColor: dangerColor(found.danger),
        weight: 2,
        opacity: 1,
        color: "#1f2937",
        fillOpacity: 0.74,
      };
    }

    return {
      fillColor: "#eeeeee",
      weight: 1,
      opacity: 0.55,
      color: "#8a8a8a",
      fillOpacity: 0.22,
    };
  }

  function onEachFeature(feature: any, layer: any) {
    const code = Number(feature.properties.code);
    const comarcaName = feature.properties.name;
    const found = warningsByComarca.get(code);

    let tooltipContent = `<strong>${escapeHtml(comarcaName)}</strong>`;

    if (found) {
      tooltipContent += `<br/>Danger: ${found.danger} (${severityLabel(found.danger)})`;
      tooltipContent += `<br/>Threshold level: ${found.level || "-"}`;
      tooltipContent += "<br/>";
      tooltipContent += found.warnings
        .map(item => {
          const threshold = item.llindar || item.evolution.llindar1 || item.evolution.llindar2 || "";
          return [
            escapeHtml(item.meteor),
            threshold ? escapeHtml(threshold) : null,
            item.evolution.distribucioGeografica
              ? escapeHtml(item.evolution.distribucioGeografica)
              : null,
          ].filter(Boolean).join(" · ");
        })
        .join("<br/>");
    } else {
      tooltipContent += "<br/>No warnings for this period.";
    }

    layer.bindTooltip(tooltipContent, { direction: "top", sticky: true });
  }

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Meteocat SMP episodes
      </Typography>

      <Stack direction="row" spacing={2} sx={{ mb: 2, flexWrap: "wrap" }}>
        {DAY_LABELS.map((label, idx) => (
          <Button
            key={label}
            variant={dayOffset === idx ? "contained" : "outlined"}
            onClick={() => setDayOffset(idx)}
          >
            {label}
          </Button>
        ))}
      </Stack>

      {loading && (
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
          <CircularProgress size={18} />
          <Typography variant="body2">Loading Meteocat SMP episodes...</Typography>
        </Stack>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!loading && !error && data.length === 0 && (
        <Alert severity="info" sx={{ mb: 2 }}>
          No open SMP episodes returned for this day.
        </Alert>
      )}

      {data.length > 0 && (
        <Alert severity={totalWarnings > 0 ? "warning" : "info"} sx={{ mb: 2 }}>
          {data.length} open episode(s), {totalWarnings} comarca-period warning(s).
        </Alert>
      )}

      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2, flexWrap: "wrap", gap: 1 }}>
        {periods.map(period => (
          <Button
            key={period.name}
            variant={selectedPeriod === period.name ? "contained" : "outlined"}
            color={period.affectedCount > 0 ? "warning" : "inherit"}
            onClick={() => setSelectedPeriod(period.name)}
          >
            {period.name} ({period.affectedCount})
          </Button>
        ))}

        <Box sx={{ display: "flex", alignItems: "center", gap: 1, ml: { md: 2 }, flexWrap: "wrap" }}>
          <Typography variant="subtitle2" sx={{ mr: 1 }}>Danger:</Typography>
          {[1, 2, 3, 4, 5, 6].map(level => (
            <Stack key={level} direction="row" spacing={0.5} alignItems="center">
              <Box sx={{ bgcolor: dangerColor(level), width: 24, height: 16, border: "1px solid #666" }} />
              <Typography variant="caption">{level}</Typography>
            </Stack>
          ))}
        </Box>
      </Stack>

      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1.25fr) minmax(360px, 0.75fr)" }, gap: 2 }}>
        <Box sx={{ minWidth: 0 }}>
          <LeafletMapContainer center={[41.8, 1.5]} zoom={8} style={{ height: "620px", width: "100%" }}>
            <LeafletTileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
            {comarcasGeoJson && (
              <LeafletGeoJSON
                key={`${dayOffset}-${selectedPeriod}-${Array.from(warningsByComarca.keys()).join("-")}`}
                data={comarcasGeoJson}
                style={style}
                onEachFeature={onEachFeature}
              />
            )}
          </LeafletMapContainer>
        </Box>

        <Box sx={{ minWidth: 0 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            SMP details
          </Typography>

          <Stack spacing={2}>
            {data.map((episode, episodeIdx) => (
              <Box key={`${episode.meteor?.nom || "episode"}-${episodeIdx}`} sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1, p: 2 }}>
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1, flexWrap: "wrap" }}>
                  <Chip label={episode.estat?.nom || "Unknown"} size="small" color="info" />
                  <Chip label={episode.meteor?.nom || "Weather"} size="small" />
                </Stack>

                {(episode.avisos || []).map((aviso, avisoIdx) => (
                  <Box key={`${aviso.tipus}-${avisoIdx}`} sx={{ mt: avisoIdx === 0 ? 0 : 2 }}>
                    <Typography variant="subtitle2">
                      {aviso.tipus}{aviso.estat ? ` · ${aviso.estat}` : ""}
                    </Typography>
                    <Typography variant="caption" display="block" sx={{ opacity: 0.8 }}>
                      Issued {formatDateTime(aviso.dataEmisio)} · Active {formatDateTime(aviso.dataInici)} to {formatDateTime(aviso.dataFi)}
                    </Typography>

                    {(aviso.evolucions || []).map((evolution, evolutionIdx) => (
                      <Box key={`${evolution.dia}-${evolutionIdx}`} sx={{ mt: 1.5 }}>
                        <Divider sx={{ mb: 1 }} />
                        <Typography variant="body2" fontWeight="bold">
                          {formatDateTime(evolution.dia)}
                        </Typography>
                        <Stack direction="row" spacing={1} sx={{ my: 1, flexWrap: "wrap", gap: 1 }}>
                          {evolution.distribucioGeografica && (
                            <Chip size="small" label={`Distribution: ${evolution.distribucioGeografica}`} />
                          )}
                          {evolution.representatiu !== null && (
                            <Chip size="small" label={`Representative threshold: ${evolution.representatiu}`} />
                          )}
                          {evolution.valorMaxim && (
                            <Chip size="small" label={`Max: ${evolution.valorMaxim}`} />
                          )}
                        </Stack>

                        {evolution.llindar1 && (
                          <Typography variant="body2">Threshold 1: {evolution.llindar1}</Typography>
                        )}
                        {evolution.llindar2 && (
                          <Typography variant="body2">Threshold 2: {evolution.llindar2}</Typography>
                        )}
                        {evolution.comentari && (
                          <Typography variant="body2" sx={{ mt: 1 }}>
                            {evolution.comentari}
                          </Typography>
                        )}

                        <Stack spacing={1} sx={{ mt: 1 }}>
                          {(evolution.periodes || []).map(period => {
                            const periodAffected = (period.afectacions || []).filter(item => item.idComarca !== null);
                            const maxDanger = Math.max(0, ...periodAffected.map(item => Number(item.perill || 0)));
                            const isSelected = selectedPeriod === period.nom;

                            return (
                              <Box
                                key={`${evolution.dia}-${period.nom}`}
                                sx={{
                                  borderLeft: "4px solid",
                                  borderColor: periodAffected.length > 0 ? dangerColor(maxDanger) : "divider",
                                  pl: 1.5,
                                  py: 0.5,
                                  bgcolor: isSelected ? "action.selected" : "transparent",
                                }}
                              >
                                <Stack direction="row" spacing={1} alignItems="center" sx={{ flexWrap: "wrap", gap: 1 }}>
                                  <Button size="small" variant={isSelected ? "contained" : "outlined"} onClick={() => setSelectedPeriod(period.nom)}>
                                    {period.nom}
                                  </Button>
                                  <Typography variant="body2">
                                    {periodAffected.length} affected comarca(s)
                                  </Typography>
                                  {maxDanger > 0 && (
                                    <Chip size="small" label={`Danger ${maxDanger}`} color={maxDanger >= 4 ? "error" : "warning"} />
                                  )}
                                </Stack>

                                {periodAffected.length > 0 && (
                                  <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                                    {periodAffected
                                      .map(item => {
                                        const name = comarcaNames.get(Number(item.idComarca)) || `Comarca ${item.idComarca}`;
                                        return `${name}: perill ${item.perill ?? "-"}, nivell ${item.nivell ?? "-"}${item.llindar ? `, ${item.llindar}` : ""}${item.auxiliar ? ", auxiliary" : ""}`;
                                      })
                                      .join(" · ")}
                                  </Typography>
                                )}
                              </Box>
                            );
                          })}
                        </Stack>
                      </Box>
                    ))}
                  </Box>
                ))}
              </Box>
            ))}
          </Stack>
        </Box>
      </Box>
    </Box>
  );
}
