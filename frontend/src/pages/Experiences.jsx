import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Plus, ArrowUpRight, Film } from "lucide-react";
import { api } from "@/lib/api";
import { Header } from "@/components/Header";

const IMGS = {
  travel: "https://images.unsplash.com/photo-1782835576404-f5eaddd63ac3?crop=entropy&cs=srgb&fm=jpg&w=800&q=80",
  event: "https://images.unsplash.com/photo-1485846234645-a62644f84728?crop=entropy&cs=srgb&fm=jpg&w=800&q=80",
  lifestyle: "https://images.unsplash.com/photo-1782714040856-cf19b8ba888b?crop=entropy&cs=srgb&fm=jpg&w=800&q=80",
};
const PHASE_LABEL = { before: "Before", during: "During", after: "After" };
const PHASE_COLOR = {
  before: "text-lumiere-gold border-lumiere-gold/50",
  during: "text-lumiere-iris border-lumiere-iris/50",
  after: "text-lumiere-sage border-lumiere-sage/50",
};

export default function Experiences() {
  const navigate = useNavigate();
  const [experiences, setExperiences] = useState([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api.get("/experiences").then((r) => setExperiences(r.data)).catch(() => {}).finally(() => setLoaded(true));
  }, []);

  const open = (id) => { localStorage.setItem("lumiere_last_exp", id); navigate(`/studio/${id}`); };

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink">
      <Header />
      <main className="px-4 sm:px-8 lg:px-16 py-10 max-w-7xl mx-auto" data-testid="experiences-page">
        <div className="flex items-center justify-between mb-8">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-iris mb-2">Your experiences</p>
            <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight">Every story you're building</h1>
          </div>
          <button data-testid="experiences-new-button" onClick={() => navigate("/create")}
            className="inline-flex items-center gap-2 bg-lumiere-ink text-lumiere-ivory hover:bg-lumiere-ink/85 px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
            <Plus size={14} /> New experience
          </button>
        </div>

        {!loaded ? null : experiences.length === 0 ? (
          <div className="border border-dashed border-black/15 rounded-2xl py-24 text-center" data-testid="experiences-empty">
            <Film size={36} className="mx-auto text-lumiere-ink/30 mb-3" />
            <p className="text-lumiere-ink/50">No experiences yet. Create your first story.</p>
            <button data-testid="experiences-empty-create" onClick={() => navigate("/create")}
              className="mt-5 inline-flex items-center gap-2 bg-lumiere-gold hover:bg-lumiere-goldHover text-lumiere-ink px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              <Plus size={14} /> Create my story
            </button>
          </div>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="experiences-grid">
            {experiences.map((exp, i) => (
              <motion.button key={exp.id} data-testid={`experience-card-${exp.id}`}
                initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04 }}
                onClick={() => open(exp.id)}
                className="group text-left rounded-2xl overflow-hidden border border-black/10 hover:border-lumiere-gold/60 transition-colors bg-lumiere-warm">
                <div className="relative h-40 overflow-hidden">
                  <img src={IMGS[exp.type] || IMGS.travel} alt="" className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
                  {exp.phase && (
                    <span className={`absolute top-2 left-2 font-mono text-[0.55rem] uppercase tracking-widest border rounded-full px-2 py-0.5 bg-lumiere-warm ${PHASE_COLOR[exp.phase] || ""}`}>
                      {PHASE_LABEL[exp.phase] || exp.phase}
                    </span>
                  )}
                </div>
                <div className="p-5">
                  <div className="flex items-center justify-between">
                    <h3 className="font-display text-xl font-bold">{exp.title}</h3>
                    <ArrowUpRight size={16} className="text-lumiere-ink/30 group-hover:text-lumiere-gold transition-colors" />
                  </div>
                  <p className="font-mono text-xs text-lumiere-ink/50 mt-1 uppercase">{exp.type} · {exp.stage || exp.status || ""}</p>
                </div>
              </motion.button>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
