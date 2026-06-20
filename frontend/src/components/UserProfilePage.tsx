import React, { useState } from "react";
import { useAuth } from "../auth/AuthContext";
import { API_BASE } from '../api/client';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export default function UserProfilePage() {
  const { user, token } = useAuth();
  const [email, setEmail] = useState(user?.email || "");
  const [password, setPassword] = useState("");
  const [notificationPreferences, setNotificationPreferences] = useState(user?.notification_preferences || true);
  const [favoriteComarques, setFavoriteComarques] = useState(user?.favorite_comarques || []);
  const [alertSubscribeCurrentLocation, setAlertSubscribeCurrentLocation] = useState(
    user?.alert_subscribe_current_location ?? false
  );

  const [alertCurrentComarca, setAlertCurrentComarca] = useState(
    user?.alert_current_comarca ?? ""
  );

  const [alertMeteorTypes, setAlertMeteorTypes] = useState(
    user?.alert_meteor_types?.join(",") ?? ""
  );

  const [alertMinSeverity, setAlertMinSeverity] = useState(
    user?.alert_min_severity ?? 2
  );

  const useCurrentLocationForAlerts = () => {
    navigator.geolocation.getCurrentPosition(async pos => {
      const lat = pos.coords.latitude;
      const lon = pos.coords.longitude;

      const res = await fetch(
        `${API_BASE_URL}/comarcas/lookup?lat=${lat}&lon=${lon}`
      );

      if (!res.ok) {
        alert("Could not detect comarca from current location.");
        return;
      }

      const comarca = await res.json();

      if (!comarca?.code) {
        alert("No comarca found for your current location.");
        return;
      }

      setAlertCurrentComarca(comarca.code);
      setAlertSubscribeCurrentLocation(true);

      alert(`Alert location set to ${comarca.name}`);
    });
  };


  const handleSave = async () => {
    const res = await fetch(`${API_BASE_URL}/users/me`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        email,
        password: password || undefined,
        notification_preferences: notificationPreferences,
        favorite_comarques: favoriteComarques,

        alert_subscribe_current_location: alertSubscribeCurrentLocation,
        alert_current_comarca: alertCurrentComarca || null,
        alert_meteor_types: alertMeteorTypes
          .split(",")
          .map(x => x.trim())
          .filter(Boolean),
        alert_min_severity: alertMinSeverity,
      }),
    });
    if (res.ok) {
        alert("Profile updated successfully");
    } else {
        let errorMsg = "Failed to update profile";
        try {
        const data = await res.json();
        if (data && data.detail) {
            let detailMsg = "";
            if (typeof data.detail === "string") {
                detailMsg = data.detail;
            } else if (Array.isArray(data.detail)) {
                detailMsg = data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(", ");
            } else if (typeof data.detail === "object") {
                detailMsg = JSON.stringify(data.detail);
            }
            // Remove "Value error" (case-insensitive) from the message
            detailMsg = detailMsg.replace(/value error, :?/i, "").trim();
            if (detailMsg) {
                errorMsg += `: ${detailMsg}`;
            }
        }
    } catch (e) {
        // ignore JSON parse errors
    }
    alert(errorMsg);
    }
  };

  return (
    <div>
      <h2>User Profile</h2>
      <label>Email: <input value={email} onChange={e => setEmail(e.target.value)} /></label>
      <label>New Password: <input type="password" value={password} onChange={e => setPassword(e.target.value)} /></label>
      <label>Notification Preferences: <input type="checkbox" checked={notificationPreferences} onChange={e => setNotificationPreferences(e.target.checked)} /></label>
      <label>Favorite Comarques: <input value={favoriteComarques} onChange={e => setFavoriteComarques(e.target.value.split(","))} /></label>
      <button onClick={handleSave}>Save</button>

      <h3>Weather alert subscriptions</h3>
      <label>
        Receive weather notifications:
        <input
          type="checkbox"
          checked={notificationPreferences}
          onChange={e => setNotificationPreferences(e.target.checked)}
        />
      </label>

      <br />

      <label>
        Favorite comarques:
        <input
          value={favoriteComarques.join(",")}
          onChange={e =>
            setFavoriteComarques(
              e.target.value
                .split(",")
                .map(x => x.trim())
                .filter(Boolean)
            )
          }
          placeholder="08,13,33"
        />
      </label>

      <br />

      <label>
        Subscribe to current location:
        <input
          type="checkbox"
          checked={alertSubscribeCurrentLocation}
          onChange={e => setAlertSubscribeCurrentLocation(e.target.checked)}
        />
      </label>

      <button type="button" onClick={useCurrentLocationForAlerts}>
        Use my current comarca
      </button>

      <br />

      <label>
        Current location comarca code:
        <input
          value={alertCurrentComarca}
          onChange={e => setAlertCurrentComarca(e.target.value)}
          placeholder="13"
        />
      </label>

      <br />

      <label>
        Meteor types:
        <input
          value={alertMeteorTypes}
          onChange={e => setAlertMeteorTypes(e.target.value)}
          placeholder="Pluja, Vent, Calor"
        />
      </label>

      <br />

      <label>
        Minimum severity:
        <input
          type="number"
          min={0}
          max={6}
          value={alertMinSeverity}
          onChange={e => setAlertMinSeverity(Number(e.target.value))}
        />
      </label>
    </div>
  );
}