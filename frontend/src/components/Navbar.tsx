import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { useEffect, useState, type ReactElement } from "react";
import CloseIcon from "@mui/icons-material/Close";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import MenuIcon from "@mui/icons-material/Menu";
import "./Navbar.css";

export default function Navbar() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const location = useLocation();
  const [adminOpen, setAdminOpen] = useState(false);
  const [activityOpen, setActivityOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setAdminOpen(false);
    setActivityOpen(false);
    setMobileOpen(false);
  }, [location.pathname]);

  function closeMenus() {
    setAdminOpen(false);
    setActivityOpen(false);
    setMobileOpen(false);
  }

  function onLogout() {
    closeMenus();
    logout();
    nav("/login");
  }

  function navLink(to: string, label: string, key?: string) {
    const isActive = location.pathname === to;
    return (
      <Link
        key={key || to}
        to={to}
        className={`navbar__link${isActive ? " navbar__link--active" : ""}`}
        aria-current={isActive ? "page" : undefined}
        onClick={closeMenus}
      >
        {label}
      </Link>
    );
  }

  function dropdownMenu(
    label: string,
    open: boolean,
    menu: "activity" | "admin",
    links: ReactElement[]
  ) {
    function toggleDropdown() {
      if (menu === "activity") {
        setActivityOpen(!activityOpen);
        setAdminOpen(false);
        return;
      }

      setAdminOpen(!adminOpen);
      setActivityOpen(false);
    }

    return (
      <div className="navbar__dropdown">
        <button
          type="button"
          className={`navbar__dropdownButton${open ? " navbar__dropdownButton--open" : ""}`}
          aria-expanded={open}
          onClick={toggleDropdown}
        >
          <span>{label}</span>
          <KeyboardArrowDownIcon
            className={`navbar__chevron${open ? " navbar__chevron--open" : ""}`}
            fontSize="small"
          />
        </button>
        {open && (
          <div
            className="navbar__dropdownMenu"
            onMouseLeave={() => {
              if (menu === "activity") {
                setActivityOpen(false);
                return;
              }

              setAdminOpen(false);
            }}
          >
            {links}
          </div>
        )}
      </div>
    );
  }

  return (
    <nav className="navbar" aria-label="Main navigation">
      <Link to={user ? "/home" : "/"} className="navbar__brand" onClick={closeMenus}>
        <span className="navbar__brandIcon" aria-hidden="true">🌤️</span>
        <span className="navbar__brandText">Catalunya Weather Portal</span>
      </Link>

      <button
        type="button"
        className="navbar__toggle"
        aria-controls="primary-navigation"
        aria-expanded={mobileOpen}
        aria-label={mobileOpen ? "Close navigation menu" : "Open navigation menu"}
        onClick={() => setMobileOpen(!mobileOpen)}
      >
        {mobileOpen ? <CloseIcon fontSize="small" /> : <MenuIcon fontSize="small" />}
      </button>

      <div
        id="primary-navigation"
        className={`navbar__menu${mobileOpen ? " navbar__menu--open" : ""}`}
      >
        {user && (
          <div className="navbar__links">
            {dropdownMenu(
              "Activity recommendations",
              activityOpen,
              "activity",
              [
                navLink("/home", "Activity recommender", "activity-recommender"),
                navLink("/suggest-activity", "Suggest activity", "suggest-activity"),
              ]
            )}
            {navLink("/historical", "Station explorer", "station-explorer")}
            {navLink("/historical-map", "Station map", "station-map")}
            {navLink("/air-quality-map", "Air quality map", "air-quality-map")}
            {navLink("/episodis-oberts", "Meteo alerts", "meteo-alerts")}
            {navLink("/profile", "Profile", "profile")}
            {/* Show Verify Email only if user is not verified */}
            {user.is_verified === false && navLink("/verify-email", "Verify Email", "verify-email")}

            {user.role === "admin" && (
              dropdownMenu(
                "Admin Management",
                adminOpen,
                "admin",
                [
                  navLink("/activities", "Manage activities", "manage-activities"),
                  navLink("/manage-categories", "Manage categories", "manage-categories"),
                  navLink("/populate", "Populate data", "populate-data"),
                  navLink("/ml-model-trainer", "ML Trainer", "ml-model-trainer"),
                  navLink("/user-management", "User management", "user-management"),
                  navLink("/analytics", "Analytics dashboard", "analytics-dashboard"),
                ]
              )
            )}
          </div>
        )}

        <div className="navbar__spacer" />

        <div className="navbar__account">
          {!user ? (
            <>
              {navLink("/login", "Login")}
              {navLink("/register", "Register")}
              {/* Show password reset links only when not logged in */}
              {navLink("/request-password-reset", "Request Password Reset", "request-password-reset")}
            </>
          ) : (
            <>
              <span className="navbar__user">
                {user.email} ({user.role})
              </span>
              <button type="button" onClick={onLogout} className="navbar__logout">
                Logout
              </button>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
