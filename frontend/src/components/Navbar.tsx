import { Link, useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useState } from "react";

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const location = useLocation();
  const [adminOpen, setAdminOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [suggestOpen, setSuggestOpen] = useState(false);

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
    display: "block"
  };

  const linkActiveStyle: React.CSSProperties = {
    background: "rgba(255,255,255,0.12)",
  };

  const spacer: React.CSSProperties = { flex: 1 };

  function navLink(to: string, label: string, key?: string) {
    const isActive = location.pathname === to;
    return (
      <Link
        key={key || to}
        to={to}
        style={isActive ? { ...linkStyle, ...linkActiveStyle } : linkStyle}
        onClick={() => {
          setAdminOpen(false);
          setActivityOpen(false);
          setSuggestOpen(false);
        }}
      >
        {label}
      </Link>
    );
  }

  function dropdownMenu(label: string, open: boolean, setOpen: (v: boolean) => void, links: JSX.Element[]) {
    return (
      <div style={{ position: "relative" }}>
        <button
          style={{
            background: "rgba(255,255,255,0.12)",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            padding: "6px 14px",
            fontWeight: 600,
            cursor: "pointer",
            minWidth: 140,
          }}
          onClick={() => setOpen(!open)}
        >
          {label} ▼
        </button>
        {open && (
          <div
            style={{
              position: "absolute",
              top: "110%",
              left: 0,
              background: "#1976d2",
              borderRadius: 6,
              boxShadow: "0 2px 8px rgba(21,101,192,0.18)",
              zIndex: 100,
              minWidth: 200,
              padding: "8px 0",
            }}
            onMouseLeave={() => setOpen(false)}
          >
            {links}
          </div>
        )}
      </div>
    );
  }

  return (
    <div style={wrap}>
      <b style={{ marginRight: 20, marginLeft: 50 }}>🌤️ Catalunya Weather Portal</b>

      {user && (
        <>
          {dropdownMenu(
            "Activity recommendations",
            activityOpen,
            setActivityOpen,
            [
              navLink("/", "Activity recommender", "activity-recommender"),
              navLink("/suggest-activity", "Suggest activity", "suggest-activity"),
            ]
          )}
          {navLink("/historical", "Historical data", "historical-data")}
          {navLink("/air-quality-map", "Air quality map", "air-quality-map")}
          {navLink("/episodis-oberts", "Meteo alerts", "meteo-alerts")}

          {user.role === "admin" && (
            dropdownMenu(
              "Admin Management",
              adminOpen,
              setAdminOpen,
              [
                navLink("/activities", "Manage activities", "manage-activities"),
                navLink("/manage-categories", "Manage categories", "manage-categories"),
                navLink("/populate", "Populate data", "populate-data"),
                navLink("/ml-model-trainer", "ML Trainer", "ml-model-trainer"),
              ]
            )
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