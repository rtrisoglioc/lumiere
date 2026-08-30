import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, Loader2, Info, Wand2 } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { useI18n } from "@/i18n";
import { Header } from "@/components/Header";

const RATIOS = ["16:9", "9:16", "1:1", "2.39:1"];
const STYLES = ["cinematic", "documentary", "editorial", "dreamy"];
const DURATIONS = [4, 6, 8];

export default function CreateVideo() {
  const { t, lang } = useI18n();
  const [prompt, setPrompt] = useState("");
  const [ratio, setRatio] = useState("16:9");
  const [style, setStyle] = useState("cinematic");
  const [duration, setDuration] = useState(6);
  const [busy, setBusy] = useState(false);
  const [health, setHealth] = useState(null);
  const [jobs, setJobs] = useState([]);

  const loadJobs = async () => { try { const r = await api.get("/video/jobs"); setJobs(r.data); } catch { /* */ } };
  useEffect(() => {
    api.get("/video/health").then((r) => setHealth(r.data)).catch(() => {});
    loadJobs();
  }, []);

  const generate = async () => {
    if (!prompt.trim()) return;
    setBusy(true);
    try {
      await api.post("/video/generate", { prompt: prompt.trim(), aspect_ratio: ratio, style, duration_sec: duration });
      toast(t("veoPending"));
      setPrompt("");
      await loadJobs();
    } catch { toast.error("Failed"); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink">
      <Header back />
      <main className="px-4 sm:px-8 lg:px-16 py-12 max-w-4xl mx-auto space-y-8" data-testid="create-video-page">
        <div>
          <p className="label-mono text-lumiere-iris mb-2 flex items-center gap-2"><Sparkles size={13} /> {t("aiVideoGen")}</p>
          <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight">{t("createVideo")}</h1>
          <p className="mt-3 text-lumiere-ink/60">{t("aiVideoSub")}</p>
        </div>

        {/* Vertex not connected banner */}
        {health && !health.connected && (
          <div className="rounded-2xl border border-lumiere-iris/40 bg-lumiere-iris/5 p-4 flex items-start gap-3" data-testid="veo-not-connected">
            <Info size={18} className="text-lumiere-iris mt-0.5 shrink-0" />
            <div>
              <p className="font-display text-base">{t("aiNotConnectedTitle")}</p>
              <p className="text-sm text-lumiere-ink/60 mt-0.5">{lang === "es" ? health.note_es : health.note_en}</p>
            </div>
          </div>
        )}

        <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-6 space-y-5">
          <div>
            <label className="label-mono block mb-2 text-lumiere-ink/60">{t("promptLabel")}</label>
            <textarea data-testid="video-prompt" value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4}
              placeholder={t("promptPlaceholder")}
              className="w-full bg-white border border-black/15 focus:border-lumiere-iris outline-none rounded-lg p-4 resize-none transition-colors" />
          </div>
          <div className="grid sm:grid-cols-3 gap-4">
            <Control label={t("aspectRatio")} options={RATIOS} value={ratio} onChange={setRatio} testid="ratio" />
            <Control label={t("styleLabel")} options={STYLES} value={style} onChange={setStyle} testid="style" />
            <Control label={t("durationLabel")} options={DURATIONS} value={duration} onChange={setDuration} testid="duration" suffix="s" />
          </div>
          <button data-testid="generate-video-button" onClick={generate} disabled={busy || !prompt.trim()}
            className="inline-flex items-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover disabled:opacity-50 text-white px-6 py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors shadow-[0_0_15px_rgba(114,103,168,0.4)]">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} {t("generate")}
          </button>
        </div>

        {/* AI Enhance own video (pending) */}
        <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-6">
          <p className="label-mono text-lumiere-iris mb-2 flex items-center gap-2"><Wand2 size={13} /> {t("aiEnhance")}</p>
          <p className="text-sm text-lumiere-ink/60">{lang === "es" ? "Mejora o edita tus propios videos con IA (Vertex/Veo). Disponible al conectar GCP." : "Enhance or edit your own videos with AI (Vertex/Veo). Available once GCP is connected."}</p>
        </div>

        {/* jobs */}
        <div>
          <p className="label-mono text-lumiere-ink/50 mb-3">{t("myGenerations")}</p>
          {jobs.length === 0 ? (
            <p className="text-lumiere-ink/50 text-sm">{t("noGenerations")}</p>
          ) : (
            <div className="space-y-2">
              {jobs.map((j) => (
                <motion.div key={j.id} data-testid={`job-${j.id}`} initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="rounded-xl border border-black/10 bg-lumiere-warm p-4 flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <p className="text-sm truncate">{j.prompt || j.asset_id}</p>
                    <p className="font-mono text-[0.6rem] text-lumiere-ink/40 uppercase mt-0.5">{j.kind} · {j.options?.aspect_ratio || ""} · {j.options?.style || ""}</p>
                  </div>
                  <span className="font-mono text-[0.6rem] uppercase tracking-widest px-2 py-1 rounded-full border border-lumiere-iris/40 text-lumiere-iris shrink-0">{t("veoPending")}</span>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

function Control({ label, options, value, onChange, testid, suffix = "" }) {
  return (
    <div>
      <label className="label-mono block mb-2 text-lumiere-ink/60">{label}</label>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button key={o} data-testid={`${testid}-${o}`} onClick={() => onChange(o)}
            className={`px-3 py-1.5 font-mono text-xs rounded-full border transition-colors ${value === o ? "border-lumiere-iris bg-lumiere-iris/10 text-lumiere-ink" : "border-black/15 text-lumiere-ink/50 hover:text-lumiere-ink"}`}>
            {o}{suffix}
          </button>
        ))}
      </div>
    </div>
  );
}
