import { useNavigate, useLocation } from "react-router-dom";
import { User, LogOut, ChevronLeft, Home as HomeIcon, Film, Plus, Clapperboard } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";
import {
  DropdownMenu, DropdownMenuTrigger, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

const LAST_EXP_KEY = "lumiere_last_exp";

export function Header({ dark = false, back = false }) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { lang } = useI18n();
  const L = lang === "es"
    ? { home: "Inicio", experiences: "Experiencias", create: "Crear", studio: "Estudio", profile: "Perfil", signout: "Cerrar sesión", admin: "Admin" }
    : { home: "Home", experiences: "Experiences", create: "Create", studio: "Studio", profile: "Profile", signout: "Sign out", admin: "Admin" };

  const base = dark ? "bg-lumiere-base/70 border-white/10" : "bg-lumiere-ivory/70 border-black/10";
  const txt = dark ? "text-lumiere-ivory" : "text-lumiere-ink";
  const sub = dark ? "text-lumiere-ivory/60" : "text-lumiere-ink/50";

  const goStudio = () => {
    const last = localStorage.getItem(LAST_EXP_KEY);
    navigate(last ? `/studio/${last}` : "/experiences");
  };

  // Exactly 5 primary navigation entries (v2.0 Block 0).
  const nav = [
    { key: "home", label: L.home, icon: HomeIcon, onClick: () => navigate("/studio"), active: location.pathname === "/studio" },
    { key: "experiences", label: L.experiences, icon: Film, onClick: () => navigate("/experiences"), active: location.pathname === "/experiences" },
    { key: "create", label: L.create, icon: Plus, onClick: () => navigate("/create"), active: location.pathname === "/create" },
    { key: "studio", label: L.studio, icon: Clapperboard, onClick: goStudio, active: location.pathname.startsWith("/studio/") },
    { key: "profile", label: L.profile, icon: User, onClick: () => navigate("/account"), active: location.pathname === "/account" },
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

      <nav className="hidden md:flex items-center gap-1" data-testid="primary-nav">
        {nav.map((n) => (
          <button key={n.key} data-testid={`nav-${n.key}`} onClick={n.onClick}
            className={`px-4 py-2 font-body text-sm rounded-full transition-colors ${n.active ? "text-lumiere-ink bg-lumiere-gold" : `${sub} hover:${txt}`}`}>
            {n.label}
          </button>
        ))}
      </nav>

      <div className="flex items-center gap-3">
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
            <DropdownMenuItem data-testid="menu-account" onClick={() => navigate("/account")} className="cursor-pointer gap-2"><User size={15} /> {L.profile}</DropdownMenuItem>
            {user?.is_admin && (
              <DropdownMenuItem data-testid="menu-admin" onClick={() => navigate("/admin")} className="cursor-pointer gap-2"><User size={15} /> {L.admin}</DropdownMenuItem>
            )}
            <DropdownMenuSeparator />
            <DropdownMenuItem data-testid="menu-signout" onClick={logout} className="cursor-pointer gap-2 text-red-600"><LogOut size={15} /> {L.signout}</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}
