import { useNavigate } from "react-router-dom";
import { LogOut, ChevronLeft } from "lucide-react";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";

export function Header({ back }) {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const { t } = useI18n();
  return (
    <header className="sticky top-0 z-40 flex items-center justify-between px-4 sm:px-8 py-4 bg-lumiere-base/80 backdrop-blur-xl border-b border-white/10">
      <div className="flex items-center gap-3">
        {back && (
          <button data-testid="back-button" onClick={() => navigate("/studio")}
            className="text-zinc-400 hover:text-white transition-colors">
            <ChevronLeft size={20} />
          </button>
        )}
        <button onClick={() => navigate("/studio")} className="font-display text-xl sm:text-2xl font-black tracking-tight text-white">
          LUMIÈRE
        </button>
        <span className="label-mono hidden sm:inline">Agentic Studio</span>
      </div>
      <div className="flex items-center gap-3">
        <LanguageToggle />
        <button data-testid="logout-button" onClick={logout}
          className="text-zinc-500 hover:text-lumiere-orange transition-colors" title={t("logout")}>
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
