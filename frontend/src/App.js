import "@/App.css";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { I18nProvider } from "@/i18n";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Login from "@/pages/Login";
import Landing from "@/pages/Landing";
import AuthCallback from "@/pages/AuthCallback";
import Home from "@/pages/Home";
import Experience from "@/pages/Experience";
import Account from "@/pages/Account";
import Pricing from "@/pages/Pricing";
import CreateVideo from "@/pages/CreateVideo";
import SocialStudio from "@/pages/SocialStudio";
import Admin from "@/pages/Admin";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-lumiere-ivory">
        <span className="font-mono text-lumiere-gold text-sm cursor-blink">LUMIÈRE</span>
      </div>
    );
  }
  if (!user) return <Navigate to="/" replace />;
  return children;
}

function AppRouter() {
  const location = useLocation();
  if (location.hash?.includes("session_id=")) return <AuthCallback />;
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<Login />} />
      <Route path="/studio" element={<Protected><Home /></Protected>} />
      <Route path="/studio/:id" element={<Protected><Experience /></Protected>} />
      <Route path="/account" element={<Protected><Account /></Protected>} />
      <Route path="/pricing" element={<Protected><Pricing /></Protected>} />
      <Route path="/create-video" element={<Protected><CreateVideo /></Protected>} />
      <Route path="/social" element={<Protected><SocialStudio /></Protected>} />
      <Route path="/admin" element={<Protected><Admin /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App font-body">
      <I18nProvider>
        <AuthProvider>
          <BrowserRouter>
            <AppRouter />
          </BrowserRouter>
          <Toaster position="top-center" theme="dark" />
        </AuthProvider>
      </I18nProvider>
    </div>
  );
}
