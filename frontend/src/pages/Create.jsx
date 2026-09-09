import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Loader2, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";
import { Header } from "@/components/Header";

const TYPES = ["travel", "event", "lifestyle"];

export default function Create() {
  const navigate = useNavigate();
  const [title, setTitle] = useState("");
  const [type, setType] = useState("travel");
  const [location, setLocation] = useState("");
  const [platform, setPlatform] = useState("cinematic");
  const [creating, setCreating] = useState(false);

  const create = async () => {
    if (!title.trim()) return;
    setCreating(true);
    try {
      const res = await api.post("/experiences", { title: title.trim(), type, location_name: location.trim() || null, target_platform: platform });
      localStorage.setItem("lumiere_last_exp", res.data.id);
      navigate(`/studio/${res.data.id}`);
    } catch { toast.error("Failed to create"); }
    finally { setCreating(false); }
  };

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink">
      <Header />
      <main className="px-4 sm:px-8 lg:px-16 py-14 max-w-2xl mx-auto" data-testid="create-page">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-gold mb-3">Before · New experience</p>
        <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight leading-[0.95]">Start a new story</h1>
        <p className="mt-4 text-lumiere-ink/60">Name the experience and pick a type. Next, we'll shape the story and plan your shots.</p>

        <div className="mt-10 space-y-7 rounded-2xl border border-black/10 bg-lumiere-warm p-7">
          <div>
            <label className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50 block mb-2">Title</label>
            <input data-testid="create-title-input" value={title} onChange={(e) => setTitle(e.target.value)}
              placeholder="Coastal Road Trip"
              className="w-full bg-white border border-black/15 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-lumiere-gold" />
          </div>
          <div>
            <label className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50 block mb-2">Location <span className="opacity-50">(free text — we resolve it once)</span></label>
            <input data-testid="create-location-input" value={location} onChange={(e) => setLocation(e.target.value)}
              placeholder="Lisbon, Portugal"
              className="w-full bg-white border border-black/15 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-lumiere-gold" />
          </div>
          <div>
            <label className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50 block mb-2">Type</label>
            <div className="flex gap-2">
              {TYPES.map((ty) => (
                <button key={ty} data-testid={`create-type-${ty}`} onClick={() => setType(ty)}
                  className={`px-4 py-2 font-mono text-xs uppercase tracking-widest border rounded-full transition-colors ${type === ty ? "border-lumiere-gold bg-lumiere-gold/15 text-lumiere-ink" : "border-black/15 text-lumiere-ink/50 hover:text-lumiere-ink"}`}>
                  {ty}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50 block mb-2">Target</label>
            <div className="flex gap-2">
              {["cinematic", "social", "story"].map((pf) => (
                <button key={pf} data-testid={`create-platform-${pf}`} onClick={() => setPlatform(pf)}
                  className={`px-4 py-2 font-mono text-xs uppercase tracking-widest border rounded-full capitalize transition-colors ${platform === pf ? "border-lumiere-iris bg-lumiere-iris/15 text-lumiere-ink" : "border-black/15 text-lumiere-ink/50 hover:text-lumiere-ink"}`}>
                  {pf}
                </button>
              ))}
            </div>
          </div>
          <button data-testid="create-continue-button" onClick={create} disabled={creating || !title.trim()}
            className="w-full inline-flex items-center justify-center gap-2 bg-lumiere-gold hover:bg-lumiere-goldHover disabled:opacity-50 text-lumiere-ink py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
            {creating ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />} Continue
          </button>
        </div>
      </main>
    </div>
  );
}
