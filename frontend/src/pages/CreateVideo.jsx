import { useEffect, useState, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, Lock, Loader2, Film, AlertCircle, Trash2, Wand2 } from "lucide-react";
import { toast } from "sonner";
import { api, API, getToken } from "@/lib/api";
import { useI18n } from "@/i18n";
import { Header } from "@/components/Header";
import { VideoEditor } from "@/components/VideoEditor";

const g = (o, lang) => (o ? o[lang] : "");
const ASPECTS = ["16:9", "9:16"];
const DURATIONS = [4, 6, 8];

const T = {
  title: { en: "AI Video Generation", es: "Generación de Video con IA" },
  sub: { en: "Generate cinematic video from a prompt with Vertex AI (Veo).", es: "Genera video cinematográfico desde un prompt con Vertex AI (Veo)." },
  prompt: { en: "Describe your shot", es: "Describe tu toma" },
  ph: { en: "Aerial dawn over a misty coastline, warm golden light, slow cinematic push-in", es: "Amanecer aéreo sobre una costa con niebla, luz dorada cálida, push-in cinematográfico lento" },
  aspect: { en: "Aspect ratio", es: "Relación de aspecto" },
  dur: { en: "Duration", es: "Duración" },
  gen: { en: "Generate", es: "Generar" },
  generating: { en: "Submitting…", es: "Enviando…" },
  myGen: { en: "My generations", es: "Mis generaciones" },
  none: { en: "No generations yet.", es: "Aún no hay generaciones." },
  quota: { en: "Monthly quota", es: "Cuota mensual" },
  lockedTitle: { en: "AI Video is a Creator feature", es: "El Video IA es una función de Creator" },
  lockedSub: { en: "Upgrade to Creator or Studio to generate real cinematic video with Vertex Veo.", es: "Mejora a Creator o Studio para generar video cinematográfico real con Vertex Veo." },
  upgrade: { en: "Upgrade plan", es: "Mejorar plan" },
  quotaExceeded: { en: "Monthly quota reached — upgrade for more.", es: "Cuota mensual alcanzada — mejora para más." },
  running: { en: "Generating", es: "Generando" },
  done: { en: "Ready", es: "Listo" },
  failed: { en: "Failed", es: "Falló" },
};

