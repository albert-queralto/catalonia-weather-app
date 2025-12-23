import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import ProtectedRoute from './auth/ProtectedRoute';

import Navbar from './components/Navbar';
import PopulatePage from './components/PopulatePage';
import MLModelTrainer from './components/MLModelTrainer';

import ComarquesMap from './components/ComarquesMap';
import AirQualityMap from './components/AirQualityMap';
import EpisodisOberts from './components/EpisodisOberts';

import LoginPage from './components/LoginPage';
import RegisterPage from './components/RegisterPage';
import RecommenderHome from './components/RecommenderHome';

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Navbar />
        <Routes>
          <Route path="/" element={
            <ProtectedRoute>
              <RecommenderHome />
            </ProtectedRoute>
          } />

          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />

          <Route path="/populate" element={
            <ProtectedRoute requireRole="admin">
              <PopulatePage />
            </ProtectedRoute>
          } />

          <Route path="/ml-model-trainer" element={
            <ProtectedRoute requireRole="admin">
              <MLModelTrainer />
            </ProtectedRoute>
          } />

          <Route path="/historical" element={<ComarquesMap />} />
          <Route path="/air-quality-map" element={<AirQualityMap />} />
          <Route path="/episodis-oberts" element={<EpisodisOberts date={new Date()} />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}
