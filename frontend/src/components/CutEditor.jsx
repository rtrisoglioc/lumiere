import { useEffect, useRef, useState } from "react";
import { X, Loader2, Upload, Wand2, Music, Captions } from "lucide-react";
import { toast } from "sonner";
import { api, fileUrl, API, getToken } from "@/lib/api";
import { bl } from "@/lib/bilingual";

const ASPECTS = [["16:9", "aspect-video"], ["9:16", "aspect-[9/16]"], ["1:1", "aspect-square"]];
const FILTERS = ["none", "cinematic", "warm", "cool", "bw", "vivid", "film", "noir", "vintage", "teal_orange"];
const SPEEDS = [[0.5, "0.5×"], [1, "1×"], [2, "2×"]];
const TRANSITIONS = ["none", "fade", "dissolve", "smooth", "fadeblack", "fadewhite"];
const CAP_STYLES = ["bold", "pop", "boxed", "minimal"];
const CAP_LANGS = [["", "Auto"], ["es", "ES"], ["en", "EN"]];
const CSS_FILTER = { none: "none", cinematic: "contrast(1.1) saturate(1.2)", warm: "sepia(0.15) saturate(1.1)", cool: "hue-rotate(-12deg) saturate(1.05)", bw: "grayscale(1) contrast(1.08)", vivid: "saturate(1.4) contrast(1.08)", film: "contrast(1.12) saturate(1.05) sepia(0.06)", noir: "grayscale(1) contrast(1.28) brightness(0.98)", vintage: "sepia(0.35) saturate(0.9) contrast(1.03)", teal_orange: "contrast(1.08) saturate(1.15) hue-rotate(-6deg)" };

