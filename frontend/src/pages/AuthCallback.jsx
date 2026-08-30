import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";

export default function AuthCallback() {
  const { finalizeSession } = useAuth();
  const navigate = useNavigate();
  const processed = useRef(false);
  const [error, setError] = useState(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const hash = window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? decodeURIComponent(match[1]) : null;
    if (!sessionId) {
      navigate("/", { replace: true });
      return;
    }
    (async () => {
      try {
        await finalizeSession(sessionId);
        window.history.replaceState(null, "", window.location.pathname);
        navigate("/studio", { replace: true });
      } catch {
        setError(true);
        setTimeout(() => navigate("/", { replace: true }), 1500);
      }
    })();
  }, [finalizeSession, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-lumiere-base">
      <span className="font-mono text-sm text-lumiere-orange cursor-blink">
        {error ? "AUTH FAILED" : "AUTHENTICATING"}
      </span>
    </div>
  );
}
