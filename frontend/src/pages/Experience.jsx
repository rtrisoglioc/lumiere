import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "react-router-dom";
import { motion } from "framer-motion";
import {
  Loader2, Upload, Sparkles, Film, Wand2, ArrowRight, Check, SkipForward,
  Clock, MapPin, AlertTriangle, Camera, RefreshCw, ChevronRight, Activity, Share2, Copy, Trash2, Pencil, X, Sliders,
} from "lucide-react";
import { toast } from "sonner";
import { api, API, getToken } from "@/lib/api";
import { useI18n } from "@/i18n";
import { Header } from "@/components/Header";
import { PhaseIndicator } from "@/components/PhaseIndicator";
import { CircularScore } from "@/components/CircularScore";

const MOODS = ["curious", "free", "elegant", "warm", "energetic", "intimate", "nostalgic", "bold"];
const PRESENCE = ["none", "minimal", "balanced", "protagonist"];
const STYLES = ["cinematic", "social", "story"];
const EDIT_ASPECTS = [["16:9", "16:9"], ["9:16", "9:16"], ["1:1", "1:1"]];
const EDIT_LOOKS = ["none", "cinematic", "warm", "cool", "bw", "vivid"];
const EDIT_SPEEDS = [[0.5, "0.5×"], [1, "1×"], [1.5, "1.5×"], [2, "2×"]];
const EDIT_SCENE_TR = ["dissolve", "fade", "fadeblack", "cut"];
const EDIT_END_FADE = ["none", "fade", "fadeblack", "fadewhite"];
const EDIT_TEXT_POS = ["top", "center", "bottom"];
const EDIT_TEXT_SZ = ["small", "medium", "large"];
const g = (v) => (v && typeof v === "object" ? v.en || v.es || "" : v || "");
const WIN_LABEL = {
  golden_hour_am: { en: "Golden hour · AM", es: "Hora dorada · mañana" },
  golden_hour_pm: { en: "Golden hour · PM", es: "Hora dorada · tarde" },
  morning: { en: "Morning", es: "Mañana" },
  midday: { en: "Midday", es: "Mediodía" },
  afternoon: { en: "Afternoon", es: "Tarde" },
  blue_hour: { en: "Blue hour", es: "Hora azul" },
  night: { en: "Night", es: "Noche" },
  any: { en: "Any time", es: "Cualquier hora" },
};
const winLabel = (w, lang) => { const k = (w || "").toLowerCase(); return WIN_LABEL[k] ? (lang === "es" ? WIN_LABEL[k].es : WIN_LABEL[k].en) : (w || ""); };
const cov = { covered: "text-lumiere-sage border-lumiere-sage/50", partial: "text-lumiere-gold border-lumiere-gold/50", empty: "text-lumiere-ink/40 border-lumiere-ink/15" };