export default function CreateVideo() {
  const { lang } = useI18n();
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const [prompt, setPrompt] = useState("");
  const [aspect, setAspect] = useState("16:9");
  const [duration, setDuration] = useState(8);
  const [busy, setBusy] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [editing, setEditing] = useState(null);
  const pollRef = useRef(null);

  const loadAccount = async () => { try { const r = await api.get("/account"); setAccount(r.data); } catch { /* */ } };
  const loadJobs = useCallback(async () => {
    try { const r = await api.get("/video/jobs"); setJobs(r.data); } catch { /* */ }
  }, []);

  useEffect(() => { loadAccount(); loadJobs(); }, [loadJobs]);
  useEffect(() => {
    pollRef.current = setInterval(loadJobs, 10000);
    return () => clearInterval(pollRef.current);
  }, [loadJobs]);

  const entitled = account?.entitlements?.video;
  const used = account?.usage?.ai_generations ?? 0;
  const limit = account?.limits?.ai_generations ?? 0;

  const generate = async () => {
    if (!prompt.trim()) return;
    setBusy(true);
    try {
      const r = await api.post("/video/generate", { prompt: prompt.trim(), aspect_ratio: aspect, duration_sec: duration });
      setJobs((j) => [r.data, ...j]);
      setPrompt("");
      toast.success(g(T.running, lang));
      loadAccount();
    } catch (e) {
      const d = e?.response?.data?.detail;
      if (d === "quota_exceeded") toast.error(g(T.quotaExceeded, lang));
      else if (d === "video_not_entitled") toast.error(g(T.lockedTitle, lang));
      else toast.error("Failed");
    } finally { setBusy(false); }
  };

  const videoSrc = (job) => `${API}/video/${job.id}/download?auth=${encodeURIComponent(getToken() || "")}`;

  const deleteJob = async (jobId) => {
    try {
      await api.delete(`/video/jobs/${jobId}`);
      setJobs((j) => j.filter((x) => x.id !== jobId));
      toast.success(lang === "es" ? "Video eliminado" : "Video deleted");
    } catch { toast.error("Failed"); }
  };

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink">
      <Header back />
      <main className="px-4 sm:px-8 lg:px-16 py-10 max-w-6xl mx-auto" data-testid="create-video-page">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-iris mb-2">{g(T.title, lang)}</p>
        <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight">{g(T.sub, lang)}</h1>

        {!account ? (
          <div className="mt-10"><Loader2 className="animate-spin text-lumiere-iris" /></div>
        ) : !entitled ? (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="mt-10 rounded-2xl border border-lumiere-iris/40 bg-lumiere-iris/5 p-10 text-center max-w-xl" data-testid="video-locked">
            <Lock size={32} className="mx-auto text-lumiere-iris mb-4" />
            <h2 className="font-display text-2xl">{g(T.lockedTitle, lang)}</h2>
            <p className="text-lumiere-ink/60 mt-3">{g(T.lockedSub, lang)}</p>
            <button data-testid="video-upgrade-button" onClick={() => navigate("/pricing")}
              className="mt-6 inline-flex items-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover text-white px-6 py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              <Sparkles size={14} /> {g(T.upgrade, lang)}
            </button>
          </motion.div>
        ) : (
          <>
            <div className="mt-8 grid lg:grid-cols-2 gap-8">
              <div className="rounded-2xl border border-lumiere-ink/10 bg-lumiere-warm p-6 space-y-5">
                <div>
                  <label className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50 block mb-2">{g(T.prompt, lang)}</label>
                  <textarea data-testid="video-prompt-input" value={prompt} onChange={(e) => setPrompt(e.target.value)} rows={4}
                    placeholder={g(T.ph, lang)}
                    className="w-full bg-white border border-lumiere-ink/15 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-lumiere-iris resize-none" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50 block mb-2">{g(T.aspect, lang)}</label>
                    <div className="flex gap-2">
                      {ASPECTS.map((a) => (
                        <button key={a} data-testid={`aspect-${a}`} onClick={() => setAspect(a)}
                          className={`px-4 py-2 rounded-full font-mono text-xs border transition-colors ${aspect === a ? "border-lumiere-iris bg-lumiere-iris/10 text-lumiere-ink" : "border-lumiere-ink/15 text-lumiere-ink/50"}`}>{a}</button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <label className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50 block mb-2">{g(T.dur, lang)}</label>
                    <div className="flex gap-2">
                      {DURATIONS.map((d) => (
                        <button key={d} data-testid={`duration-${d}`} onClick={() => setDuration(d)}
                          className={`px-4 py-2 rounded-full font-mono text-xs border transition-colors ${duration === d ? "border-lumiere-iris bg-lumiere-iris/10 text-lumiere-ink" : "border-lumiere-ink/15 text-lumiere-ink/50"}`}>{d}s</button>
                      ))}
                    </div>
                  </div>
                </div>
                <button data-testid="video-generate-button" onClick={generate} disabled={busy || !prompt.trim()}
                  className="w-full inline-flex items-center justify-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover disabled:opacity-50 text-white py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors shadow-[0_0_20px_rgba(114,103,168,0.35)]">
                  {busy ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} {busy ? g(T.generating, lang) : g(T.gen, lang)}
                </button>
              </div>

              <div className="rounded-2xl border border-lumiere-ink/10 bg-lumiere-warm p-6">
                <p className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50 mb-2">{g(T.quota, lang)}</p>
                <div className="flex items-end gap-2">
                  <span className="font-mono text-3xl">{used}</span><span className="font-mono text-lumiere-ink/40 mb-1">/ {limit}</span>
                </div>
                <div className="h-1.5 bg-black/10 rounded-full overflow-hidden mt-3">
                  <div className="h-full bg-lumiere-iris rounded-full" style={{ width: `${Math.min(100, (used / (limit || 1)) * 100)}%`, transition: "width 0.6s ease" }} />
                </div>
                <p className="text-sm text-lumiere-ink/50 mt-4">{account.plan?.name}</p>
              </div>
            </div>

            <div className="mt-12">
              <p className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50 mb-4">{g(T.myGen, lang)}</p>
              {jobs.length === 0 ? (
                <div className="border border-dashed border-lumiere-ink/15 rounded-2xl py-16 text-center">
                  <Film size={32} className="mx-auto text-lumiere-ink/30 mb-2" />
                  <p className="text-lumiere-ink/50">{g(T.none, lang)}</p>
                </div>
              ) : (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="video-jobs-list">
                  {jobs.map((j) => (
                    <div key={j.id} data-testid={`video-job-${j.id}`} className="rounded-2xl border border-lumiere-ink/10 bg-black overflow-hidden">
                      <div className="aspect-video bg-lumiere-ink flex items-center justify-center relative">
                        {j.status === "DONE" ? (
                          <>
                            <video src={videoSrc(j)} controls className="w-full h-full object-contain" data-testid={`video-player-${j.id}`} />
                            <button data-testid={`video-edit-overlay-${j.id}`} onClick={() => setEditing(j)}
                              className="absolute top-2 right-2 inline-flex items-center gap-1.5 bg-lumiere-iris/90 hover:bg-lumiere-iris text-white px-3 py-1.5 rounded-full font-mono text-[0.6rem] uppercase tracking-widest shadow-lg backdrop-blur transition-colors">
                              <Wand2 size={12} /> {lang === "es" ? "Editar" : "Edit"}
                            </button>
                          </>
                        ) : j.status === "FAILED" ? (
                          <div className="text-center text-red-400"><AlertCircle size={24} className="mx-auto mb-1" /><span className="font-mono text-xs">{g(T.failed, lang)}</span></div>
                        ) : (
                          <div className="text-center text-lumiere-iris"><Loader2 size={24} className="mx-auto mb-1 animate-spin" /><span className="font-mono text-xs uppercase tracking-widest">{g(T.running, lang)}</span></div>
                        )}
                      </div>
                      <div className="p-3 bg-lumiere-warm flex items-start justify-between gap-2">
                        <div className="min-w-0">
                          <p className="text-xs text-lumiere-ink/70 line-clamp-2">{j.prompt}</p>
                          <p className="font-mono text-[0.6rem] text-lumiere-ink/40 mt-1 uppercase">{j.options?.aspect_ratio} · {j.options?.duration_sec}s</p>
                        </div>
                        <button data-testid={`video-delete-${j.id}`} onClick={() => deleteJob(j.id)}
                          title={lang === "es" ? "Eliminar video" : "Delete video"}
                          className="text-lumiere-ink/40 hover:text-red-600 transition-colors shrink-0"><Trash2 size={15} /></button>
                      </div>
                      {j.status === "DONE" && (
                        <button data-testid={`video-edit-${j.id}`} onClick={() => setEditing(j)}
                          className="w-full inline-flex items-center justify-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover text-white py-3 font-mono text-xs uppercase tracking-widest transition-colors shadow-[0_0_20px_rgba(114,103,168,0.35)]">
                          <Wand2 size={15} /> {lang === "es" ? "Editar Pro · Formato, filtros y logo" : "Pro Edit · Format, filters & logo"}
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </main>
      {editing && (
        <VideoEditor job={editing} lang={lang}
          onClose={() => setEditing(null)}
          onDone={(newJob) => { setJobs((j) => [newJob, ...j]); loadAccount(); }} />
      )}
    </div>
  );
}
