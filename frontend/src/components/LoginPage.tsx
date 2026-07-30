import React, { useState } from "react";
import LoginIcon from "@mui/icons-material/Login";
import { Button } from "@mui/material";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();
  const nav = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setBusy(true);
    try {
      await login(email, password);
      nav("/");
    } catch (e: any) {
      setErr(e?.message ?? "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <section className="auth-card" aria-labelledby="login-title">
        <h2 id="login-title">Login</h2>
        <form onSubmit={onSubmit} className="auth-form">
          <label>
            Email
            <input value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </label>
          <Button type="submit" variant="contained" startIcon={<LoginIcon />} disabled={busy}>
            {busy ? "Signing in..." : "Login"}
          </Button>
        </form>

        {err && <div className="auth-error">{err}</div>}

        <div className="auth-links">
          <span>
            No account? <Link to="/register">Register</Link>
          </span>
          <Link to="/request-password-reset">Forgot password?</Link>
        </div>
      </section>
    </div>
  );
}
