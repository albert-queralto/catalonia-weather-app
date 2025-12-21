import { useEffect, useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import { Box, Typography, CircularProgress } from "@mui/material";
import "leaflet/dist/leaflet.css";
import L from "leaflet";

const pluviometerIcon = new L.Icon({
  iconUrl: "https://aplicacions.aca.gencat.cat/sentilo-catalog-web/static/img/icons/pluviometres-poi.png",
  iconSize: [32, 32],
  iconAnchor: [16, 32],
  popupAnchor: [0, -32],
});

export default function AcaPluviometersMap() {
  const [sensors, setSensors] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [pluviometerData, setPluviometerData] = useState<any[]>([]);
  const [dataLoading, setDataLoading] = useState(true);

  // Fetch sensor catalog
  useEffect(() => {
    fetch("/api/v1/aca/pluviometers")
      .then(res => res.json())
      .then(data => {
        const allSensors = (data.providers || []).flatMap((prov: any) => prov.sensors || []);
        setSensors(allSensors);
        setLoading(false);
      });
  }, []);

  // Fetch all pluviometer data once
  useEffect(() => {
    setDataLoading(true);
    fetch("/api/v1/aca/pluviometer_data")
      .then(res => res.json())
      .then(data => {
        setPluviometerData(data.sensors || []);
        setDataLoading(false);
      });
  }, []);

  return (
    <Box sx={{ p: 2 }}>
      <Typography variant="h6" gutterBottom>ACA Pluviometers</Typography>
      {loading || dataLoading ? (
        <CircularProgress />
      ) : (
        <MapContainer center={[41.8, 1.5]} zoom={8} style={{ height: "600px", width: "100%" }}>
          <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {sensors.map(sensor => {
            const [lat, lon] = sensor.location.split(" ").map(Number);
            // Find the latest observation for this sensor
            const sensorData = pluviometerData.find((s: any) => s.sensor === sensor.sensor);
            const lastObs = sensorData?.observations?.[0];
            return (
              <Marker key={sensor.sensor} position={[lat, lon]} icon={pluviometerIcon}>
                <Popup>
                  <strong>{sensor.componentDesc}</strong><br />
                  {sensor.description}<br />
                  <em>{sensor.sensor}</em><br />
                  {lastObs
                    ? <span>Last value: {lastObs.value} mm/h</span>
                    : <span>No recent data</span>
                  }
                </Popup>
              </Marker>
            );
          })}
        </MapContainer>
      )}
    </Box>
  );
}