export default function Experience() {
  const { id } = useParams();
  const { lang } = useI18n();
  const s = (en, es) => (lang === "es" ? es : en);
  const [state, setState] = useState(null);
  const [busy, setBusy] = useState("");
  const [tab, setTab] = useState(null);
  const fileRef = useRef();
  const [revText, setRevText] = useState("");
  const [trace, setTrace] = useState(null);
  const [demo, setDemo] = useState(false);
  const [previz, setPreviz] = useState({});
  const [shared, setShared] = useState({});
  const EDIT_DEFAULTS = { aspect: "16:9", look: "none", speed: 1, scene_transition: "dissolve", end_fade: "none", text_enabled: false, text_content: "", text_position: "bottom", text_size: "medium" };
  const [editCutId, setEditCutId] = useState(null);
  const [editOpts, setEditOpts] = useState(EDIT_DEFAULTS);
  const [editBusy, setEditBusy] = useState(false);
  const openEditor = (cut) => { setEditCutId(cut.cut_id); setEditOpts({ ...EDIT_DEFAULTS, text_content: (story?.title || "") }); };
  const applyEdit = async () => {
    setEditBusy(true);
    try {
      await api.post(`/v2/cuts/${editCutId}/edit`, editOpts);
      setEditCutId(null); await load();
      toast.success(lang === "es" ? "Nueva versión creada" : "New version created");
    } catch { toast.error(lang === "es" ? "Falló la edición" : "Edit failed"); }
    finally { setEditBusy(false); }
  };

  // intent form
  const [feelings, setFeelings] = useState([]);
  const [freeText, setFreeText] = useState("");
  const [presence, setPresence] = useState("balanced");
  const [ideas, setIdeas] = useState([]);

  const load = useCallback(async () => {
    try {
      const r = await api.get(`/v2/experiences/${id}/state`);
      setState(r.data);
      if (tab === null) setTab(r.data.experience?.phase || "before");
      localStorage.setItem("lumiere_last_exp", id);
    } catch { toast.error("Failed to load"); }
  }, [id, tab]);
  useEffect(() => { load(); }, [id]); // eslint-disable-line
  useEffect(() => { api.get(`/v2/demo/config`).then((r) => setDemo(r.data.demo_mode)).catch(() => {}); }, []);

  const demoLoad = async () => { setBusy("demoload"); try { const r = await api.post(`/v2/experiences/${id}/demo/load-footage`); if (r.data.ok) { await load(); setTab("after"); toast.success(`Loaded ${r.data.loaded} demo clip(s)`); } else { toast.info(r.data.message || "No demo clips available yet"); } } catch { toast.error("Failed"); } finally { setBusy(""); } };
  const demoReset = async () => { setBusy("demoreset"); try { await api.post(`/v2/experiences/${id}/demo/reset`); await load(); toast.success("Demo reset"); } catch { toast.error("Failed"); } finally { setBusy(""); } };

  const exp = state?.experience;
  const story = state?.story;
  const beats = state?.beats || [];
  const shots = state?.shots || [];
  const assets = state?.assets || [];
  const gaps = state?.gaps || [];
  const cuts = state?.cuts || [];
  const c = state?.completeness;

  const doIntentStory = async () => {
    if (feelings.length === 0) { toast.error("Pick at least one mood"); return; }
    setBusy("story");
    try {
      await api.post(`/v2/experiences/${id}/intent`, { feeling_tags: feelings, free_text: freeText, creator_presence: presence });
    } catch { toast.error("Couldn't save your intent — please try again"); setBusy(""); return; }
    try {
      await api.post(`/v2/experiences/${id}/story`);
    } catch { toast.error("Story generation failed — please try again"); await load(); setBusy(""); return; }
    await load();  // story + beats are saved and now visible even if shots lag
    toast.success("Story ready");
    try {
      await api.post(`/v2/experiences/${id}/shots`);
      await load();
    } catch { toast.warning("Shot list didn't finish — tap ↻ to retry"); }
    setBusy("");
  };

  const genShots = async () => { setBusy("shots"); try { await api.post(`/v2/experiences/${id}/shots`); await load(); toast.success("Shots ready"); } catch { toast.error("Failed"); } finally { setBusy(""); } };

  const suggestIdeas = async () => { setBusy("ideas"); try { const r = await api.post(`/v2/experiences/${id}/story-ideas`); setIdeas(r.data.ideas || []); if (!r.data.ideas?.length) toast.info("No ideas — try again"); } catch { toast.error("Couldn't fetch ideas"); } finally { setBusy(""); } };
  const applyIdea = (idea) => { setFeelings((idea.feeling_tags || []).slice(0, 3)); setFreeText(idea.free_text || ""); toast.success("Idea applied — tweak or create"); };
  const deleteShot = async (shotId) => { try { await api.delete(`/v2/shots/${shotId}`); await load(); toast.success("Shot removed"); } catch { toast.error("Couldn't remove shot"); } };

  const [editingBeat, setEditingBeat] = useState(null);
  const [beatDraft, setBeatDraft] = useState({ label: "", purpose: "" });
  const startEditBeat = (b) => { setEditingBeat(b.beat_id); setBeatDraft({ label: g(b.label), purpose: g(b.purpose) }); };
  const saveBeat = async () => { try { await api.patch(`/v2/beats/${editingBeat}`, beatDraft); setEditingBeat(null); await load(); toast.success(s("Saved", "Guardado")); } catch { toast.error(s("Save failed", "No se pudo guardar")); } };
  const deleteBeat = async (bid) => { try { await api.delete(`/v2/beats/${bid}`); await load(); toast.success(s("Beat removed", "Beat eliminado")); } catch { toast.error("Error"); } };
  const translateStory = async (to) => { setBusy("translate"); try { await api.post(`/v2/experiences/${id}/translate?to=${to}`); await load(); toast.success(s("Translated", "Traducido")); } catch { toast.error(s("Translation failed", "Falló la traducción")); } finally { setBusy(""); } };

  const [editingShot, setEditingShot] = useState(null);
  const [shotDraft, setShotDraft] = useState("");
  const startEditShot = (sh) => { setEditingShot(sh.shot_id); setShotDraft(g(sh.action)); };
  const saveShot = async () => { try { await api.patch(`/v2/shots/${editingShot}`, { action: shotDraft }); setEditingShot(null); await load(); toast.success(s("Saved", "Guardado")); } catch { toast.error(s("Save failed", "No se pudo guardar")); } };
  const [regenShotId, setRegenShotId] = useState(null);
  const regenShot = async (shotId) => { setRegenShotId(shotId); try { await api.post(`/v2/shots/${shotId}/regenerate`); await load(); toast.success(s("New shot generated", "Nueva toma generada")); } catch { toast.error(s("Couldn't regenerate", "No se pudo regenerar")); } finally { setRegenShotId(null); } };

  const upload = async (files) => {
    if (!files?.length) return;
    setBusy("upload");
    try {
      for (const f of files) { const fd = new FormData(); fd.append("file", f); await api.post(`/v2/experiences/${id}/upload`, fd, { headers: { "Content-Type": "multipart/form-data" } }); }
      await load(); toast.success(`${files.length} clip(s) uploaded`);
    } catch { toast.error("Upload failed"); } finally { setBusy(""); }
  };

  const analyze = async () => { setBusy("analyze"); try { const r = await api.post(`/v2/experiences/${id}/analyze`); await load(); setTab("after"); toast.success(`Story completeness: ${r.data.completeness.score}`); } catch { toast.error("Analysis failed"); } finally { setBusy(""); } };

  const deleteAsset = async (assetId) => { try { await api.delete(`/v2/experiences/${id}/assets/${assetId}`); await load(); toast.success("Clip removed"); } catch { toast.error("Couldn't remove clip"); } };

  const getTheShot = async (gapId) => { setBusy("gap"); try { await api.post(`/v2/gaps/${gapId}/mission`); await load(); setTab("during"); toast("Go get the shot — back to directing", { icon: "🎬" }); } catch { toast.error("Failed"); } finally { setBusy(""); } };

  const setShot = async (shotId, status, reason) => {
    try { const r = await api.post(`/v2/shots/${shotId}/status`, { status, skip_reason: reason }); await load();
      if (r.data.alternative) toast("No problem. Here's another way to tell that part.", { icon: "↻" });
    } catch { toast.error("Failed"); }
  };

  const build = async (style) => { setBusy("build"); try { await api.post(`/v2/experiences/${id}/build`, { style }); await load(); toast.success("Film rendered"); } catch (e) { toast.error("Render failed"); } finally { setBusy(""); } };

  const revise = async (cutId) => { if (!revText.trim()) return; setBusy("revise"); try { await api.post(`/v2/cuts/${cutId}/revise`, { instruction: revText.trim() }); setRevText(""); await load(); toast.success("New version created"); } catch { toast.error("Revision failed"); } finally { setBusy(""); } };

  const loadTrace = async () => { try { const r = await api.get(`/v2/experiences/${id}/trace`); setTrace(r.data); } catch { /* */ } };

  const doPreviz = async (shotId) => {
    setPreviz((p) => ({ ...p, [shotId]: { loading: true } }));
    try { const r = await api.post(`/v2/shots/${shotId}/previz`); setPreviz((p) => ({ ...p, [shotId]: r.data })); }
    catch { setPreviz((p) => ({ ...p, [shotId]: { degraded: true, caption: "This is the shot. Go get the real one." } })); }
  };

  const doShare = async (cutId) => {
    setBusy("share");
    try {
      const r = await api.post(`/v2/cuts/${cutId}/share`);
      const url = `${window.location.origin}/share/${r.data.share_id}`;
      setShared((s) => ({ ...s, [cutId]: url }));
      try { await navigator.clipboard.writeText(url); toast.success("Public link copied"); } catch { toast.success("Public link ready"); }
    } catch { toast.error("Share failed"); } finally { setBusy(""); }
  };

  const fileUrl = (path) => `${API}/files/${path}?auth=${encodeURIComponent(getToken() || "")}`;

  if (!state) return <div className="min-h-screen bg-lumiere-ivory flex items-center justify-center"><Loader2 className="animate-spin text-lumiere-gold" /></div>;

  const Tab = ({ k, label }) => (
    <button data-testid={`tab-${k}`} onClick={() => setTab(k)}
      className={`px-4 py-2 rounded-full font-mono text-[0.65rem] uppercase tracking-widest transition-colors ${tab === k ? "bg-lumiere-ink text-lumiere-ivory" : "text-lumiere-ink/50 hover:text-lumiere-ink border border-lumiere-ink/15"}`}>{label}</button>
  );

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink">
      <Header back />
      <div className="sticky top-[64px] z-30 bg-lumiere-ivory/90 backdrop-blur border-b border-black/5 px-4 sm:px-8 py-3 flex flex-wrap items-center justify-between gap-3">
        <PhaseIndicator phase={exp?.phase || "before"} />
        <div className="flex items-center gap-2">
          {demo && <button data-testid="demo-reset" onClick={demoReset} disabled={busy === "demoreset"} className="inline-flex items-center gap-1.5 border border-lumiere-iris/40 text-lumiere-iris hover:bg-lumiere-iris/10 px-3 py-1.5 rounded-full font-mono text-[0.55rem] uppercase tracking-widest transition-colors">{busy === "demoreset" ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />} {s("Reset demo", "Reiniciar demo")}</button>}
          <Tab k="before" label={s("Before", "Antes")} /><Tab k="during" label={s("During", "Durante")} /><Tab k="after" label={s("After", "Después")} />
        </div>
      </div>

      <main className="px-4 sm:px-8 lg:px-16 py-8 max-w-6xl mx-auto" data-testid="experience-workspace">
        <div className="flex items-baseline justify-between mb-6">
          <div>
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-iris">{exp?.type} · {exp?.location_name || "—"}</p>
            <h1 className="font-display text-3xl sm:text-4xl font-black">{g(story?.title) || exp?.title}</h1>
            {story?.premise && <p className="text-lumiere-ink/60 mt-2 max-w-2xl">{g(story.premise)}</p>}
          </div>
        </div>

        {/* ---------------- BEFORE ---------------- */}
        {tab === "before" && (
          <div data-testid="phase-before-content" className="space-y-8">
            {!story ? (
              <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-7 max-w-2xl" data-testid="intent-form">
                <p className="font-mono text-xs uppercase tracking-widest text-lumiere-gold mb-1">{s("Story Intent", "Intención de la historia")}</p>
                <h2 className="font-display text-2xl mb-4">{s("What do you want this experience to feel like?", "¿Qué quieres que transmita esta experiencia?")}</h2>
                <button data-testid="suggest-ideas" onClick={suggestIdeas} disabled={busy === "ideas"}
                  className="mb-4 inline-flex items-center gap-2 border border-lumiere-iris/40 text-lumiere-iris hover:bg-lumiere-iris/10 px-4 py-2 rounded-full font-mono text-[0.6rem] uppercase tracking-widest transition-colors">
                  {busy === "ideas" ? <Loader2 size={13} className="animate-spin" /> : <Wand2 size={13} />} {s("Suggest ideas with AI", "Sugerir ideas con IA")}
                </button>
                {ideas.length > 0 && (
                  <div className="space-y-2 mb-5" data-testid="ideas-list">
                    {ideas.map((idea, i) => (
                      <button key={i} data-testid={`idea-${i}`} onClick={() => applyIdea(idea)}
                        className="w-full text-left rounded-xl border border-lumiere-iris/25 bg-lumiere-iris/5 hover:bg-lumiere-iris/10 p-3 transition-colors">
                        <span className="font-display text-base">{g(idea.title)}</span>
                        <span className="block text-xs text-lumiere-ink/55 mt-0.5">{g(idea.free_text)}</span>
                        <span className="block font-mono text-[0.5rem] uppercase tracking-widest text-lumiere-iris mt-1">{(idea.feeling_tags || []).join(" · ")}</span>
                      </button>
                    ))}
                  </div>
                )}
                <div className="flex flex-wrap gap-2 mb-5">
                  {MOODS.map((m) => (
                    <button key={m} data-testid={`mood-${m}`} onClick={() => setFeelings((f) => f.includes(m) ? f.filter((x) => x !== m) : f.length < 3 ? [...f, m] : f)}
                      className={`px-3.5 py-1.5 rounded-full font-mono text-[0.65rem] uppercase tracking-widest border transition-colors ${feelings.includes(m) ? "bg-lumiere-gold border-lumiere-gold text-lumiere-ink" : "border-black/15 text-lumiere-ink/60 hover:border-lumiere-gold"}`}>{lang === "es" ? { curious: "Curiosa", free: "Libre", elegant: "Elegante", warm: "Cálida", energetic: "Enérgica", intimate: "Íntima", nostalgic: "Nostálgica", bold: "Audaz" }[m] : m}</button>
                  ))}
                </div>
                <textarea data-testid="intent-freetext" value={freeText} onChange={(e) => setFreeText(e.target.value)} rows={2} placeholder={s("Optional: a sentence about the story you want…", "Opcional: una frase sobre la historia que quieres…")}
                  className="w-full bg-white border border-black/15 rounded-lg p-3 text-sm focus:outline-none focus:ring-2 focus:ring-lumiere-gold resize-none mb-4" />
                <div className="mb-5">
                  <label className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50 block mb-2">{s("Creator presence", "Presencia del creador")}</label>
                  <div className="flex gap-2">
                    {PRESENCE.map((p) => (
                      <button key={p} data-testid={`presence-${p}`} onClick={() => setPresence(p)}
                        className={`px-3 py-1.5 rounded-full font-mono text-[0.6rem] uppercase tracking-widest border capitalize transition-colors ${presence === p ? "bg-lumiere-iris border-lumiere-iris text-white" : "border-black/15 text-lumiere-ink/60"}`}>{lang === "es" ? { none: "Ninguna", minimal: "Mínima", balanced: "Equilibrada", protagonist: "Protagonista" }[p] : p}</button>
                    ))}
                  </div>
                </div>
                <button data-testid="create-story-button" onClick={doIntentStory} disabled={busy === "story"}
                  className="inline-flex items-center gap-2 bg-lumiere-ink text-lumiere-ivory hover:bg-lumiere-ink/85 disabled:opacity-50 px-6 py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
                  {busy === "story" ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />} {s("Create my story", "Crear mi historia")}
                </button>
                {busy === "story" && <p className="text-sm text-lumiere-ink/50 mt-3 animate-pulse">{s("Understanding your intent… Building the arc… Planning the moments…", "Entendiendo tu intención… Construyendo el arco… Planeando los momentos…")}</p>}
              </div>
            ) : (
              <>
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <p className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50">{s("Story arc", "Arco narrativo")} · {beats.length} {s("beats", "beats")}</p>
                    <button data-testid="translate-story" onClick={() => translateStory(lang === "en" ? "es" : "en")} disabled={busy === "translate"}
                      className="inline-flex items-center gap-1.5 border border-lumiere-ink/20 hover:border-lumiere-gold px-3 py-1 rounded-full font-mono text-[0.55rem] uppercase tracking-widest transition-colors">
                      {busy === "translate" ? <Loader2 size={11} className="animate-spin" /> : <Wand2 size={11} />} {lang === "en" ? "Translate to Spanish" : "Traducir al inglés"}
                    </button>
                  </div>
                  <div className="flex gap-3 overflow-x-auto pb-3" data-testid="beats-strip">
                    {beats.map((b) => (
                      <div key={b.beat_id} data-testid={`beat-${b.sequence}`} className="group relative min-w-[240px] rounded-xl border border-black/10 bg-lumiere-warm p-4">
                        {editingBeat === b.beat_id ? (
                          <div className="space-y-2">
                            <input data-testid={`beat-edit-label-${b.sequence}`} value={beatDraft.label} onChange={(e) => setBeatDraft((d) => ({ ...d, label: e.target.value }))}
                              className="w-full bg-white border border-black/15 rounded px-2 py-1 font-display text-lg" />
                            <textarea data-testid={`beat-edit-purpose-${b.sequence}`} rows={3} value={beatDraft.purpose} onChange={(e) => setBeatDraft((d) => ({ ...d, purpose: e.target.value }))}
                              className="w-full bg-white border border-black/15 rounded px-2 py-1 text-xs resize-none" />
                            <div className="flex gap-2">
                              <button data-testid={`beat-save-${b.sequence}`} onClick={saveBeat} className="inline-flex items-center gap-1 bg-lumiere-ink text-lumiere-ivory px-3 py-1 rounded-full font-mono text-[0.55rem] uppercase tracking-widest"><Check size={11} /> {s("Save", "Guardar")}</button>
                              <button onClick={() => setEditingBeat(null)} className="inline-flex items-center gap-1 border border-black/15 text-lumiere-ink/60 px-3 py-1 rounded-full font-mono text-[0.55rem] uppercase tracking-widest"><X size={11} /> {s("Cancel", "Cancelar")}</button>
                            </div>
                          </div>
                        ) : (
                          <>
                            <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                              <button data-testid={`beat-edit-${b.sequence}`} onClick={() => startEditBeat(b)} className="w-6 h-6 flex items-center justify-center rounded-full bg-black/5 text-lumiere-ink/50 hover:bg-lumiere-ink hover:text-white" title={s("Edit", "Editar")}><Pencil size={11} /></button>
                              <button data-testid={`beat-delete-${b.sequence}`} onClick={() => deleteBeat(b.beat_id)} className="w-6 h-6 flex items-center justify-center rounded-full bg-black/5 text-lumiere-ink/50 hover:bg-red-600 hover:text-white" title={s("Remove", "Eliminar")}><Trash2 size={11} /></button>
                            </div>
                            <div className="flex items-center justify-between mb-1 pr-12">
                              <span className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-iris">{b.function}</span>
                              <span className={`font-mono text-[0.5rem] uppercase tracking-widest border rounded-full px-1.5 py-0.5 ${b.criticality === "critical" ? "text-lumiere-gold border-lumiere-gold/50" : "text-lumiere-ink/40 border-black/15"}`}>{b.criticality}</span>
                            </div>
                            <h3 className="font-display text-lg leading-tight">{g(b.label)}</h3>
                            <p className="text-xs text-lumiere-ink/55 mt-1 line-clamp-3">{g(b.purpose)}</p>
                            <span className={`inline-block mt-2 font-mono text-[0.5rem] uppercase tracking-widest border rounded-full px-1.5 py-0.5 ${cov[b.coverage_status] || cov.empty}`}>{b.coverage_status}</span>
                          </>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-3">
                    <p className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50">{s("Shot list", "Lista de tomas")} · {shots.length}</p>
                    <button data-testid="regen-shots" onClick={genShots} disabled={busy === "shots"} className="text-lumiere-ink/50 hover:text-lumiere-ink"><RefreshCw size={14} className={busy === "shots" ? "animate-spin" : ""} /></button>
                  </div>
                  <div className="grid sm:grid-cols-2 gap-3" data-testid="shots-list">
                    {shots.map((s) => (
                      <div key={s.shot_id} data-testid={`shot-${s.shot_id}`} className="group relative rounded-xl border border-black/10 bg-lumiere-warm p-4">
                        <div className="absolute top-2 right-2 flex gap-1 opacity-100 transition-all">
                          <button data-testid={`edit-shot-${s.shot_id}`} onClick={() => startEditShot(s)} title={lang === "es" ? "Editar" : "Edit"}
                            className="w-6 h-6 flex items-center justify-center rounded-full bg-black/10 text-lumiere-ink/60 hover:bg-lumiere-ink hover:text-white transition-colors">
                            <Pencil size={12} />
                          </button>
                          <button data-testid={`regen-shot-${s.shot_id}`} onClick={() => regenShot(s.shot_id)} disabled={regenShotId === s.shot_id} title={lang === "es" ? "Actualizar con IA" : "Update with AI"}
                            className="w-6 h-6 flex items-center justify-center rounded-full bg-lumiere-iris/10 text-lumiere-iris hover:bg-lumiere-iris hover:text-white transition-colors">
                            {regenShotId === s.shot_id ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />}
                          </button>
                          <button data-testid={`delete-shot-${s.shot_id}`} onClick={() => deleteShot(s.shot_id)} title={lang === "es" ? "Eliminar toma" : "Remove shot"}
                            className="w-6 h-6 flex items-center justify-center rounded-full bg-black/10 text-lumiere-ink/50 hover:bg-red-600 hover:text-white transition-colors">
                            <Trash2 size={12} />
                          </button>
                        </div>
                        <div className="flex items-center justify-between pr-20">
                          <span className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/50">{g(s.shot_type)} · {g(s.movement)}</span>
                          <span className="font-mono text-[0.55rem] text-lumiere-ink/40">P{s.priority}{s.status === "captured" ? " · ✓" : ""}</span>
                        </div>
                        {editingShot === s.shot_id ? (
                          <div className="mt-2 space-y-2">
                            <textarea data-testid={`shot-edit-action-${s.shot_id}`} rows={3} value={shotDraft} onChange={(e) => setShotDraft(e.target.value)}
                              className="w-full text-sm bg-white border border-black/15 rounded-lg px-2 py-1.5 focus:outline-none focus:border-lumiere-ink" />
                            <div className="flex gap-2">
                              <button data-testid={`shot-save-${s.shot_id}`} onClick={saveShot} className="inline-flex items-center gap-1 bg-lumiere-ink text-lumiere-ivory px-3 py-1 rounded-full font-mono text-[0.55rem] uppercase tracking-widest"><Check size={11} /> {lang === "es" ? "Guardar" : "Save"}</button>
                              <button onClick={() => setEditingShot(null)} className="inline-flex items-center gap-1 border border-black/15 text-lumiere-ink/60 px-3 py-1 rounded-full font-mono text-[0.55rem] uppercase tracking-widest"><X size={11} /> {lang === "es" ? "Cancelar" : "Cancel"}</button>
                            </div>
                          </div>
                        ) : (
                          <p className="text-sm mt-1">{g(s.action)}</p>
                        )}
                        <div className="flex items-center gap-2 mt-2 text-lumiere-gold">
                          <Clock size={12} /><span className="font-mono text-[0.6rem] uppercase tracking-widest">{s.ideal_time_label ? `${winLabel(s.ideal_time_window, lang)} · ${s.ideal_time_label}` : winLabel(s.ideal_time_window, lang)}</span>
                        </div>
                        {previz[s.shot_id]?.ok && previz[s.shot_id]?.previz_path ? (
                          <div className="relative mt-2 rounded-lg overflow-hidden" data-testid={`previz-img-${s.shot_id}`}>
                            <img src={fileUrl(previz[s.shot_id].previz_path)} alt="" className="w-full h-28 object-cover" />
                            <span className="absolute top-1 left-1 font-mono text-[0.45rem] uppercase tracking-widest bg-lumiere-iris text-white px-1.5 py-0.5 rounded">AI Reference</span>
                            <span className="block text-[0.55rem] text-lumiere-ink/50 mt-1 italic">This is the shot. Go get the real one.</span>
                          </div>
                        ) : (
                          <button data-testid={`previz-${s.shot_id}`} onClick={() => doPreviz(s.shot_id)} disabled={previz[s.shot_id]?.loading}
                            className="mt-2 inline-flex items-center gap-1.5 border border-lumiere-iris/30 text-lumiere-iris hover:bg-lumiere-iris/10 px-2.5 py-1 rounded-full font-mono text-[0.55rem] uppercase tracking-widest transition-colors">
                            {previz[s.shot_id]?.loading ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />} {previz[s.shot_id]?.degraded ? (lang === "es" ? "Vista previa no disponible" : "Preview unavailable") : (lang === "es" ? "Previsualizar toma" : "Preview shot")}
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                  <button data-testid="go-capture" onClick={() => setTab("during")} className="mt-5 inline-flex items-center gap-2 bg-lumiere-iris text-white hover:bg-lumiere-irisHover px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
                    <Camera size={14} /> {s("Start directing", "Empezar a dirigir")}
                  </button>
                </div>
              </>
            )}
          </div>
        )}

        {/* ---------------- DURING ---------------- */}
        {tab === "during" && <LiveDirector id={id} beats={beats} onAction={setShot} reload={load} onGoAfter={() => setTab("after")} />}

        {/* ---------------- AFTER ---------------- */}
        {tab === "after" && (
          <div data-testid="phase-after-content" className="space-y-8">
            <div className="rounded-2xl border border-black/10 bg-lumiere-warm p-6">
              <div className="flex items-center justify-between flex-wrap gap-3">
                <div>
                  <p className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50 mb-1">{s("Footage", "Material")} · {assets.length} {s("clip(s)", "clip(s)")}</p>
                  <p className="text-sm text-lumiere-ink/55">{s("Upload what you captured. LUMIÈRE analyzes it against your story.", "Sube lo que capturaste. LUMIÈRE lo analiza contra tu historia.")}</p>
                </div>
                <div className="flex gap-2">
                  <input ref={fileRef} type="file" accept="video/*" multiple className="hidden" onChange={(e) => upload(Array.from(e.target.files || []))} data-testid="upload-input" />
                  {demo && <button data-testid="demo-load-footage" onClick={demoLoad} disabled={busy === "demoload"} className="inline-flex items-center gap-2 border border-lumiere-iris/40 text-lumiere-iris hover:bg-lumiere-iris/10 px-4 py-2 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">{busy === "demoload" ? <Loader2 size={14} className="animate-spin" /> : <Film size={14} />} {s("Load demo footage", "Cargar material demo")}</button>}
                  <button data-testid="upload-button" onClick={() => fileRef.current?.click()} disabled={busy === "upload"} className="inline-flex items-center gap-2 border border-lumiere-ink/20 hover:border-lumiere-iris px-4 py-2 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
                    {busy === "upload" ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />} {s("Upload", "Subir")}
                  </button>
                  <button data-testid="analyze-button" onClick={analyze} disabled={busy === "analyze" || assets.length === 0} className="inline-flex items-center gap-2 bg-lumiere-ink text-lumiere-ivory hover:bg-lumiere-ink/85 disabled:opacity-50 px-4 py-2 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
                    {busy === "analyze" ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />} {s("Analyze", "Analizar")}
                  </button>
                </div>
              </div>
              {assets.length > 0 && (
                <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 mt-4">
                  {assets.map((a) => (
                    <div key={a.id} className="group rounded-lg overflow-hidden border border-black/10 bg-black aspect-video relative">
                      <video src={fileUrl(a.storage_path)} className="w-full h-full object-cover" muted preload="metadata" playsInline />
                      <span className={`absolute bottom-1 left-1 font-mono text-[0.45rem] uppercase px-1 rounded ${a.status === "analyzed" ? "bg-lumiere-sage/80 text-white" : "bg-black/60 text-white"}`}>{a.status}</span>
                      <button data-testid={`delete-asset-${a.id}`} onClick={() => deleteAsset(a.id)}
                        className="absolute top-1 right-1 w-6 h-6 flex items-center justify-center rounded-full bg-black/60 text-white/90 hover:bg-red-600 opacity-0 group-hover:opacity-100 transition-opacity" title="Remove clip">
                        <Trash2 size={12} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {c && (
              <div className="grid md:grid-cols-[auto_1fr] gap-6 items-center rounded-2xl border border-black/10 bg-lumiere-warm p-6" data-testid="completeness-panel">
                <CircularScore value={c.score} label={s("Story completeness", "Completitud")} testid="completeness-score" />
                <div className="space-y-2">
                  <Bar label={s("Narrative", "Narrativa")} v={c.narrative} /><Bar label={s("Visual", "Visual")} v={c.visual} /><Bar label={s("Emotional", "Emocional")} v={c.emotional} />
                  <p className="font-mono text-[0.6rem] uppercase tracking-widest mt-2 text-lumiere-ink/50">
                    {s("Critical beats", "Beats críticos")} {c.critical_covered}/{c.critical_total} · <span className={c.status === "COMPLETE" ? "text-lumiere-sage" : "text-lumiere-gold"}>{c.status}</span>
                  </p>
                </div>
              </div>
            )}

            {gaps.length > 0 && (
              <div className="rounded-2xl border-2 border-lumiere-iris/40 bg-lumiere-iris/5 p-7" data-testid="missing-shot">
                <p className="font-mono text-xs uppercase tracking-widest text-lumiere-iris mb-1">{s("The film needs one more thing", "A la película le falta una cosa")}</p>
                <h2 className="font-display text-2xl">{s("Your film is almost ready.", "Tu película casi está lista.")}</h2>
                <p className="text-lumiere-ink/60 mt-1">{s("One final shot could make it stronger.", "Una toma final podría hacerla más fuerte.")}</p>
                <div className="mt-4 space-y-3">
                  {gaps.map((gp) => (
                    <div key={gp.gap_id} data-testid={`gap-${gp.gap_id}`} className="rounded-xl border border-black/10 bg-lumiere-warm p-4 flex items-center justify-between gap-4">
                      <div>
                        <span className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-gold">{s("Missing", "Falta")}: {gp.missing_function}</span>
                        <p className="text-sm mt-0.5">{g(gp.why_it_matters)}</p>
                      </div>
                      <button data-testid={`get-the-shot-${gp.gap_id}`} onClick={() => getTheShot(gp.gap_id)} disabled={busy === "gap"}
                        className="shrink-0 inline-flex items-center gap-2 bg-lumiere-iris text-white hover:bg-lumiere-irisHover px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors shadow-[0_0_18px_rgba(114,103,168,0.35)]">
                        {busy === "gap" ? <Loader2 size={14} className="animate-spin" /> : <Camera size={14} />} {s("Get the shot", "Consigue la toma")}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div>
              <div className="flex items-center justify-between mb-3">
                <p className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50">{s("Your film", "Tu película")}</p>
                <div className="flex gap-2">
                  {STYLES.map((st) => (
                    <button key={st} data-testid={`build-${st}`} onClick={() => build(st)} disabled={busy === "build"}
                      className="inline-flex items-center gap-1.5 border border-lumiere-ink/20 hover:border-lumiere-gold px-3 py-1.5 rounded-full font-mono text-[0.6rem] uppercase tracking-widest capitalize transition-colors">
                      {busy === "build" ? <Loader2 size={12} className="animate-spin" /> : <Film size={12} />} {st}
                    </button>
                  ))}
                </div>
              </div>
              {cuts.length === 0 ? (
                <div className="border border-dashed border-black/15 rounded-2xl py-14 text-center text-lumiere-ink/50">{s("Build your film once footage is analyzed.", "Arma tu película cuando el material esté analizado.")}</div>
              ) : (
                <div className="space-y-4" data-testid="cuts-list">
                  {cuts.map((cut, i) => (
                    <div key={cut.cut_id} data-testid={`cut-${cut.cut_id}`} className="rounded-2xl border border-black/10 bg-lumiere-warm overflow-hidden">
                      <div className="flex items-center gap-2 px-4 py-2 border-b border-black/5">
                        <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/60">v{i + 1} · {cut.style} · {Math.round(cut.actual_duration)}s</span>
                        {cut.parent_cut_id && <span className="font-mono text-[0.55rem] text-lumiere-iris">↳ {s("revision", "revisión")}</span>}
                        <div className="ml-auto flex gap-2">
                          <button data-testid={`edit-cut-${cut.cut_id}`} onClick={() => openEditor(cut)}
                            className="inline-flex items-center gap-1.5 border border-lumiere-iris/40 text-lumiere-iris hover:bg-lumiere-iris/10 px-3 py-1 rounded-full font-mono text-[0.55rem] uppercase tracking-widest transition-colors">
                            <Sliders size={11} /> {s("Edit", "Editar")}
                          </button>
                          <button data-testid={`share-${cut.cut_id}`} onClick={() => doShare(cut.cut_id)} disabled={busy === "share"}
                            className="inline-flex items-center gap-1.5 border border-lumiere-ink/20 hover:border-lumiere-gold px-3 py-1 rounded-full font-mono text-[0.55rem] uppercase tracking-widest transition-colors">
                            {busy === "share" ? <Loader2 size={11} className="animate-spin" /> : <Share2 size={11} />} {s("Share", "Compartir")}
                          </button>
                        </div>
                      </div>
                      {shared[cut.cut_id] && (
                        <div className="flex items-center gap-2 px-4 py-2 bg-lumiere-gold/10" data-testid={`share-link-${cut.cut_id}`}>
                          <input readOnly value={shared[cut.cut_id]} className="flex-1 bg-white border border-black/10 rounded px-2 py-1 font-mono text-[0.6rem]" />
                          <button onClick={() => { navigator.clipboard?.writeText(shared[cut.cut_id]); toast.success("Copied"); }} className="text-lumiere-ink/60 hover:text-lumiere-ink"><Copy size={13} /></button>
                        </div>
                      )}
                      <video src={fileUrl(cut.storage_path)} controls preload="metadata" playsInline className="w-full bg-black max-h-[380px]" data-testid={`cut-player-${cut.cut_id}`} />
                      <div className="p-4 flex gap-2">
                        <input data-testid="revise-input" value={revText} onChange={(e) => setRevText(e.target.value)} placeholder={s('e.g. "make it faster, less of me"', 'ej. "más rápido, menos de mí"')}
                          className="flex-1 bg-white border border-black/15 rounded-full px-4 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-lumiere-iris" />
                        <button data-testid={`revise-${cut.cut_id}`} onClick={() => revise(cut.cut_id)} disabled={busy === "revise"}
                          className="inline-flex items-center gap-2 bg-lumiere-ink text-lumiere-ivory hover:bg-lumiere-ink/85 px-4 py-2 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
                          {busy === "revise" ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />} {s("Revise", "Revisar")}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ---------------- AGENT TRACE ---------------- */}
        <div className="mt-12 border-t border-black/10 pt-6">
          <button data-testid="trace-toggle" onClick={() => (trace ? setTrace(null) : loadTrace())} className="inline-flex items-center gap-2 font-mono text-[0.65rem] uppercase tracking-widest text-lumiere-ink/50 hover:text-lumiere-ink">
            <Activity size={14} /> {s("Agent Trace", "Traza de agentes")} {trace ? "▲" : "▼"}
          </button>
          {trace && (
            <div className="mt-3 overflow-x-auto rounded-xl border border-black/10" data-testid="agent-trace">
              <table className="w-full text-xs">
                <thead><tr className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40 border-b border-black/10">
                  <th className="text-left p-2">Time</th><th className="text-left p-2">Agent</th><th className="text-left p-2">Operation</th><th className="text-left p-2">ms</th><th className="text-left p-2">Status</th><th className="text-left p-2">Conf</th></tr></thead>
                <tbody>
                  {trace.map((r, i) => (
                    <tr key={i} className="border-b border-black/5">
                      <td className="p-2 font-mono text-lumiere-ink/40">{(r.timestamp || "").slice(11, 19)}</td>
                      <td className="p-2">{r.agent}</td><td className="p-2 font-mono">{r.operation}</td>
                      <td className="p-2 font-mono">{r.duration_ms}</td>
                      <td className="p-2 font-mono">{r.status}</td><td className="p-2 font-mono">{r.confidence?.toFixed?.(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </main>

      {editCutId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" data-testid="cut-editor-modal" onClick={() => !editBusy && setEditCutId(null)}>
          <div className="w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-2xl bg-lumiere-ivory border border-black/10 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-display text-2xl">{s("Edit film", "Editar película")}</h3>
              <button data-testid="cut-editor-close" onClick={() => setEditCutId(null)} className="text-lumiere-ink/50 hover:text-lumiere-ink"><X size={18} /></button>
            </div>
            {(() => {
              const Group = ({ label, children }) => (
                <div className="mb-4">
                  <p className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50 mb-2">{label}</p>
                  <div className="flex flex-wrap gap-2">{children}</div>
                </div>
              );
              const pill = (active, onClick, key, content, testid) => (
                <button key={key} data-testid={testid} onClick={onClick}
                  className={`px-3 py-1.5 rounded-full font-mono text-[0.6rem] uppercase tracking-widest border transition-colors capitalize ${active ? "border-lumiere-iris bg-lumiere-iris/15 text-lumiere-ink" : "border-black/15 text-lumiere-ink/55 hover:text-lumiere-ink"}`}>{content}</button>
              );
              const set = (k, v) => setEditOpts((o) => ({ ...o, [k]: v }));
              const looksES = { none: "Ninguno", cinematic: "Cine", warm: "Cálido", cool: "Frío", bw: "B/N", vivid: "Vívido" };
              const trES = { dissolve: "Disolvencia", fade: "Fundido", fadeblack: "A negro", cut: "Corte", fadewhite: "A blanco", none: "Ninguno" };
              const posES = { top: "Arriba", center: "Centro", bottom: "Abajo" };
              const szES = { small: "Pequeño", medium: "Mediano", large: "Grande" };
              return (
                <>
                  <Group label={s("Format / orientation", "Formato / orientación")}>
                    {EDIT_ASPECTS.map(([v, lbl]) => pill(editOpts.aspect === v, () => set("aspect", v), v, lbl, `edit-aspect-${v}`))}
                  </Group>
                  <Group label={s("Color effect", "Efecto de color")}>
                    {EDIT_LOOKS.map((v) => pill(editOpts.look === v, () => set("look", v), v, lang === "es" ? looksES[v] : v, `edit-look-${v}`))}
                  </Group>
                  <Group label={s("Speed", "Velocidad")}>
                    {EDIT_SPEEDS.map(([v, lbl]) => pill(editOpts.speed === v, () => set("speed", v), v, lbl, `edit-speed-${v}`))}
                  </Group>
                  <Group label={s("Scene transition (multi-clip)", "Transición de escenas (multi-clip)")}>
                    {EDIT_SCENE_TR.map((v) => pill(editOpts.scene_transition === v, () => set("scene_transition", v), v, lang === "es" ? trES[v] : v, `edit-scenetr-${v}`))}
                  </Group>
                  <Group label={s("Ending fade", "Fundido final")}>
                    {EDIT_END_FADE.map((v) => pill(editOpts.end_fade === v, () => set("end_fade", v), v, lang === "es" ? trES[v] : v, `edit-endfade-${v}`))}
                  </Group>
                  <div className="mb-4 border-t border-black/10 pt-4">
                    <label className="flex items-center gap-2 mb-2 cursor-pointer">
                      <input type="checkbox" data-testid="edit-text-toggle" checked={editOpts.text_enabled} onChange={(e) => set("text_enabled", e.target.checked)} className="accent-lumiere-iris" />
                      <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/60">{s("Title text", "Texto del título")}</span>
                    </label>
                    {editOpts.text_enabled && (
                      <div className="space-y-2">
                        <input data-testid="edit-text-content" value={editOpts.text_content} onChange={(e) => set("text_content", e.target.value)}
                          placeholder={s("Your title", "Tu título")} className="w-full bg-white border border-black/15 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-lumiere-iris" />
                        <div className="flex flex-wrap gap-2">
                          {EDIT_TEXT_POS.map((v) => pill(editOpts.text_position === v, () => set("text_position", v), v, lang === "es" ? posES[v] : v, `edit-textpos-${v}`))}
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {EDIT_TEXT_SZ.map((v) => pill(editOpts.text_size === v, () => set("text_size", v), v, lang === "es" ? szES[v] : v, `edit-textsz-${v}`))}
                        </div>
                      </div>
                    )}
                  </div>
                  <div className="flex gap-2 justify-end border-t border-black/10 pt-4">
                    <button onClick={() => setEditCutId(null)} disabled={editBusy} className="px-4 py-2 rounded-full border border-black/15 text-lumiere-ink/60 font-mono text-xs uppercase tracking-widest">{s("Cancel", "Cancelar")}</button>
                    <button data-testid="edit-apply" onClick={applyEdit} disabled={editBusy}
                      className="inline-flex items-center gap-2 bg-lumiere-iris text-white hover:bg-lumiere-irisHover px-5 py-2 rounded-full font-mono text-xs uppercase tracking-widest transition-colors disabled:opacity-60">
                      {editBusy ? <Loader2 size={14} className="animate-spin" /> : <Sliders size={14} />} {editBusy ? s("Rendering…", "Renderizando…") : s("Apply", "Aplicar")}
                    </button>
                  </div>
                </>
              );
            })()}
          </div>
        </div>
      )}
    </div>
  );
}

function Bar({ label, v = 0 }) {
  const pct = Math.round((v || 0) * 100);
  return (
    <div>
      <div className="flex justify-between mb-1"><span className="text-sm text-lumiere-ink/70">{label}</span><span className="font-mono text-xs text-lumiere-ink/50">{pct}%</span></div>
      <div className="h-1.5 bg-black/10 rounded-full overflow-hidden"><div className="h-full bg-lumiere-iris rounded-full" style={{ width: `${pct}%`, transition: "width 0.8s ease" }} /></div>
    </div>
  );
}

function LiveDirector({ id, beats, onAction, reload, onGoAfter }) {
  const { lang } = useI18n();
  const s = (en, es) => (lang === "es" ? es : en);
  const [data, setData] = useState(null);
  const load = useCallback(async () => { try { const r = await api.get(`/v2/experiences/${id}/next-shot`); setData(r.data); } catch { /* */ } }, [id]);
  useEffect(() => { load(); }, [load]);
  const m = data?.mission;
  const act = async (status, reason) => { await onAction(m.shot_id, status, reason); await load(); await reload(); };
  if (!data) return <div className="py-16 text-center"><Loader2 className="animate-spin text-lumiere-iris mx-auto" /></div>;
  if (!m) return (
    <div data-testid="phase-during-content" className="rounded-2xl border border-black/10 bg-lumiere-warm p-10 text-center">
      <Check size={32} className="mx-auto text-lumiere-sage mb-3" />
      <h2 className="font-display text-2xl">{s("All missions handled.", "Todas las misiones completadas.")}</h2>
      <p className="text-lumiere-ink/55 mt-1">{s("Head to After to upload and build your film.", "Ve a Después para subir y armar tu película.")}</p>
      <button data-testid="during-go-after" onClick={onGoAfter}
        className="mt-6 inline-flex items-center gap-2 bg-lumiere-ink text-lumiere-ivory hover:bg-lumiere-ink/85 px-6 py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
        {s("Go to After", "Ir a Después")} <ArrowRight size={15} />
      </button>
    </div>
  );
  const p = data.progress || {};
  return (
    <div data-testid="phase-during-content" className="max-w-2xl mx-auto">
      <div className="rounded-2xl overflow-hidden border border-black/10 bg-gradient-to-br from-lumiere-iris/15 to-lumiere-gold/10 p-8" data-testid="live-director">
        <div className="flex items-center gap-2 text-lumiere-iris mb-4">
          <Clock size={14} /><span className="font-mono text-[0.6rem] uppercase tracking-widest">{m.ideal_time_label ? `${s("Golden hour", "Hora dorada")} · ${m.ideal_time_label}` : m.ideal_time_window} · {s("why now: best light", "por qué ahora: mejor luz")}</span>
        </div>
        <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50">{g(m.shot_type)} · {g(m.movement)}{m.is_gap_mission ? " · GAP" : ""}</span>
        <h2 className="font-display text-3xl mt-2 leading-tight" data-testid="live-mission-action">{g(m.action)}</h2>
        <p className="text-lumiere-ink/60 mt-3">{g(m.narrative_purpose)}</p>
        <p className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/40 mt-3">~{m.duration_seconds}s</p>
        <div className="flex flex-wrap gap-2 mt-6">
          <button data-testid="mission-gotit" onClick={() => act("captured")} className="inline-flex items-center gap-2 bg-lumiere-ink text-lumiere-ivory hover:bg-lumiere-ink/85 px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest"><Check size={14} /> {s("I got it", "Lo tengo")}</button>
          <button data-testid="mission-skip" onClick={() => act("skipped", "not_possible")} className="inline-flex items-center gap-2 border border-black/15 text-lumiere-ink/60 hover:text-lumiere-ink px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest"><SkipForward size={14} /> {s("Skip", "Saltar")}</button>
          <button data-testid="mission-notnow" onClick={() => act("pending", "not_now")} className="inline-flex items-center gap-2 border border-black/15 text-lumiere-ink/60 hover:text-lumiere-ink px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest"><ChevronRight size={14} /> {s("Not now", "Ahora no")}</button>
        </div>
      </div>
      <div className="mt-4 flex items-center justify-between font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50" data-testid="production-progress">
        <span>{p.captured || 0} {s("of", "de")} {p.total || 0} {s("shots", "tomas")} · {p.critical_covered || 0} {s("of", "de")} {p.critical_total || 0} {s("critical beats covered", "beats críticos cubiertos")}</span>
        <span>{data.remaining} {s("pending", "pendientes")}</span>
      </div>
    </div>
  );
}
