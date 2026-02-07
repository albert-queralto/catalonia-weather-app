import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export default function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setStatus("error");
      return;
    }
    fetch(`${API_BASE_URL}/users/verify-email?token=${token}`)
      .then(res => res.ok ? setStatus("success") : setStatus("error"))
      .catch(() => setStatus("error"));
  }, [searchParams]);

  if (status === "loading") return <div>Verifying email...</div>;
  if (status === "success") return <div>Email verified! You can now log in.</div>;
  return <div>Verification failed. Please try again or contact support.</div>;
}