export function CutEditor({ cut, lang, onDone, onClose }) {
  const [aspect, setAspect] = useState("16:9");
  const [filter, setFilter] = useState("cinematic");
  const [speed, setSpeed] = useState(1);
  const [transition, setTransition] = useState("fade");
  const [musicId, setMusicId] = useState("");
  const [tracks, setTracks] = useState([]);
  const [captions, setCaptions] = useState({ enabled: false, style: "pop", lang: "" });
  const [logo, setLogo] = useState({ enabled: false, x: 0.95, y: 0.95, scale: 0.18, opacity: 0.85 });
  const [hasLogo, setHasLogo] = useState(false);
  const [busy, setBusy] = useState(false);
  const [logoBust, setLogoBust] = useState(Date.now());
  const fileRef = useRef();

  useEffect(() => {
    api.get("/music").then((r) => setTracks(r.data)).catch(() => {});
    api.get("/me/preferences").then((r) => { setHasLogo(r.data.has_logo); if (r.data.logo) setLogo((l) => ({ ...l, ...r.data.logo })); }).catch(() => {});
  }, []);

  const aspectClass = ASPECTS.find((a) => a[0] === aspect)?.[1] || "aspect-video";
  const logoUrl = `${API}/me/logo?auth=${encodeURIComponent(getToken() || "")}&b=${logoBust}`;

  const uploadLogo = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try { await api.post("/me/logo", fd, { headers: { "Content-Type": "multipart/form-data" } }); setHasLogo(true); setLogo((l) => ({ ...l, enabled: true })); setLogoBust(Date.now()); toast.success("Logo OK"); }
    catch { toast.error("Upload failed"); }
  };

  const apply = async () => {
    setBusy(true);
    try {
      const r = await api.post(`/cuts/${cut.id}/pro-edit`, { aspect, filter, speed, transition, music_id: musicId || null, logo, captions }, { timeout: 300000 });
      toast.success(lang === "es" ? "Nueva versión lista" : "New version ready");
      onDone?.(r.data); onClose?.();
    } catch (e) { toast.error(e?.response?.data?.detail || (lang === "es" ? "Falló" : "Failed")); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[70] bg-black/80 flex items-center justify-center p-4" onClick={() => !busy && onClose?.()}>
      <div className="bg-lumiere-surface border border-white/15 max-w-4xl w-full max-h-[92vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="cut-editor">
        <div className="flex items-center justify-between p-5 border-b border-white/10 sticky top-0 bg-lumiere-surface z-10">
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-iris">{lang === "es" ? "Editor Pro del Corte" : "Cut Pro Editor"}</span>
          <button onClick={onClose} data-testid="cut-editor-close" className="text-zinc-400 hover:text-white"><X size={18} /></button>
        </div>
        <div className="grid md:grid-cols-2 gap-6 p-6">
          <div>
            <div className={`relative ${aspectClass} bg-black rounded-lg overflow-hidden max-h-[60vh] mx-auto`} data-testid="cut-editor-preview">
              <video src={fileUrl(cut.storage_path)} controls loop className="w-full h-full object-cover" style={{ filter: CSS_FILTER[filter] }} />
              {logo.enabled && hasLogo && (
                <img src={logoUrl} alt="" style={{ position: "absolute", width: `${logo.scale * 100}%`, opacity: logo.opacity, left: `calc((100% - ${logo.scale * 100}%) * ${logo.x})`, top: `calc((100% - ${logo.scale * 100}%) * ${logo.y})`, pointerEvents: "none" }} />
              )}
              {captions.enabled && (
                <div className="absolute inset-x-0 bottom-[9%] flex justify-center pointer-events-none" data-testid="cut-captions-preview">
                  <span className={`px-2 py-0.5 font-bold text-white text-center leading-tight ${captions.style === "boxed" ? "bg-black/70" : ""} ${captions.style === "pop" ? "text-lumiere-gold uppercase" : ""}`}
                    style={{ textShadow: captions.style === "boxed" ? "none" : "0 1px 3px #000, 0 0 3px #000", fontSize: "clamp(11px,3vw,20px)" }}>
                    {lang === "es" ? "Subtítulos automáticos IA" : "AI auto-captions"}
                  </span>
                </div>
              )}
            </div>
          </div>
          <div className="space-y-4">
            <Ctrl label={lang === "es" ? "Formato" : "Format"}>{ASPECTS.map(([a]) => <Pill key={a} active={aspect === a} onClick={() => setAspect(a)} testid={`cut-aspect-${a}`}>{a}</Pill>)}</Ctrl>
            <Ctrl label={lang === "es" ? "Transición" : "Transition"}>{TRANSITIONS.map((tr) => <Pill key={tr} active={transition === tr} onClick={() => setTransition(tr)} testid={`cut-transition-${tr}`}>{tr}</Pill>)}</Ctrl>
            <Ctrl label={lang === "es" ? "Estilo" : "Look"}>{FILTERS.map((f) => <Pill key={f} active={filter === f} onClick={() => setFilter(f)} testid={`cut-filter-${f}`}>{f}</Pill>)}</Ctrl>
            <Ctrl label={lang === "es" ? "Velocidad" : "Speed"}>{SPEEDS.map(([s, l]) => <Pill key={s} active={speed === s} onClick={() => setSpeed(s)} testid={`cut-speed-${s}`}>{l}</Pill>)}</Ctrl>
            <div>
              <span className="font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500 flex items-center gap-1 mb-1.5"><Music size={11} /> {lang === "es" ? "Música" : "Music"}</span>
              <select value={musicId} onChange={(e) => setMusicId(e.target.value)} data-testid="cut-music"
                className="w-full bg-lumiere-ink border border-white/15 rounded px-2 py-2 text-sm text-white">
                <option value="">{lang === "es" ? "Sin música (audio original)" : "No music (original audio)"}</option>
                {tracks.map((t) => <option key={t.id} value={t.id}>{bl(t.title, lang)} · {t.mood}</option>)}
              </select>
            </div>
            <div className="border-t border-white/10 pt-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500 flex items-center gap-1"><Captions size={11} /> {lang === "es" ? "Subtítulos (IA)" : "Captions (AI)"}</span>
                <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={captions.enabled} data-testid="cut-captions-toggle" onChange={(e) => setCaptions({ ...captions, enabled: e.target.checked })} /><span className="text-xs text-zinc-300">{lang === "es" ? "Activar" : "Enable"}</span></label>
              </div>
              {captions.enabled && (
                <div className="mt-2 space-y-2">
                  <div className="flex flex-wrap gap-1.5">{CAP_STYLES.map((s) => <Pill key={s} active={captions.style === s} onClick={() => setCaptions({ ...captions, style: s })} testid={`cut-cap-style-${s}`}>{s}</Pill>)}</div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[0.55rem] uppercase tracking-widest text-zinc-500">{lang === "es" ? "Idioma" : "Language"}</span>
                    {CAP_LANGS.map(([v, l]) => <Pill key={v} active={captions.lang === v} onClick={() => setCaptions({ ...captions, lang: v })} testid={`cut-cap-lang-${v || "auto"}`}>{l}</Pill>)}
                  </div>
                  <p className="text-[0.6rem] text-zinc-500 leading-snug">{lang === "es" ? "Transcribe el audio del corte con IA y quema los subtítulos." : "Transcribes the cut's audio with AI and burns in subtitles."}</p>
                </div>
              )}
            </div>
            <div className="border-t border-white/10 pt-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500">Logo</span>
                {hasLogo && <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={logo.enabled} data-testid="cut-logo-toggle" onChange={(e) => setLogo({ ...logo, enabled: e.target.checked })} /><span className="text-xs text-zinc-300">{lang === "es" ? "Mostrar" : "Show"}</span></label>}
              </div>
              <input ref={fileRef} type="file" accept="image/png" onChange={uploadLogo} className="hidden" data-testid="cut-logo-file" />
              <button onClick={() => fileRef.current?.click()} data-testid="cut-logo-upload" className="mt-2 inline-flex items-center gap-2 border border-white/15 px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-widest text-zinc-300 hover:border-lumiere-iris"><Upload size={12} /> {hasLogo ? (lang === "es" ? "Reemplazar" : "Replace") : (lang === "es" ? "Subir logo" : "Upload logo")}</button>
              {hasLogo && logo.enabled && (
                <div className="mt-3 space-y-2">
                  <div className="grid grid-cols-3 gap-1 w-20">
                    {[0, 0.5, 1].map((yy) => [0, 0.5, 1].map((xx) => (
                      <button key={`${xx}-${yy}`} data-testid={`cut-logo-pos-${xx}-${yy}`} onClick={() => setLogo({ ...logo, x: xx, y: yy })}
                        className={`h-6 border ${Math.abs(logo.x - xx) < 0.01 && Math.abs(logo.y - yy) < 0.01 ? "bg-lumiere-iris border-lumiere-iris" : "border-white/15"}`} />)))}
                  </div>
                  <Slider label={`${lang === "es" ? "Tamaño" : "Size"} ${Math.round(logo.scale * 100)}%`} min={3} max={50} value={logo.scale * 100} onChange={(v) => setLogo({ ...logo, scale: v / 100 })} testid="cut-logo-size" />
                  <Slider label={`${lang === "es" ? "Opacidad" : "Opacity"} ${Math.round(logo.opacity * 100)}%`} min={10} max={100} value={logo.opacity * 100} onChange={(v) => setLogo({ ...logo, opacity: v / 100 })} testid="cut-logo-opacity" />
                </div>
              )}
            </div>
            <button onClick={apply} disabled={busy} data-testid="cut-editor-apply"
              className="w-full inline-flex items-center justify-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover disabled:opacity-50 text-white py-3 font-mono text-xs uppercase tracking-widest">
              {busy ? <Loader2 size={15} className="animate-spin" /> : <Wand2 size={15} />} {busy ? (lang === "es" ? "Renderizando…" : "Rendering…") : (lang === "es" ? "Aplicar → nueva versión" : "Apply → new version")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const Ctrl = ({ label, children }) => (<div><span className="font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500 block mb-1.5">{label}</span><div className="flex flex-wrap gap-1.5">{children}</div></div>);
const Pill = ({ active, onClick, children, testid }) => (<button data-testid={testid} onClick={onClick} className={`px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-widest border capitalize transition-colors ${active ? "bg-lumiere-iris border-lumiere-iris text-white" : "border-white/15 text-zinc-400 hover:border-white/40"}`}>{children}</button>);
const Slider = ({ label, min, max, value, onChange, testid }) => (<div><span className="font-mono text-[0.55rem] uppercase tracking-widest text-zinc-500">{label}</span><input type="range" min={min} max={max} value={value} data-testid={testid} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-lumiere-iris" /></div>);
