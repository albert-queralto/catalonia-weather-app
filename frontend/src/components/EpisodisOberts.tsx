import { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import { Box, Button, Typography, Paper, Stack } from "@mui/material";
import "leaflet/dist/leaflet.css";
import { EpisodiObert } from "../api/types";


function getAffectedComarques(episodis, periodNom) {
  const affected = [];
  episodis.forEach(ep =>
    (ep.avisos || []).forEach(aviso =>
      (aviso.evolucions || []).forEach(evol =>
        (evol.periodes || []).forEach(period => {
          if (period.nom === periodNom && Array.isArray(period.afectacions)) {
            affected.push(...period.afectacions.map(a => ({
              idComarca: a.idComarca,
              perill: a.perill,
              nivell: a.nivell,
              llindar: a.llindar
            })));
          }
        })
      )
    )
  );
  return affected;
}

const DAY_LABELS = ["Today", "Tomorrow"];

export default function EpisodisObertsMap() {
  const [dayOffset, setDayOffset] = useState(0);
  const [data, setData] = useState<EpisodiObert[] | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null);
  const [periods, setPeriods] = useState<string[]>([]);
  const [comarcasGeoJson, setComarcasGeoJson] = useState<any>(null);

  // Compute the date based on offset
  const date = new Date();
  date.setDate(date.getDate() + dayOffset);

  useEffect(() => {
        fetch("/api/v1/comarcas/geojson")
        .then(res => res.json())
        .then(setComarcasGeoJson);
    }, []);

    useEffect(() => {
      const base = new Date();
      base.setHours(0, 0, 0, 0); // Ensure midnight for consistency
      base.setDate(base.getDate() + dayOffset);
      const year = base.getFullYear();
      const month = String(base.getMonth() + 1).padStart(2, "0");
      const day = String(base.getDate()).padStart(2, "0");
      fetch(`/api/v1/meteocat/episodis-oberts?year=${year}&month=${month}&day=${day}`)
        .then(async res => {
          if (!res.ok) {
            const text = await res.text();
            throw new Error(`HTTP ${res.status}: ${text}`);
          }
          return res.json();
        })
        .then(res => {
          setData(res);
          const allPeriods = new Set<string>();
          res.forEach((ep: EpisodiObert) =>
            (ep.avisos || []).forEach(av =>
              (av.evolucions || []).forEach(ev =>
                (ev.periodes || []).forEach(p => allPeriods.add(p.nom))
              )
            )
          );
          setPeriods(Array.from(allPeriods));
          setSelectedPeriod(Array.from(allPeriods)[0] || null);
        })
        .catch(err => {
          setData([]);
          setPeriods([]);
          setSelectedPeriod(null);
          console.error("Failed to fetch episodi oberts:", err);
        });
    }, [dayOffset]);

  const affected = data && selectedPeriod
    ? getAffectedComarques(data, selectedPeriod)
    : [];

  function style(feature) {
    const code = Number(feature.properties.code);
    const found = affected.find(a => a.idComarca === code);
    if (found) {
      const colors = ["#ffffb2", "#fecc5c", "#fd8d3c", "#f03b20", "#bd0026"];
      return {
        fillColor: colors[found.perill] || "#f03b20",
        weight: 2,
        opacity: 1,
        color: "#000000ff",
        fillOpacity: 0.7,
      };
    }
    return {
      fillColor: "#eee",
      weight: 1,
      opacity: 0.5,
      color: "#888",
      fillOpacity: 0.2,
    };
  }

  function onEachFeature(feature, layer) {
    const code = Number(feature.properties.code);
    const affectedInfo = affected.filter(a => a.idComarca === code);

    let tooltipContent = `<strong>${feature.properties.name}</strong>`;
    if (affectedInfo.length > 0) {
        tooltipContent += "<br/>";
        tooltipContent += affectedInfo.map(a =>
        `Perill: ${a.perill}, Nivell: ${a.nivell}${a.llindar ? `, Llindar: ${a.llindar}` : ""}`
        ).join("<br/>");
    } else {
        tooltipContent += "<br/>No warnings for this period.";
    }

    layer.bindTooltip(tooltipContent, { direction: "top", sticky: true });
  }

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2 }}>Episodis Oberts Map</Typography>
      <Stack direction="row" spacing={2} sx={{ mb: 2 }}>
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
      <Stack direction="row" spacing={2} alignItems="center" sx={{ mb: 2 }}>
        {periods.map(p => (
          <Button
            key={p}
            variant={selectedPeriod === p ? "contained" : "outlined"}
            onClick={() => setSelectedPeriod(p)}
          >
            {p}
          </Button>
        ))}
        {/* Danger Level Legend */}
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, ml: 4 }}>
          <Typography variant="subtitle2" sx={{ mr: 1 }}>Danger Level:</Typography>
          <Box sx={{ bgcolor: "#ffffb2", width: 24, height: 16, border: "1px solid #888" }} /> <span>1</span>
          <Box sx={{ bgcolor: "#fecc5c", width: 24, height: 16, border: "1px solid #888" }} /> <span>2</span>
          <Box sx={{ bgcolor: "#fd8d3c", width: 24, height: 16, border: "1px solid #888" }} /> <span>3</span>
          <Box sx={{ bgcolor: "#f03b20", width: 24, height: 16, border: "1px solid #888" }} /> <span>4</span>
          <Box sx={{ bgcolor: "#bd0026", width: 24, height: 16, border: "1px solid #888" }} /> <span>5</span>
        </Box>
      </Stack>
      <MapContainer center={[41.8, 1.5]} zoom={8} style={{ height: "600px", width: "100%" }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {comarcasGeoJson && (
            <GeoJSON
                key={dayOffset + '-' + selectedPeriod + '-' + JSON.stringify(affected.map(a => a.idComarca))}
                data={comarcasGeoJson}
                style={style}
                onEachFeature={onEachFeature}
            />
        )}
      </MapContainer>
      {/* Footer with Servei Meteorològic de Catalunya logo */}
            <Box
              sx={{
                position: "fixed",
                bottom: 0,
                left: 0,
                width: "100%",
                bgcolor: "white",
                py: 1,
                boxShadow: 2,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 1300,
              }}
            >
              <img
                src="https://external-content.duckduckgo.com/iu/?u=https%3A%2F%2Ftse1.mm.bing.net%2Fth%2Fid%2FOIP.7CD-xJdTQEq2L_FOoo6puQHaB1%3Fpid%3DApi&f=1&ipt=1087bf38f2747e410daeaa02fbcf88325c11716b0a6f223924786151b4cdb244&ipo=images"
                alt="Servei Meteorològic de Catalunya"
                style={{ height: 32, marginRight: 12 }}
              />
            </Box>
    </Box>
  );
}