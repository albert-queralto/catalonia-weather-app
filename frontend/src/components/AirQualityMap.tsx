import { MapContainer, TileLayer, CircleMarker, Popup, GeoJSON, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect, useState } from 'react';
import { Box, Modal, Typography, Radio, RadioGroup, FormControlLabel, FormGroup, Button } from '@mui/material';
import { LineChart, Line, XAxis, YAxis, Tooltip as RechartsTooltip, CartesianGrid, ResponsiveContainer, ReferenceLine } from 'recharts';

// List of air quality parameters
const AIR_QUALITY_PARAMS = [
  { key: 'pm2_5', label: 'PM2.5' },
  { key: 'pm10', label: 'PM10' },
  { key: 'carbon_monoxide', label: 'CO' },
  { key: 'carbon_dioxide', label: 'CO₂' },
  { key: 'nitrogen_dioxide', label: 'NO₂' },
  { key: 'sulphur_dioxide', label: 'SO₂' },
  { key: 'ozone', label: 'O₃' },
  { key: 'uv_index', label: 'UV Index' },
];

const COLOR_BANDS: Record<string, {breaks: number[], colors: string[]}> = {
  pm2_5: {
    breaks: [0, 10, 20, 25, 50, 75, 800],
    colors: ['#009966', '#99cc00', '#ffde33', '#ff9933', '#cc0033', '#660099'],
  },
  pm10: {
    breaks: [0, 20, 40, 50, 100, 150, 1200],
    colors: ['#009966', '#99cc00', '#ffde33', '#ff9933', '#cc0033', '#660099'],
  },
  nitrogen_dioxide: {
    breaks: [0, 40, 90, 120, 230, 340, 1000],
    colors: ['#009966', '#99cc00', '#ffde33', '#ff9933', '#cc0033', '#660099'],
  },
  ozone: {
    breaks: [0, 50, 100, 130, 240, 380, 800],
    colors: ['#009966', '#99cc00', '#ffde33', '#ff9933', '#cc0033', '#660099'],
  },
  sulphur_dioxide: {
    breaks: [0, 100, 200, 350, 500, 750, 1250],
    colors: ['#009966', '#99cc00', '#ffde33', '#ff9933', '#cc0033', '#660099'],
  },
  carbon_monoxide: {
    breaks: [0, 100, 200, 350, 500, 750, 1250],
    colors: ['#009966', '#99cc00', '#ffde33', '#ff9933', '#cc0033', '#660099'],
  },
  carbon_dioxide: {
    breaks: [350, 375, 400, 425, 450, 475, 500],
    colors: ['#009966', '#99cc00', '#ffde33', '#ff9933', '#cc0033', '#660099'],
  },
  // fallback for others
  default: {
    breaks: [0, 10, 20, 30, 40, 50, 1000],
    colors: ['#009966', '#99cc00', '#ffde33', '#ff9933', '#cc0033', '#660099'],
  }
};

function formatValue(val: any) {
  if (val == null || isNaN(val)) return 'N/A';
  return Number(val).toFixed(1);
}

function Legend({ param }: { param: string }) {
  const band = COLOR_BANDS[param] || COLOR_BANDS.default;
  return (
    <Box sx={{
      display: 'flex',
      alignItems: 'center',
      gap: 1,
      bgcolor: 'white',
      border: '1px solid #ccc',
      borderRadius: 1,
      p: 1,
      mb: 2,
      width: 'fit-content',
      boxShadow: 2,
    }}>
      {band.colors.map((color, i) => (
        <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Box sx={{
            width: 24, height: 16, bgcolor: color, border: '1px solid #888', mr: 0.5
          }} />
          <Typography variant="caption">
            {band.breaks[i]}{i < band.breaks.length - 2 ? '–' + (band.breaks[i + 1] - 1) : '+'}
          </Typography>
          {i < band.colors.length - 1 && <span style={{ margin: '0 4px' }}>|</span>}
        </Box>
      ))}
    </Box>
  );
}

