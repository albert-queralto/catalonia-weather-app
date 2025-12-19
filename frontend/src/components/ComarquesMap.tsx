import { MapContainer, TileLayer, GeoJSON } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useEffect, useState } from 'react';
import L from 'leaflet';

export default function ComarquesMap() {
  const [geojson, setGeojson] = useState(null);

  useEffect(() => {
    fetch('/api/v1/comarcas/geojson')
      .then(res => res.json())
      .then(setGeojson);
  }, []);

  const comarcaStyle = {
    color: 'black',
    weight: 1,
    fill: true,
    fillOpacity: 0,
  };

  // Bind tooltip with comarca name on hover
  function onEachFeature(feature: any, layer: L.Layer) {
    if (feature.properties && feature.properties.name) {
      layer.bindTooltip(feature.properties.name, {
        direction: 'top',
        sticky: true,
        className: 'comarca-tooltip',
      });
    }
  }

  return (
    <MapContainer center={[41.8, 1.5]} zoom={8} style={{ height: '600px', width: '100%' }}>
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; OpenStreetMap contributors"
      />
      {geojson && (
        <GeoJSON data={geojson} style={comarcaStyle} onEachFeature={onEachFeature} />
      )}
    </MapContainer>
  );
}