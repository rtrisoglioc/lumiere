import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Plus, Film, Lock, ArrowUpRight } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useI18n } from "@/i18n";
import { Header } from "@/components/Header";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

const TYPES = ["travel", "event", "lifestyle"];

export default function Dashboard() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [experiences, setExperiences] = useState([]);
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [type, setType] = useState("travel");
  const [creating, setCreating] = useState(false);

  const load = async () => {
    try { const res = await api.get("/experiences"); setExperiences(res.data); } catch { /* */ }
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

  return (
    <div className="min-h-screen bg-lumiere-base">
      <Header />
      <main className="px-4 sm:px-8 py-8 max-w-6xl mx-auto">
        <div className="flex items-end justify-between mb-10">
          <div>
            <p className="label-mono mb-2">{t("studio")}</p>
            <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight text-white">
              {t("newExperience")}
            </h1>
          </div>
          <Dialog open={open} onOpenChange={setOpen}>
            <DialogTrigger asChild>
              <button data-testid="new-experience-button"
                className="inline-flex items-center gap-2 bg-lumiere-orange hover:bg-lumiere-orangeHover text-white px-5 py-3 font-mono text-xs uppercase tracking-widest transition-colors duration-300">
                <Plus size={16} /> {t("create")}
              </button>
            </DialogTrigger>
            <DialogContent className="bg-lumiere-surface border border-white/10 text-white rounded-none">
              <DialogHeader><DialogTitle className="font-display text-2xl">{t("createExperience")}</DialogTitle>
                <DialogDescription className="text-zinc-500 font-mono text-xs">{t("subtitle")}</DialogDescription></DialogHeader>
              <div className="space-y-5 pt-2">
                <div>
                  <label className="label-mono block mb-2">{t("title")}</label>
                  <Input data-testid="experience-title-input" value={title} onChange={(e) => setTitle(e.target.value)}
                    className="bg-black/40 border-white/15 rounded-none focus-visible:ring-lumiere-orange" placeholder="Coastal Road Trip" />
                </div>
                <div>
                  <label className="label-mono block mb-2">{t("type")}</label>
                  <div className="flex gap-2">
                    {TYPES.map((ty) => (
                      <button key={ty} data-testid={`type-${ty}`} onClick={() => setType(ty)}
                        className={`px-3 py-2 font-mono text-xs uppercase tracking-widest border transition-colors duration-300 ${type === ty ? "border-lumiere-orange text-lumiere-orange" : "border-white/15 text-zinc-500 hover:text-white"}`}>
                        {ty}
                      </button>
                    ))}
                  </div>
                </div>
                <button data-testid="confirm-create-button" onClick={create} disabled={creating}
                  className="w-full bg-lumiere-orange hover:bg-lumiere-orangeHover disabled:opacity-50 text-white py-3 font-mono text-xs uppercase tracking-widest transition-colors duration-300">
                  {creating ? "…" : t("create")}
                </button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {experiences.length === 0 ? (
          <div className="border border-dashed border-white/10 py-24 text-center">
            <Film size={40} className="mx-auto text-zinc-700 mb-4" />
            <p className="text-zinc-500">{t("noExperiences")}</p>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {experiences.map((exp, i) => (
              <motion.button
                key={exp.id} data-testid={`experience-card-${exp.id}`}
                initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}
                onClick={() => navigate(`/studio/${exp.id}`)}
                className="group text-left viewfinder bg-lumiere-surface border border-white/10 hover:border-white/25 p-6 transition-colors duration-300"
              >
                <span className="vf-bl" /><span className="vf-br" />
                <div className="flex items-center justify-between mb-6">
                  <span className="label-mono flex items-center gap-1"><Lock size={11} /> {t("private")}</span>
                  <ArrowUpRight size={16} className="text-zinc-600 group-hover:text-lumiere-orange transition-colors" />
                </div>
                <h3 className="font-display text-2xl font-bold text-white leading-tight">{exp.title}</h3>
                <div className="flex items-center gap-3 mt-4">
                  <span className="font-mono text-xs text-lumiere-cyan uppercase">{exp.type}</span>
                  <span className="font-mono text-xs text-zinc-600">·</span>
                  <span className="font-mono text-xs text-zinc-500">{exp.stage}</span>
                </div>
              </motion.button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