export default function AirQualityMap() {
  const [selectedParam, setSelectedParam] = useState('pm2_5');
  const [stations, setStations] = useState<any[]>([]);
  const [airQualityPoints, setAirQualityPoints] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [modalData, setModalData] = useState<any[]>([]);
  const [modalLocation, setModalLocation] = useState<{lat: number, lon: number} | null>(null);
  const [comarcasGeoJson, setComarcasGeoJson] = useState<any>(null);

  useEffect(() => {
    fetch('/api/v1/comarcas/geojson')
      .then(res => res.json())
      .then(setComarcasGeoJson);
  }, []);

  // Fetch stations on mount
  useEffect(() => {
    fetch('/api/v1/meteocat/stations')
      .then(res => res.json())
      .then(setStations);
  }, []);

  // Fetch air quality for all stations
  useEffect(() => {
    if (stations.length === 0) return;
    Promise.all(
      stations.map(async (st) => {
        const res = await fetch(`/api/v1/air-quality?lat=${st.latitud}&lon=${st.longitud}`);
        const data = await res.json();
        return { ...st, ...data.observations?.[0] };
      })
    ).then(setAirQualityPoints);
  }, [stations]);

  // Color scale for colormap
  function getColor(value: number | null | undefined, param: string) {
    if (value == null) return '#ccc';
    const band = COLOR_BANDS[param] || COLOR_BANDS.default;
    for (let i = 0; i < band.breaks.length - 1; i++) {
        if (value >= band.breaks[i] && value < band.breaks[i + 1]) {
        return band.colors[i];
        }
    }
    return band.colors[band.colors.length - 1];
  }

  function comarcaStyle() {
    return {
      fillColor: "transparent",
      weight: 2,
      opacity: 1,
      color: "#333",
      fillOpacity: 0,
    };
  }

  // Handle marker click: fetch hourly data for that point
  const handleMarkerClick = async (pt: any) => {
    const res = await fetch(`/api/v1/air-quality/hourly?lat=${pt.latitud}&lon=${pt.longitud}`);
    let data = await res.json();
    if (!Array.isArray(data)) {
        data = [];
    }
    setModalData(data);
    setModalLocation({ lat: pt.latitud, lon: pt.longitud, name: pt.nom });
    setModalOpen(true);
  };

  // Find the closest time in modalData to now
  const now = new Date();
  let currentTimeISO: string | undefined = undefined;
  if (modalData && modalData.length > 0) {
    // modalData[i].time is assumed to be ISO string
    const closest = modalData.reduce((a, b) =>
      Math.abs(new Date(a.time).getTime() - now.getTime()) <
      Math.abs(new Date(b.time).getTime() - now.getTime()) ? a : b
    );
    currentTimeISO = closest.time;
  }

  return (
    <Box>
      <RadioGroup
        row
        value={selectedParam}
        onChange={(_, value) => setSelectedParam(value)}
        sx={{ mb: 2 }}
        >
        {AIR_QUALITY_PARAMS.map(param => (
            <FormControlLabel
            key={param.key}
            value={param.key}
            control={<Radio />}
            label={param.label}
            />
        ))}
      </RadioGroup>
      <Legend param={selectedParam} />
      <MapContainer center={[41.8, 1.5]} zoom={8} style={{ height: '600px', width: '100%' }}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />
        {comarcasGeoJson && (
          <GeoJSON data={comarcasGeoJson} style={comarcaStyle} />
        )}
        {airQualityPoints.map((pt, idx) => (
          <CircleMarker
            key={`${pt.id || idx}-${selectedParam}`}
            center={[pt.latitud, pt.longitud]}
            radius={16}
            fillOpacity={0.7}
            color={getColor(pt[selectedParam], selectedParam)}
            eventHandlers={{
              click: () => handleMarkerClick(pt),
            }}
          >
            <Tooltip direction="top" offset={[0, -10]} opacity={1} permanent={false}>
              <strong>{pt.nom}</strong><br />
              <strong>{AIR_QUALITY_PARAMS.find(p => p.key === selectedParam)?.label}:</strong> {formatValue(pt[selectedParam])}
            </Tooltip>
            <Popup>
              <strong>{pt.nom}</strong><br />
              <strong>{AIR_QUALITY_PARAMS.find(p => p.key === selectedParam)?.label}:</strong> {formatValue(pt[selectedParam])}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
      <Modal open={modalOpen} onClose={() => setModalOpen(false)}>
        <Box sx={{
          position: 'absolute', top: '50%', left: '50%',
          transform: 'translate(-50%, -50%)', bgcolor: 'background.paper',
          boxShadow: 24, p: 4, minWidth: 600, maxWidth: 900, maxHeight: '90vh', overflowY: 'auto'
        }}>
          <Typography variant="h6" gutterBottom>
            Hourly {AIR_QUALITY_PARAMS.find(p => p.key === selectedParam)?.label} at {modalLocation?.name} ({modalLocation?.lat}, {modalLocation?.lon})
          </Typography>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={modalData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="time" tickFormatter={d => d ? new Date(d).toLocaleString('es-ES', { hour12: false }) : ''} />
                <YAxis />
                <RechartsTooltip 
                  labelFormatter={d => d ? new Date(d).toLocaleString('es-ES', { hour12: false }) : ''} 
                  formatter={(value) => [formatValue(value), AIR_QUALITY_PARAMS.find(p => p.key === selectedParam)?.label]}
                />
                <Line type="monotone" dataKey={selectedParam} stroke="#1976d2" dot={false} />
                {currentTimeISO && (
                <ReferenceLine
                    x={currentTimeISO}
                    stroke="red"
                    strokeDasharray="3 3"
                    label={{ value: 'Now', position: 'top', fill: 'red', fontSize: 12 }}
                />
                )}
            </LineChart>
          </ResponsiveContainer>
          <Box sx={{ mt: 2, textAlign: 'right' }}>
            <Button onClick={() => setModalOpen(false)}>Close</Button>
          </Box>
        </Box>
      </Modal>
    </Box>
  );
}