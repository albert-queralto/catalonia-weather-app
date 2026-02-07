import { useState } from "react";
import { useSearchParams } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export default function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState<"idle" | "success" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState<string>("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      setErrorMsg("Missing token.");
      setTimeout(() => window.location.reload(), 2000);
      return;
    }
    try {
      const res = await fetch(`${API_BASE_URL}/users/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });
      if (res.ok) {
        setStatus("success");
        setErrorMsg("");
      } else {
        setStatus("error");
        let data = {};
        try {
          data = await res.json();
        } catch {
          // If response is not JSON, fallback
        }
        let filteredMsg = data.detail || data.message || "Password reset failed.";
        if (Array.isArray(data.detail)) {
          const errorObj = data.detail.find(
            (d: any) => typeof d.msg === "string" && !d.msg.startsWith("Value error")
          );
          filteredMsg = errorObj?.msg || data.detail[0]?.msg || "Password reset failed.";
          if (filteredMsg.startsWith("Value error,")) {
            filteredMsg = filteredMsg.split(",").slice(1).join(",").trim();
          }
        }
        setErrorMsg(filteredMsg);
        setTimeout(() => window.location.reload(), 2000); // Reload after 2 seconds
      }
    } catch (err) {
      setStatus("error");
      setErrorMsg("Network error or unexpected error occurred.");
      setTimeout(() => window.location.reload(), 2000); // Reload after 2 seconds
    }
  }

  if (status === "success") return <div>Password reset successful! You can now log in.</div>;
  if (status === "error") return <div>Password reset failed. {errorMsg}</div>;

  return (
    <form onSubmit={handleSubmit}>
      <label>
        New Password:
        <input
          value={password}
          onChange={e => setPassword(e.target.value)}
          type="password"
          required
        />
      </label>
      <button type="submit">Reset Password</button>
    </form>
  );
}