import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './auth/AuthContext';
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
import SuggestActivityPage from './components/SuggestActivityPage';
import AllActivitiesPage from './components/AllActivitiesPage';
import ManageCategoriesPage from './components/ManageCategoriesPage';
import LandingPage from './components/LandingPage';
import UserProfilePage from './components/UserProfilePage';
import UserManagementPage from './components/UserManagementPage';
import VerifyEmailPage from "./components/EmailVerification";
import RequestPasswordResetPage from "./components/PasswordResetRequest";
import ResetPasswordPage from "./components/PasswordReset";


function AppRoutes() {
  const { user } = useAuth();
  const location = useLocation();

  // If user is logged in and on landing, login, or register, redirect to home
  if (user && (location.pathname === "/" || location.pathname === "/login" || location.pathname === "/register")) {
    return <Navigate to="/home" replace />;
  }

  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />

        <Route path="/home" element={
          <ProtectedRoute>
            <RecommenderHome />
          </ProtectedRoute>
        } />

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
        <Route path="/episodis-oberts" element={<EpisodisOberts />} />
        <Route path="/suggest-activity" element={<SuggestActivityPage />} />
        <Route path="/activities" element={<AllActivitiesPage />} />
        <Route path="/manage-categories" element={<ManageCategoriesPage />} />
        <Route path="/profile" element={<UserProfilePage />} />
        <Route path="/user-management" element={
          <ProtectedRoute requireRole="admin">
            <UserManagementPage />
          </ProtectedRoute>
        } />
        <Route path="/verify-email" element={<VerifyEmailPage />} />
        <Route path="/request-password-reset" element={<RequestPasswordResetPage />} />
        <Route path="/reset-password" element={<ResetPasswordPage />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </AuthProvider>
  );
}