import React, { createContext, useContext, useState, useMemo, useEffect } from "react";

type User = {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
};

type AuthState = {
  token: string | null;
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

const LS_TOKEN = "token";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(LS_TOKEN));
  const [user, setUser] = useState<User | null>(null);

  // Fetch user info if token changes
  useEffect(() => {
    async function fetchUser() {
      if (!token) {
        setUser(null);
        return;
      }
      const res = await fetch("/api/v1/auth/me", {
        headers: { Authorization: `Bearer ${token}` }
      });
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
    const res = await fetch("/api/v1/auth/token", {
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
    const meRes = await fetch("/api/v1/auth/me", {
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