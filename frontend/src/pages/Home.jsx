import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Plus, ArrowUpRight, Play, Film, Gauge, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useI18n } from "@/i18n";
import { useAuth } from "@/context/AuthContext";
import { Header } from "@/components/Header";
import { LoopStrip } from "@/components/LoopStrip";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { Input } from "@/components/ui/input";

const TYPES = ["travel", "event", "lifestyle"];
const IMGS = {
  travel: "https://images.unsplash.com/photo-1782835576404-f5eaddd63ac3?crop=entropy&cs=srgb&fm=jpg&w=800&q=80",
  event: "https://images.unsplash.com/photo-1485846234645-a62644f84728?crop=entropy&cs=srgb&fm=jpg&w=800&q=80",
  lifestyle: "https://images.unsplash.com/photo-1782714040856-cf19b8ba888b?crop=entropy&cs=srgb&fm=jpg&w=800&q=80",
};

export default function Home() {
  const { t, lang } = useI18n();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [experiences, setExperiences] = useState([]);
  const [account, setAccount] = useState(null);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [type, setType] = useState("travel");
  const [creating, setCreating] = useState(false);
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const load = async () => {
    try {
      const [e, a] = await Promise.all([api.get("/experiences"), api.get("/account")]);
      setExperiences(e.data); setAccount(a.data);
    } catch { /* */ }
  };
  useEffect(() => { load(); }, []);

  const create = async () => {
    if (!title.trim()) return;
    setCreating(true);
    try {
      const res = await api.post("/experiences", { title: title.trim(), type });
      setOpen(false); setTitle("");
      navigate(`/studio/${res.data.id}`);
    } catch { toast.error("Failed to create"); }
    finally { setCreating(false); }
  };

  const active = experiences[0];
  const plan = account?.plan;
  const usage = account?.usage;
  const limits = account?.limits;

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await api.delete(`/experiences/${pendingDelete.id}`);
      setExperiences((prev) => prev.filter((e) => e.id !== pendingDelete.id));
      setPendingDelete(null);
      toast.success(t("deletedExp"));
      load();
    } catch { toast.error("Error"); }
    finally { setDeleting(false); }
  };

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink">
      <Header />

      {/* hero */}
      <section className="px-4 sm:px-8 lg:px-16 pt-10 pb-6 max-w-7xl mx-auto">
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="label-mono text-lumiere-ink/50 mb-3">
          {t("welcomeBack")}, {(user?.name || "Creator").split(" ")[0]}
        </motion.p>
        <motion.h1 initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}
          className="font-display text-4xl sm:text-6xl font-black tracking-tight max-w-3xl leading-[0.95]">
          {t("tagline")}
        </motion.h1>
        <p className="mt-5 text-base sm:text-lg text-lumiere-ink/60 max-w-2xl italic">{t("positioning")}</p>
      </section>

      <LoopStrip />

      <main className="px-4 sm:px-8 lg:px-16 py-10 max-w-7xl mx-auto grid lg:grid-cols-3 gap-8">
        {/* left/main */}
        <div className="lg:col-span-2 space-y-10">
          {active && (
            <div>
              <p className="label-mono text-lumiere-ink/50 mb-3">{t("activeExperience")}</p>
              <div className="relative overflow-hidden rounded-2xl border border-black/10 group">
                <img src={IMGS[active.type] || IMGS.travel} alt="" className="w-full h-64 object-cover" />
                <div className="absolute inset-0 bg-gradient-to-t from-lumiere-ink/80 via-lumiere-ink/20 to-transparent" />
                <button data-testid={`delete-active-${active.id}`} onClick={() => setPendingDelete(active)}
                  title={t("deleteExp")}
                  className="absolute top-3 right-3 w-9 h-9 flex items-center justify-center rounded-full bg-lumiere-ink/50 backdrop-blur text-lumiere-ivory/80 hover:bg-red-600 hover:text-white transition-colors">
                  <Trash2 size={16} />
                </button>
                <div className="absolute bottom-0 left-0 p-6">
                  <span className="font-mono text-xs uppercase tracking-widest text-lumiere-gold">{active.type} · {active.stage}</span>
                  <h2 className="font-display text-3xl font-bold text-lumiere-ivory mt-1">{active.title}</h2>
                  <button data-testid="continue-experience" onClick={() => navigate(`/studio/${active.id}`)}
                    className="mt-4 inline-flex items-center gap-2 bg-lumiere-gold hover:bg-lumiere-goldHover text-lumiere-ink px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
                    <Play size={14} /> {t("continueExp")}
                  </button>
                </div>
              </div>
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-4">
              <p className="label-mono text-lumiere-ink/50">{t("recentFilms")}</p>
              <Dialog open={open} onOpenChange={setOpen}>
                <DialogTrigger asChild>
                  <button data-testid="new-experience-button" className="inline-flex items-center gap-2 bg-lumiere-ink text-lumiere-ivory hover:bg-lumiere-ink/85 px-4 py-2 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
                    <Plus size={14} /> {t("createNew")}
                  </button>
                </DialogTrigger>
                <DialogContent className="bg-lumiere-warm border border-black/10 text-lumiere-ink rounded-2xl">
                  <DialogHeader>
                    <DialogTitle className="font-display text-3xl">{t("createExperience")}</DialogTitle>
                    <DialogDescription className="text-lumiere-ink/50">{t("subtitle")}</DialogDescription>
                  </DialogHeader>
                  <div className="space-y-5 pt-2">
                    <div>
                      <label className="label-mono block mb-2 text-lumiere-ink/60">{t("title")}</label>
                      <Input data-testid="experience-title-input" value={title} onChange={(e) => setTitle(e.target.value)}
                        className="bg-white border-black/15 rounded-lg focus-visible:ring-lumiere-gold" placeholder="Coastal Road Trip" />
                    </div>
                    <div>
                      <label className="label-mono block mb-2 text-lumiere-ink/60">{t("type")}</label>
                      <div className="flex gap-2">
                        {TYPES.map((ty) => (
                          <button key={ty} data-testid={`type-${ty}`} onClick={() => setType(ty)}
                            className={`px-4 py-2 font-mono text-xs uppercase tracking-widest border rounded-full transition-colors ${type === ty ? "border-lumiere-gold bg-lumiere-gold/15 text-lumiere-ink" : "border-black/15 text-lumiere-ink/50 hover:text-lumiere-ink"}`}>
                            {ty}
                          </button>
                        ))}
                      </div>
                    </div>
                    <button data-testid="confirm-create-button" onClick={create} disabled={creating}
                      className="w-full bg-lumiere-gold hover:bg-lumiere-goldHover disabled:opacity-50 text-lumiere-ink py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
                      {creating ? "…" : t("create")}
                    </button>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            {experiences.length === 0 ? (
              <div className="border border-dashed border-black/15 rounded-2xl py-20 text-center">
                <Film size={36} className="mx-auto text-lumiere-ink/30 mb-3" />
                <p className="text-lumiere-ink/50">{t("noExperiences")}</p>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 gap-4">
                {experiences.map((exp, i) => (
                  <motion.div key={exp.id} data-testid={`experience-card-${exp.id}`}
                    initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                    className="group relative text-left rounded-2xl overflow-hidden border border-black/10 hover:border-lumiere-gold/60 transition-colors bg-lumiere-warm">
                    <button data-testid={`delete-experience-${exp.id}`}
                      onClick={(e) => { e.stopPropagation(); setPendingDelete(exp); }} title={t("deleteExp")}
                      className="absolute top-3 right-3 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-lumiere-ink/50 backdrop-blur text-lumiere-ivory/80 hover:bg-red-600 hover:text-white opacity-0 group-hover:opacity-100 transition-all">
                      <Trash2 size={16} />
                    </button>
                    <button onClick={() => navigate(`/studio/${exp.id}`)} className="block w-full text-left">
                      <div className="relative h-40 overflow-hidden">
                        <img src={IMGS[exp.type] || IMGS.travel} alt="" className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
                      </div>
                      <div className="p-5">
                        <div className="flex items-center justify-between">
                          <h3 className="font-display text-xl font-bold">{exp.title}</h3>
                          <ArrowUpRight size={16} className="text-lumiere-ink/30 group-hover:text-lumiere-gold transition-colors" />
                        </div>
                        <p className="font-mono text-xs text-lumiere-ink/50 mt-1 uppercase">{exp.type} · {exp.stage}</p>
                      </div>
                    </button>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* sidebar: plan + usage */}
        <aside className="space-y-6">
          <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-6">
            <p className="label-mono text-lumiere-ink/50 mb-2">{t("currentPlanLabel")}</p>
            <h3 className="font-display text-2xl font-bold">{plan?.name || "LUMIÈRE FREE"}</h3>
            <button data-testid="home-manage-plan" onClick={() => navigate("/pricing")}
              className="mt-4 w-full inline-flex items-center justify-center gap-2 border border-lumiere-gold text-lumiere-ink hover:bg-lumiere-gold/15 px-4 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              <Gauge size={14} /> {t("managePlan")}
            </button>
          </div>

          {usage && limits && (
            <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-6 space-y-4">
              <p className="label-mono text-lumiere-ink/50">{t("usageLabel")}</p>
              {[
                { k: "experiences", label: t("story") },
                { k: "cuts", label: t("finalFilm") },
              ].map((row) => {
                const val = usage[row.k] || 0; const lim = limits[row.k] || 1;
                const pct = Math.min(100, Math.round((val / lim) * 100));
                return (
                  <div key={row.k}>
                    <div className="flex justify-between mb-1">
                      <span className="text-sm text-lumiere-ink/70">{row.label}</span>
                      <span className="font-mono text-xs text-lumiere-ink/60">{val}/{lim}</span>
                    </div>
                    <div className="h-1.5 bg-black/10 rounded-full overflow-hidden">
                      <div className="h-full bg-lumiere-gold rounded-full" style={{ width: `${pct}%`, transition: "width 0.8s ease" }} />
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          <button data-testid="home-create-video" onClick={() => navigate("/create")}
            className="w-full rounded-2xl border border-lumiere-gold/40 bg-lumiere-gold/5 p-6 text-left hover:bg-lumiere-gold/10 transition-colors">
            <p className="label-mono text-lumiere-gold mb-1">New story</p>
            <p className="font-display text-lg">Start an experience</p>
          </button>
        </aside>
      </main>

      <AlertDialog open={!!pendingDelete} onOpenChange={(o) => { if (!o) setPendingDelete(null); }}>
        <AlertDialogContent data-testid="delete-experience-dialog" className="bg-lumiere-warm border border-black/10 text-lumiere-ink">
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display text-2xl">{t("deleteExpTitle")}</AlertDialogTitle>
            <AlertDialogDescription className="text-lumiere-ink/60">
              {pendingDelete ? <span className="font-semibold">{pendingDelete.title}</span> : null} — {t("deleteExpBody")}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel data-testid="delete-cancel" className="rounded-full">{t("cancel")}</AlertDialogCancel>
            <AlertDialogAction data-testid="delete-confirm" onClick={confirmDelete} disabled={deleting}
              className="rounded-full bg-red-600 hover:bg-red-700 text-white">
              {deleting ? "…" : t("deleteExp")}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
