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
    </div>
  );
}