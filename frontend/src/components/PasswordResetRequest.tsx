import { useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export default function RequestPasswordResetPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    await fetch(`${API_BASE_URL}/users/request-password-reset`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email }),
    });
    setSent(true);
  }

  if (sent) return <div>If the email exists, a reset link has been sent.</div>;

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Email:
        <input value={email} onChange={e => setEmail(e.target.value)} type="email" required />
      </label>
      <button type="submit">Send Reset Link</button>
    </form>
  );
}