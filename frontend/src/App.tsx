import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import PopulatePage from './components/PopulatePage';
import ComarquesMap from './components/ComarquesMap';
import AirQualityMap from './components/AirQualityMap';
import EpisodisOberts from './components/EpisodisOberts';
import MLModelTrainer from './components/MLModelTrainer';

export default function App() {
  return (
    <Router>
      <Navbar />
      <Routes>
        <Route path="/populate" element={<PopulatePage />} />
        <Route path="/historical" element={<ComarquesMap />} />
        <Route path="/air-quality-map" element={<AirQualityMap />} />
        <Route path="/episodis-oberts" element={<EpisodisOberts date={new Date()} />} />
        <Route path="/ml-model-trainer" element={<MLModelTrainer />} />
      </Routes>
    </Router>
  );
}