import { 
  MapContainer, 
  TileLayer, 
  GeoJSON, 
  Marker, 
  Popup, 
  useMap 
} from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect, useState, useRef } from 'react';
import L from 'leaflet';
import {
  Modal,
  Box,
  Typography,
  Select,
  MenuItem,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Drawer,
  IconButton,
  List,
  ListItem,
  ListItemText,
  Divider
} from '@mui/material';
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  Tooltip, 
  CartesianGrid, 
  ResponsiveContainer 
} from 'recharts';
import MenuIcon from '@mui/icons-material/Menu';
import CloseIcon from '@mui/icons-material/Close';

// Helper component to center the map when requested
function CenterMapToStation({ station }: { station: any }) {
  const map = useMap();
  useEffect(() => {
    if (station) {
      map.setView([station.latitud, station.longitud], 12, { animate: true });
    }
  }, [station, map]);
  return null;
}

export default function ComarquesMap() {
  const [geojson, setGeojson] = useState(null);
  const [stations, setStations] = useState<any[]>([]);
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedStation, setSelectedStation] = useState<any>(null);
  const [variables, setVariables] = useState<any[]>([]);
  const [selectedVariable, setSelectedVariable] = useState<string>('');
  const [date, setDate] = useState('');
  const [variableData, setVariableData] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [stationVariables, setStationVariables] = useState<{ [codi: string]: any[] }>({});
  const [stationToCenter, setStationToCenter] = useState<any>(null);

  const mapRef = useRef<any>(null);

  useEffect(() => {
    fetch('/api/v1/comarcas/geojson')
      .then(res => res.json())
      .then(setGeojson);

    fetch('/api/v1/meteocat/stations')
      .then(res => res.json())
      .then(async stationsData => {
        setStations(stationsData);
        // Fetch variables for each station
        const vars: { [codi: string]: any[] } = {};
        await Promise.all(
          stationsData.map(async (station: any) => {
            const res = await fetch(`/api/v1/meteocat/station/${station.codi}/variables`);
            const data = await res.json();
            vars[station.codi] = data;
          })
        );
        setStationVariables(vars);
      });
  }, []);

  const comarcaStyle = {
    color: 'black',
    weight: 1,
    fill: true,
    fillOpacity: 0,
  };

  function onEachFeature(feature: any, layer: L.Layer) {
    if (feature.properties && feature.properties.name) {
      layer.bindTooltip(feature.properties.name, {
        direction: 'top',
        sticky: true,
        className: 'comarca-tooltip',
      });
    }
  }

  const stationIcon = new L.Icon({
    iconUrl: 'https://aplicacions.aca.gencat.cat/sentilo-catalog-web/static/img/icons/pluviometres-poi.png',
    iconSize: [25, 27],
    iconAnchor: [12, 27],
    popupAnchor: [1, -34],
  });

  // Open modal and fetch available variables for the station
  const handleMarkerClick = async (station: any) => {
    setSelectedStation(station);
    setModalOpen(true);
    setVariableData([]);
    setSelectedVariable('');
    setDate('');
    // Fetch variables metadata for this station
    const res = await fetch(`/api/v1/meteocat/station/${station.codi}/variables`);
    const data = await res.json();
    setVariables(data);
  };

  // Fetch variable values for the selected variable and date range
  const handleFetchVariableData = async () => {
    if (!selectedStation || !selectedVariable || !dateFrom || !dateTo) return;
    setLoading(true);
    const params = new URLSearchParams({
      date_from: dateFrom,
      date_to: dateTo,
    });
    const res = await fetch(
      `/api/v1/meteocat/station/${selectedStation.codi}/variable/${selectedVariable}/values?${params.toString()}`
    );
    const data = await res.json();
    setVariableData(data);
    setLoading(false);
  };

  // Center map to station (just set state)
  const handleCenterStation = (station: any) => {
    setSidebarOpen(false);
    setStationToCenter(station);
  };

  return (
    <>
      {/* Sidebar toggle button */}
      <IconButton
        onClick={() => setSidebarOpen(true)}
        sx={{ position: 'absolute', top: 16, left: 16, zIndex: 1200, bgcolor: 'white' }}
        size="large"
      >
        <MenuIcon />
      </IconButton>
      {/* Sidebar Drawer */}
      <Drawer anchor="left" open={sidebarOpen} onClose={() => setSidebarOpen(false)}>
        <Box sx={{ width: 320, p: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>Stations</Typography>
            <IconButton onClick={() => setSidebarOpen(false)}><CloseIcon /></IconButton>
          </Box>
          <Divider />
          <List>
            {stations.map(station => (
              <Box key={station.codi}>
                <ListItem
                  secondaryAction={
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => handleCenterStation(station)}
                    >
                      Center
                    </Button>
                  }
                >
                  <ListItemText
                    primary={station.nom}
                    secondary={`Code: ${station.codi}`}
                  />
                </ListItem>
                <Divider />
              </Box>
            ))}
          </List>
        </Box>
      </Drawer>
      <MapContainer
        center={[41.8, 1.5]}
        zoom={8}
        style={{ height: '600px', width: '100%' }}
      >
        {/* This will center the map when stationToCenter changes */}
        <CenterMapToStation station={stationToCenter} />
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />
        {geojson && (
          <GeoJSON data={geojson} style={comarcaStyle} onEachFeature={onEachFeature} />
        )}
        {stations.map(station => (
          <Marker
            key={station.codi}
            position={[station.latitud, station.longitud]}
            icon={stationIcon}
            eventHandlers={{
              click: () => handleMarkerClick(station),
            }}
          >
            <Popup>
              <strong>{station.nom}</strong><br />
              {station.emplacament}<br />
              {station.comarca?.nom}, {station.provincia?.nom}<br />
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      <Modal open={modalOpen} onClose={() => setModalOpen(false)}>
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            bgcolor: 'background.paper',
            boxShadow: 24,
            p: 4,
            minWidth: variableData.length > 0 ? 600 : 350,
            maxWidth: variableData.length > 0 ? 900 : 600,
            minHeight: variableData.length > 0 ? 500 : 'auto',
            maxHeight: '90vh',
            overflowY: 'auto',
          }}
        >
          <Typography variant="h6" gutterBottom>
            {selectedStation?.nom} - Variables
          </Typography>
          {variables.length === 0 ? (
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              No variables were found
            </Typography>
          ) : (
            <>
              <FormControl fullWidth sx={{ mb: 2 }}>
                <InputLabel id="variable-select-label">Variable</InputLabel>
                <Select
                  labelId="variable-select-label"
                  value={selectedVariable}
                  label="Variable"
                  onChange={e => setSelectedVariable(e.target.value)}
                >
                  {variables.map(v => (
                    <MenuItem key={v.codi} value={v.codi}>
                      {v.nom} ({v.unitat})
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <Box sx={{ display: 'flex', gap: 2, mb: 2 }}>
                <TextField
                  label="From"
                  type="date"
                  InputLabelProps={{ shrink: true }}
                  value={dateFrom}
                  onChange={e => setDateFrom(e.target.value)}
                  fullWidth
                />
                <TextField
                  label="To"
                  type="date"
                  InputLabelProps={{ shrink: true }}
                  value={dateTo}
                  onChange={e => setDateTo(e.target.value)}
                  fullWidth
                />
              </Box>
              <Button
                variant="contained"
                onClick={handleFetchVariableData}
                disabled={!selectedVariable || !dateFrom || !dateTo || loading}
                fullWidth
              >
                {loading ? "Loading..." : "Show Data"}
              </Button>
              {variableData.length > 0 && (
                <Box sx={{ mt: 3 }}>
                  <Typography variant="subtitle1">Results:</Typography>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={variableData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="data"
                        tickFormatter={d => d ? new Date(d).toLocaleString('es-ES', { hour12: false }) : ''}
                        minTickGap={20}
                      />
                      <YAxis />
                      <Tooltip
                        labelFormatter={d => d ? new Date(d).toLocaleString('es-ES', { hour12: false }) : ''}
                      />
                      <Line type="monotone" dataKey="valor" stroke="#1976d2" dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </Box>
              )}
            </>
          )}
        </Box>
      </Modal>
    </>
  );
}