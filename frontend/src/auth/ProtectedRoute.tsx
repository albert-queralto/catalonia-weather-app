import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import type { Role } from "../api/types";

export default function ProtectedRoute({
  children,
  requireRole
}: {
  children: React.ReactNode;
  requireRole?: Role;
}) {
  const { user, loading } = useAuth();

  if (loading) return <div style={{ padding: 16 }}>Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;

  if (requireRole && user.role !== requireRole) {
    return <div style={{ padding: 16 }}>403 – Insufficient permissions.</div>;
  }
  return <>{children}</>;
}
