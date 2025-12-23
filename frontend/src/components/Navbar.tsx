import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const location = useLocation();

  function onLogout() {
    logout();
    nav("/login");
  }

  const wrap: React.CSSProperties = {
    display: "flex",
    gap: 16,
    alignItems: "center",
    padding: "14px 24px",
    borderBottom: "2px solid #1565c0",
    background: "linear-gradient(90deg, #1976d2 0%, #1565c0 100%)",
    color: "#fff",
    fontFamily: "Segoe UI, Arial, sans-serif",
    fontSize: 17,
    minHeight: 56,
    boxShadow: "0 2px 8px rgba(21,101,192,0.08)"
  };

  const linkStyle: React.CSSProperties = {
    color: "#fff",
    textDecoration: "none",
    fontWeight: 500,
    padding: "6px 12px",
    borderRadius: 4,
    transition: "background 0.2s",
  };

  const linkActiveStyle: React.CSSProperties = {
    background: "rgba(255,255,255,0.12)",
  };

  const spacer: React.CSSProperties = { flex: 1 };

  // Helper to merge styles
  function navLink(to: string, label: string) {
    const isActive = location.pathname === to;
    return (
      <Link
        to={to}
        style={isActive ? { ...linkStyle, ...linkActiveStyle } : linkStyle}
      >
        {label}
      </Link>
    );
  }

  return (
    <div style={wrap}>
      <b style={{ marginRight: 20, marginLeft: 50 }}>🌤️ Catalunya Weather Portal</b>

      {user && (
        <>
          {navLink("/", "Activity recommendations")}
          {navLink("/historical", "Historical data")}
          {navLink("/air-quality-map", "Air quality map")}
          {navLink("/episodis-oberts", "Meteo alerts")}

          {user.role === "admin" && (
            <>
              {navLink("/populate", "Populate data")}
              {navLink("/ml-model-trainer", "ML Trainer")}
            </>
          )}
        </>
      )}

      <div style={spacer} />

      {!user ? (
        <>
          {navLink("/login", "Login")}
          {navLink("/register", "Register")}
        </>
      ) : (
        <>
          <span style={{ opacity: 0.8 }}>
            {user.email} ({user.role})
          </span>
          <button
            onClick={onLogout}
            style={{
              background: "#fff",
              color: "#1565c0",
              border: "none",
              borderRadius: 4,
              padding: "6px 14px",
              fontWeight: 600,
              cursor: "pointer",
              marginLeft: 4,
              transition: "background 0.2s",
            }}
          >Logout</button>
        </>
      )}
    </div>
  );
}