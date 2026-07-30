import React, { createContext, useContext, useState, useMemo, useEffect } from "react";
import { API_BASE } from "../api/client";
import type { Me } from "../api/types";

type User = Me;

type AuthState = {
  token: string | null;
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  updateUser: (user: User) => void;
};

const AuthContext = createContext<AuthState | null>(null);

const LS_TOKEN = "token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(LS_TOKEN));
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => Boolean(localStorage.getItem(LS_TOKEN)));

  // Fetch user info if token changes
  useEffect(() => {
    let active = true;

    async function fetchUser() {
      if (!token) {
        console.log("No token found, user is not authenticated.");
        if (active) {
          setUser(null);
          setLoading(false);
        }
        return;
      }

      setLoading(true);

      try {
        const res = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${token}` }
        });

        if (!active) return;

        if (res.ok) {
          setUser(await res.json());
        } else {
          setUser(null);
          localStorage.removeItem(LS_TOKEN);
          setToken(null);
        }
      } finally {
        if (active) setLoading(false);
      }
    }
    fetchUser();

    return () => {
      active = false;
    };
  }, [token]);

  async function login(email: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ username: email, password }),
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "Login failed");
    }
    const data = await res.json();
    setToken(data.access_token);
    localStorage.setItem(LS_TOKEN, data.access_token);
    // Fetch user info after login
    const meRes = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${data.access_token}` }
    });
    if (meRes.ok) {
      setUser(await meRes.json());
    } else {
      setUser(null);
    }
  }

  function logout() {
    setToken(null);
    setUser(null);
    setLoading(false);
    localStorage.removeItem(LS_TOKEN);
  }

  function updateUser(nextUser: User) {
    setUser(nextUser);
  }

  const value = useMemo<AuthState>(() => ({
    token,
    user,
    loading,
    login,
    logout,
    updateUser,
  }), [token, user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
