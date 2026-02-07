import React from "react";
import { useNavigate } from "react-router-dom";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>
      <h1>Catalunya Weather App</h1>
      <p>
        Real-time weather, air quality, and activity recommendations for Catalonia.<br />
        Interactive maps, alerts, and more!
      </p>
      <div style={{ margin: "2rem 0" }}>
        <button style={{ margin: "0 1rem" }} onClick={() => navigate("/login")}>
          Login
        </button>
        <button style={{ margin: "0 1rem" }} onClick={() => navigate("/register")}>
          Register
        </button>
      </div>
      <ul style={{ listStyle: "none", padding: 0 }}>
        <li>🌦️ Real-time weather and air quality</li>
        <li>🗺️ Interactive maps of comarques</li>
        <li>⚠️ Alerts and notifications</li>
        <li>🤖 Activity recommendations</li>
      </ul>
    </div>
  );
}