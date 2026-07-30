import React, { useState } from "react";
import PersonAddAltIcon from "@mui/icons-material/PersonAddAlt";
import { Button } from "@mui/material";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

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

  if (registered) {
    return (
      <div className="auth-success">
        <section className="auth-success__panel">
          Registration successful. Check your email to verify your account before logging in.
        </section>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <section className="auth-card" aria-labelledby="register-title">
        <h2 id="register-title">Register</h2>
        <form onSubmit={onSubmit} className="auth-form">
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <Button type="submit" variant="contained" startIcon={<PersonAddAltIcon />} disabled={busy}>
            {busy ? "Creating..." : "Create account"}
          </Button>
        </form>

        {err && <div className="auth-error">{err}</div>}

        <div className="auth-links">
          <span>
            Already have an account? <Link to="/login">Login</Link>
          </span>
        </div>
      </section>
    </div>
  );
}
