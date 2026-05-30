import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export default function RegisterPage() {
  const nav = useNavigate();
  const { login } = useAuth();

  const [registered, setRegistered] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_BASE_URL || ""}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      let data: any = {};
      try {
        data = await res.json();
      } catch {
        // If response is not JSON, fallback to text
        data = { detail: await res.text() };
      }
      if (!res.ok) {
        // Try to extract a user-friendly error message
        let message = "Registration failed";
        if (typeof data.detail === "string") {
          message = data.detail.replace(/^Value error,?\s*/i, "");
        } else if (Array.isArray(data.detail) && data.detail.length > 0 && data.detail[0].msg) {
          message = data.detail[0].msg.replace(/^Value error,?\s*/i, "");
        }
        throw new Error(message);
      }
      setRegistered(true);
    } catch (e: any) {
      setErr(e?.message ?? "Register failed");
    } finally {
      setBusy(false);
    }
  }

  if (registered) return <div style={{ padding: 16 }}>Registration successful! Check your email to verify your account before logging in.</div>;

  return (
    <div style={{ padding: 16, maxWidth: 420 }}>
      <h2>Register</h2>
      <form onSubmit={onSubmit} style={{ display: "grid", gap: 10 }}>
        <label>
          Email
          <input value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: "100%" }} />
        </label>
        <label>
          Password
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} style={{ width: "100%" }} />
        </label>
        <button disabled={busy}>{busy ? "Creating…" : "Create account"}</button>
      </form>

      {err && <div style={{ marginTop: 10, color: "crimson" }}>{err}</div>}

      <div style={{ marginTop: 12 }}>
        Already have an account? <Link to="/login">Login</Link>
      </div>
    </div>
  );
}