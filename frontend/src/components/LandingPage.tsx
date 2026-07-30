import React from "react";
import LoginIcon from "@mui/icons-material/Login";
import PersonAddAltIcon from "@mui/icons-material/PersonAddAlt";
import { Button } from "@mui/material";
import { useNavigate } from "react-router-dom";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing">
      <section className="landing__hero" aria-labelledby="landing-title">
        <div className="landing__content">
          <p className="landing__eyebrow">Catalonia conditions, alerts, and planning</p>
          <h1 id="landing-title" className="landing__title">
            Catalunya Weather Portal
          </h1>
          <p className="landing__copy">
            A calm planning desk for regional forecasts, air quality signals, Meteocat warnings,
            and weather-aware activity choices across Catalonia.
          </p>
          <div className="landing__actions">
            <Button
              variant="contained"
              size="large"
              startIcon={<LoginIcon />}
              onClick={() => navigate("/login")}
            >
              Login
            </Button>
            <Button
              variant="outlined"
              size="large"
              color="inherit"
              startIcon={<PersonAddAltIcon />}
              onClick={() => navigate("/register")}
              sx={{
                borderColor: "rgba(255, 255, 255, 0.46)",
                color: "#ffffff",
                backgroundColor: "rgba(255, 255, 255, 0.12)",
                backdropFilter: "blur(12px)",
                "&:hover": {
                  borderColor: "rgba(255, 255, 255, 0.7)",
                  backgroundColor: "rgba(255, 255, 255, 0.2)",
                },
              }}
            >
              Register
            </Button>
          </div>
        </div>
      </section>

      <section className="landing__forecast-strip" aria-label="Portal highlights">
        <div className="landing__metric">
          <span className="landing__metric-label">Weather</span>
          <span className="landing__metric-value">Live regional context</span>
        </div>
        <div className="landing__metric">
          <span className="landing__metric-label">Air</span>
          <span className="landing__metric-value">Quality-aware decisions</span>
        </div>
        <div className="landing__metric">
          <span className="landing__metric-label">Alerts</span>
          <span className="landing__metric-value">Meteocat warnings</span>
        </div>
        <div className="landing__metric">
          <span className="landing__metric-label">Activities</span>
          <span className="landing__metric-value">Forecast-fit options</span>
        </div>
      </section>

      <section className="landing__secondary">
        <h2>Built for days when the weather changes the plan.</h2>
        <p>
          Compare local station signals, scan map-based conditions, and choose activities with
          the practical weather context already in view.
        </p>
      </section>
    </div>
  );
}
