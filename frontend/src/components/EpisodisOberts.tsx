import { useEffect, useState } from "react";
import { MapContainer, TileLayer, GeoJSON } from "react-leaflet";
import { Box, Button, Typography, Paper, Stack } from "@mui/material";
import "leaflet/dist/leaflet.css";
import { EpisodiObert } from "../api/types";


function getAffectedComarques(avisos, periodNom) {
  // Returns array of { idComarca, perill, nivell }
  const affected = [];
  avisos.forEach(aviso =>
    aviso.evolucions.forEach(evol =>
      evol.periodes.forEach(period => {
        if (period.nom === periodNom && period.afectacions) {
          affected.push(...period.afectacions.map(a => ({
            idComarca: a.idComarca,
            perill: a.perill,
            nivell: a.nivell,
            llindar: a.llindar
          })));
        }
      })
    )
  );
  return affected;
}

export default function EpisodisObertsMap() {
  const [date, setDate] = useState(new Date());
  const [data, setData] = useState<EpisodiObert[] | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<string | null>(null);
  const [periods, setPeriods] = useState<string[]>([]);
  const [comarcasGeoJson, setComarcasGeoJson] = useState<any>(null);

  useEffect(() => {
    fetch("/api/v1/comarcas/geojson")
      .then(res => res.json())
      .then(setComarcasGeoJson);
  }, []);

  useEffect(() => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");
    fetch(`/api/v1/meteocat/episodis-oberts?year=${year}&month=${month}&day=${day}`)
      .then(res => res.json())
      .then(res => {
        setData(res);
        // Collect all unique periods for the day
        const allPeriods = new Set<string>();
        res.forEach((ep: EpisodiObert) =>
          ep.avisos.forEach(av =>
            av.evolucions.forEach(ev =>
              ev.periodes.forEach(p => allPeriods.add(p.nom))
            )
          )
        );
        setPeriods(Array.from(allPeriods));
        setSelectedPeriod(Array.from(allPeriods)[0] || null);
      });
  }, [date]);

  // Map idComarca to GeoJSON feature
  const comarcaFeatures = comarcasGeoJson?.features || [];
  const comarcaMap = Object.fromEntries(
    comarcaFeatures.map(f => [f.properties.code, f])
  );

  // Get affected comarques for selected period
  const affected = data && selectedPeriod
    ? getAffectedComarques(data.flatMap(ep => ep.avisos), selectedPeriod)
    : [];

  // Style function for GeoJSON
  function style(feature) {
    const code = Number(feature.properties.code);
    const found = affected.find(a => a.idComarca === code);
    if (found) {
      // Color by perill (danger level)
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
    // Find affected info for this comarca
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
        {periods.map(p => (
          <Button
            key={p}
            variant={selectedPeriod === p ? "contained" : "outlined"}
            onClick={() => setSelectedPeriod(p)}
          >
            {p}
          </Button>
        ))}
      </Stack>
      <MapContainer center={[41.8, 1.5]} zoom={8} style={{ height: "600px", width: "100%" }}>
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        {comarcasGeoJson && (
            <GeoJSON
                key={selectedPeriod + JSON.stringify(affected.map(a => a.idComarca))}
                data={comarcasGeoJson}
                style={style}
                onEachFeature={onEachFeature}
            />
        )}
      </MapContainer>
      <Paper sx={{ mt: 2, p: 2 }}>
        <Typography variant="subtitle1">Legend: Danger Level (Perill)</Typography>
        <Box sx={{ display: "flex", gap: 2 }}>
          <Box sx={{ bgcolor: "#ffffb2", width: 24, height: 16, border: "1px solid #888" }} /> <span>1</span>
          <Box sx={{ bgcolor: "#fecc5c", width: 24, height: 16, border: "1px solid #888" }} /> <span>2</span>
          <Box sx={{ bgcolor: "#fd8d3c", width: 24, height: 16, border: "1px solid #888" }} /> <span>3</span>
          <Box sx={{ bgcolor: "#f03b20", width: 24, height: 16, border: "1px solid #888" }} /> <span>4</span>
          <Box sx={{ bgcolor: "#bd0026", width: 24, height: 16, border: "1px solid #888" }} /> <span>5</span>
        </Box>
      </Paper>
    </Box>
  );
}