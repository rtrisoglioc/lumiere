import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { CreditCard, Shield, Settings as SettingsIcon, LogOut, Lock } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";
import { Header } from "@/components/Header";

export default function Account() {
  const { user, logout } = useAuth();
  const { t, lang, setLang } = useI18n();
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);

  useEffect(() => { api.get("/account").then((r) => setAccount(r.data)).catch(() => {}); }, []);

  const plan = account?.plan;
  const usage = account?.usage;
  const limits = account?.limits;
  const initial = (user?.name || user?.email || "L").charAt(0).toUpperCase();

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink">
      <Header back />
      <main className="px-4 sm:px-8 lg:px-16 py-12 max-w-4xl mx-auto space-y-10" data-testid="account-page">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="label-mono text-lumiere-ink/50 mb-2">{t("account")}</p>
            <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight">{t("profile")}</h1>
          </div>
          <div className="flex items-center gap-1 border border-black/10 rounded-full p-1 bg-lumiere-warm" data-testid="language-toggle">
            {["en", "es"].map((lg) => (
              <button key={lg} data-testid={`lang-${lg}`} onClick={() => { setLang(lg); localStorage.setItem("lumiere_lang", lg); }}
                className={`px-3 py-1.5 rounded-full font-mono text-[0.6rem] uppercase tracking-widest transition-colors ${lang === lg ? "bg-lumiere-ink text-lumiere-ivory" : "text-lumiere-ink/50 hover:text-lumiere-ink"}`}>
                {lg === "en" ? "English" : "Español"}
              </button>
            ))}
          </div>
        </div>

        {/* profile card — NO video */}
        <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-8 flex items-center gap-6">
          <div className="w-20 h-20 rounded-full overflow-hidden border-2 border-lumiere-gold/60 flex items-center justify-center bg-lumiere-gold/20 shrink-0">
            {user?.picture ? <img src={user.picture} alt="" className="w-full h-full object-cover" />
              : <span className="font-display text-2xl">{initial}</span>}
          </div>
          <div className="min-w-0">
            <h2 className="font-display text-2xl font-bold truncate">{user?.name || "Creator"}</h2>
            <p className="font-mono text-sm text-lumiere-ink/50 truncate">{user?.email}</p>
            <span className="inline-block mt-2 font-mono text-[0.6rem] uppercase tracking-widest px-2 py-0.5 rounded-full bg-lumiere-gold/20 text-lumiere-ink">{plan?.name || "LUMIÈRE FREE"}</span>
          </div>
        </div>

        {/* plan + usage */}
        <div className="grid sm:grid-cols-2 gap-6">
          <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-6">
            <p className="label-mono text-lumiere-ink/50 mb-2">{t("currentPlanLabel")}</p>
            <h3 className="font-display text-2xl font-bold">{plan?.name}</h3>
            <button data-testid="account-manage-plan" onClick={() => navigate("/pricing")}
              className="mt-4 inline-flex items-center gap-2 bg-lumiere-gold hover:bg-lumiere-goldHover text-lumiere-ink px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              <CreditCard size={14} /> {t("managePlan")}
            </button>
          </div>
          {usage && limits && (
            <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-6 space-y-3">
              <p className="label-mono text-lumiere-ink/50">{t("usageLabel")}</p>
              {[["experiences", t("story")], ["cuts", t("finalFilm")], ["ai_generations", t("aiVideoGen")]].map(([k, label]) => {
                const val = usage[k] || 0; const lim = limits[k] || 1; const pct = Math.min(100, Math.round((val / lim) * 100));
                return (
                  <div key={k}>
                    <div className="flex justify-between mb-1"><span className="text-sm text-lumiere-ink/70">{label}</span>
                      <span className="font-mono text-xs text-lumiere-ink/60">{val}/{lim}</span></div>
                    <div className="h-1.5 bg-black/10 rounded-full overflow-hidden"><div className="h-full bg-lumiere-gold rounded-full" style={{ width: `${pct}%` }} /></div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* settings + privacy */}
        <div className="grid sm:grid-cols-2 gap-6">
          <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-6">
            <div className="flex items-center gap-2 mb-3"><SettingsIcon size={16} className="text-lumiere-ink/60" /><p className="label-mono text-lumiere-ink/50">{t("settings")}</p></div>
            <p className="text-sm text-lumiere-ink/60">Language, notifications and playback preferences.</p>
          </div>
          <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-6">
            <div className="flex items-center gap-2 mb-3"><Shield size={16} className="text-lumiere-sage" /><p className="label-mono text-lumiere-ink/50">{t("privacy")}</p></div>
            <p className="text-sm text-lumiere-ink/60 flex items-center gap-2"><Lock size={13} /> Experiences are private by default. Originals are never modified.</p>
          </div>
        </div>

        <button data-testid="account-signout" onClick={logout}
          className="inline-flex items-center gap-2 border border-red-300 text-red-600 hover:bg-red-50 px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
          <LogOut size={14} /> {t("signOut")}
        </button>
      </main>
    </div>
  );
}
