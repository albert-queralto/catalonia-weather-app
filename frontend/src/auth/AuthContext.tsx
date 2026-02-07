import React, { createContext, useContext, useState, useMemo, useEffect } from "react";

type User = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
};

type AuthState = {
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

const LS_TOKEN = "token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(LS_TOKEN));
  const [user, setUser] = useState<User | null>(null);

  // Fetch user info if token changes
  useEffect(() => {
    async function fetchUser() {
      if (!token) {
        console.log("No token found, user is not authenticated.");
        setUser(null);
        return;
      }
      console.log("Sending token in Authorization header:", token);
      const res = await fetch(`${API_BASE_URL}/auth/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      console.log("Response status for /auth/me:", res.status);
      if (res.ok) {
        setUser(await res.json());
      } else {
        setUser(null);
        localStorage.removeItem(LS_TOKEN);
        setToken(null);
      }
    }
    fetchUser();
  }, [token]);

  async function login(email: string, password: string) {
    const res = await fetch(`${API_BASE_URL}/auth/token`, {
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
    const meRes = await fetch(`${API_BASE_URL}/auth/me`, {
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
    localStorage.removeItem(LS_TOKEN);
  }

  const value = useMemo<AuthState>(() => ({
    token,
    user,
    login,
    logout,
  }), [token, user]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}