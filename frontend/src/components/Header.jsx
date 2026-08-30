import { useNavigate, useLocation } from "react-router-dom";
import { User, CreditCard, LogOut, Sparkles, ChevronLeft } from "lucide-react";
import { LanguageToggle } from "@/components/LanguageToggle";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

export function Header({ dark = false, back = false }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { t } = useI18n();

  const base = dark ? "bg-lumiere-base/70 border-white/10" : "bg-lumiere-ivory/70 border-black/10";
  const txt = dark ? "text-lumiere-ivory" : "text-lumiere-ink";
  const sub = dark ? "text-lumiere-ivory/60" : "text-lumiere-ink/50";

  const nav = [
    { label: t("home"), to: "/studio" },
    { label: t("createVideo"), to: "/create-video" },
    { label: t("pricing"), to: "/pricing" },
  ];

  const initial = (user?.name || user?.email || "L").charAt(0).toUpperCase();

  return (
    <header className={`sticky top-0 z-40 flex items-center justify-between px-4 sm:px-8 py-4 backdrop-blur-xl border-b ${base}`}>
      <div className="flex items-center gap-3">
        {back && (
          <button data-testid="back-button" onClick={() => navigate("/studio")} className={`${sub} hover:${txt} transition-colors`}>
            <ChevronLeft size={20} />
          </button>
        )}
        <button onClick={() => navigate("/studio")} className={`font-display text-xl sm:text-2xl font-black tracking-tight ${txt}`}>
          LUMIÈRE
        </button>
      </div>

      <nav className="hidden md:flex items-center gap-1">
        {nav.map((n) => {
          const active = location.pathname === n.to;
          return (
            <button key={n.to} data-testid={`nav-${n.to.replace(/\//g, "") || "home"}`} onClick={() => navigate(n.to)}
              className={`px-4 py-2 font-body text-sm rounded-full transition-colors ${active ? "text-lumiere-ink bg-lumiere-gold" : `${sub} hover:${txt}`}`}>
              {n.label}
            </button>
          );
        })}
      </nav>

      <div className="flex items-center gap-3">
        <LanguageToggle dark={dark} />
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button data-testid="avatar-menu-button" className="w-9 h-9 rounded-full overflow-hidden border border-lumiere-gold/60 flex items-center justify-center bg-lumiere-gold/20">
              {user?.picture ? (
                <img src={user.picture} alt="" className="w-full h-full object-cover" />
              ) : (
                <span className={`font-display text-sm ${txt}`}>{initial}</span>
              )}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="bg-lumiere-warm border border-black/10 text-lumiere-ink rounded-xl w-52">
            <div className="px-3 py-2">
              <p className="font-display text-sm truncate">{user?.name || "Creator"}</p>
              <p className="font-mono text-[0.65rem] text-lumiere-ink/50 truncate">{user?.email}</p>
            </div>
            <DropdownMenuSeparator />
            <DropdownMenuItem data-testid="menu-account" onClick={() => navigate("/account")} className="cursor-pointer gap-2"><User size={15} /> {t("account")}</DropdownMenuItem>
            <DropdownMenuItem data-testid="menu-pricing" onClick={() => navigate("/pricing")} className="cursor-pointer gap-2"><CreditCard size={15} /> {t("managePlan")}</DropdownMenuItem>
            <DropdownMenuItem data-testid="menu-create-video" onClick={() => navigate("/create-video")} className="cursor-pointer gap-2"><Sparkles size={15} /> {t("createVideo")}</DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem data-testid="menu-signout" onClick={logout} className="cursor-pointer gap-2 text-red-600"><LogOut size={15} /> {t("signOut")}</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
