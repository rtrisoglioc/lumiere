import { useEffect, useRef, useState } from "react";
import { X, Loader2, Upload, Wand2, Music, Captions, Film, Plus, Search, Trash2, Sparkles } from "lucide-react";
import { toast } from "sonner";
import { api, fileUrl, API, getToken } from "@/lib/api";

const ASPECTS = [["16:9", "aspect-video"], ["9:16", "aspect-[9/16]"], ["1:1", "aspect-square"]];
const FILTERS = ["none", "cinematic", "warm", "cool", "bw", "vivid", "film", "noir", "vintage", "teal_orange"];
const SPEEDS = [[0.5, "0.5×"], [1, "1×"], [2, "2×"]];
const TRANSITIONS = ["none", "fade", "dissolve", "smooth", "fadeblack", "fadewhite"];
const CAP_STYLES = ["bold", "pop", "boxed", "minimal"];
const CAP_LANGS = [["", "Auto"], ["es", "ES"], ["en", "EN"]];
const INSERT_EFFECTS = ["kenburns", "zoomout", "slide", "fade", "pulse"];
const CSS_FILTER = { none: "none", cinematic: "contrast(1.1) saturate(1.2)", warm: "sepia(0.15) saturate(1.1)", cool: "hue-rotate(-12deg) saturate(1.05)", bw: "grayscale(1) contrast(1.08)", vivid: "saturate(1.4) contrast(1.08)", film: "contrast(1.12) saturate(1.05) sepia(0.06)", noir: "grayscale(1) contrast(1.28) brightness(0.98)", vintage: "sepia(0.35) saturate(0.9) contrast(1.03)", teal_orange: "contrast(1.08) saturate(1.15) hue-rotate(-6deg)" };

export function CutEditor({ cut, lang, onDone, onClose }) {
  const [aspect, setAspect] = useState("16:9");
  const [filter, setFilter] = useState("cinematic");
  const [speed, setSpeed] = useState(1);
  const [transition, setTransition] = useState("fade");
  const [musicId, setMusicId] = useState("");
  const [tracks, setTracks] = useState([]);
  const [captions, setCaptions] = useState({ enabled: false, style: "pop", lang: "" });
  const [textOv, setTextOv] = useState({ enabled: false, content: "", position: "top", size: 0.06 });
  const [transSpeed, setTransSpeed] = useState("med");
  const [musicVol, setMusicVol] = useState(0.85);
  const [result, setResult] = useState(null);
  const [logo, setLogo] = useState({ enabled: false, x: 0.95, y: 0.95, scale: 0.18, opacity: 0.85 });
  const [hasLogo, setHasLogo] = useState(false);
  const [busy, setBusy] = useState(false);
  const [logoBust, setLogoBust] = useState(Date.now());
  const [videoDur, setVideoDur] = useState(30);
  const [library, setLibrary] = useState([]);
  const [cutInserts, setCutInserts] = useState([]);
  const [stockEnabled, setStockEnabled] = useState(false);
  const [aiPrompt, setAiPrompt] = useState("");
  const [stockQ, setStockQ] = useState("");
  const [stockResults, setStockResults] = useState([]);
  const [insBusy, setInsBusy] = useState(false);
  const fileRef = useRef();

  const loadLibrary = () => api.get("/inserts").then((r) => setLibrary(r.data)).catch(() => {});
  useEffect(() => {
    api.get("/music").then((r) => setTracks(r.data)).catch(() => {});
    api.get("/me/preferences").then((r) => { setHasLogo(r.data.has_logo); if (r.data.logo) setLogo((l) => ({ ...l, ...r.data.logo })); }).catch(() => {});
    api.get("/inserts/config").then((r) => setStockEnabled(r.data.stock_enabled)).catch(() => {});
    loadLibrary();
  }, []);

  const insUrl = (id) => `${API}/inserts/${id}/image?auth=${encodeURIComponent(getToken() || "")}`;
  const genAi = async () => {
    if (!aiPrompt.trim()) return;
    setInsBusy(true);
    try { const r = await api.post("/inserts/ai", { prompt: aiPrompt }, { timeout: 90000 }); setLibrary((l) => [r.data, ...l]); setAiPrompt(""); toast.success(lang === "es" ? "Inserto IA creado" : "AI insert created"); }
    catch { toast.error(lang === "es" ? "Falló la generación" : "Generation failed"); }
    finally { setInsBusy(false); }
  };
  const searchStock = async () => {
    if (!stockQ.trim()) return;
    setInsBusy(true);
    try { const r = await api.get(`/inserts/stock/search?q=${encodeURIComponent(stockQ)}`); setStockResults(r.data); }
    catch { toast.error(lang === "es" ? "Búsqueda falló" : "Search failed"); }
    finally { setInsBusy(false); }
  };
  const saveStock = async (photo) => {
    try { const r = await api.post("/inserts/stock/save", { url: photo.full, alt: photo.alt }); setLibrary((l) => [r.data, ...l]); toast.success(lang === "es" ? "Añadido a tu biblioteca" : "Added to library"); }
    catch { toast.error("Failed"); }
  };
  const addToCut = (asset) => setCutInserts((c) => [...c, { id: asset.id, thumb: insUrl(asset.id), at_sec: Math.min(2, Math.max(0, videoDur / 2)), duration: 2, effect: "kenburns" }]);
  const updateInsert = (i, patch) => setCutInserts((c) => c.map((x, idx) => idx === i ? { ...x, ...patch } : x));
  const removeInsert = (i) => setCutInserts((c) => c.filter((_, idx) => idx !== i));

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
      const r = await api.post(`/cuts/${cut.id}/pro-edit`, { aspect, filter, speed, transition, music_id: musicId || null, logo, captions, text_overlay: textOv, transition_speed: transSpeed, music_volume: musicVol, inserts: cutInserts.map((i) => ({ id: i.id, at_sec: i.at_sec, duration: i.duration, effect: i.effect })) }, { timeout: 300000 });
      if (r.data?.captions_status === "no_speech")
        toast.warning(lang === "es" ? "No se detectó voz clara para subtítulos en este corte." : "No clear speech detected for captions in this cut.");
      toast.success(lang === "es" ? "¡Listo! Mira el resultado abajo ▶" : "Done! See the result below ▶");
      setResult(r.data); onDone?.(r.data);
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
              {result ? (
                <>
                  <video src={fileUrl(result.storage_path)} controls autoPlay loop className="w-full h-full object-cover" data-testid="cut-editor-result" />
                  <span className="absolute top-2 left-2 bg-lumiere-gold text-lumiere-ink px-2 py-1 rounded font-mono text-[0.55rem] uppercase tracking-widest">{lang === "es" ? "Resultado · con audio" : "Result · with audio"}</span>
                  <button onClick={() => setResult(null)} data-testid="cut-editor-editagain" className="absolute top-2 right-2 bg-black/70 text-white px-2 py-1 rounded font-mono text-[0.55rem] uppercase tracking-widest hover:bg-black">{lang === "es" ? "Editar de nuevo" : "Edit again"}</button>
                </>
              ) : (
                <>
                  <video src={fileUrl(cut.storage_path)} controls loop muted onLoadedMetadata={(e) => setVideoDur(e.target.duration || 30)} className="w-full h-full object-cover" style={{ filter: CSS_FILTER[filter] }} />
                  <span className="absolute top-2 left-2 bg-black/60 text-white/80 px-2 py-1 rounded font-mono text-[0.5rem] uppercase tracking-widest">{lang === "es" ? "Vista previa · sin audio" : "Preview · muted"}</span>
                  {logo.enabled && hasLogo && (
                    <img src={logoUrl} alt="" style={{ position: "absolute", width: `${logo.scale * 100}%`, opacity: logo.opacity, left: `calc((100% - ${logo.scale * 100}%) * ${logo.x})`, top: `calc((100% - ${logo.scale * 100}%) * ${logo.y})`, pointerEvents: "none" }} />
                  )}
                  {textOv.enabled && textOv.content && (
                    <div className={`absolute inset-x-0 flex justify-center px-4 pointer-events-none ${textOv.position === "top" ? "top-[6%]" : textOv.position === "center" ? "top-1/2 -translate-y-1/2" : "bottom-[12%]"}`}>
                      <span className="font-bold text-white text-center leading-tight" style={{ textShadow: "0 2px 4px #000,0 0 3px #000", fontSize: "clamp(14px,4vw,30px)" }}>{textOv.content}</span>
                    </div>
                  )}
                  {captions.enabled && (
                    <div className="absolute inset-x-0 bottom-[9%] flex justify-center pointer-events-none" data-testid="cut-captions-preview">
                      <span className={`px-2 py-0.5 font-bold text-white text-center leading-tight ${captions.style === "boxed" ? "bg-black/70" : ""} ${captions.style === "pop" ? "text-lumiere-gold uppercase" : ""}`}
                        style={{ textShadow: captions.style === "boxed" ? "none" : "0 1px 3px #000, 0 0 3px #000", fontSize: "clamp(11px,3vw,20px)" }}>
                        {lang === "es" ? "(ejemplo) subtítulos reales al exportar" : "(sample) real captions on export"}
                      </span>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
          <div className="space-y-4">
            <Ctrl label={lang === "es" ? "Formato" : "Format"}>{ASPECTS.map(([a]) => <Pill key={a} active={aspect === a} onClick={() => setAspect(a)} testid={`cut-aspect-${a}`}>{a}</Pill>)}</Ctrl>
            <Ctrl label={lang === "es" ? "Transición" : "Transition"}>{TRANSITIONS.map((tr) => <Pill key={tr} active={transition === tr} onClick={() => setTransition(tr)} testid={`cut-transition-${tr}`}>{tr}</Pill>)}</Ctrl>
            <p className="text-[0.6rem] text-zinc-500 -mt-2">{lang === "es" ? "Se aplica entre escenas del corte al exportar." : "Applied between scenes on export."}</p>
            {transition !== "none" && (
              <Ctrl label={lang === "es" ? "Velocidad de transición" : "Transition speed"}>
                {[["slow", lang === "es" ? "Lenta" : "Slow"], ["med", lang === "es" ? "Media" : "Med"], ["fast", lang === "es" ? "Rápida" : "Fast"]].map(([v, l]) => <Pill key={v} active={transSpeed === v} onClick={() => setTransSpeed(v)} testid={`cut-transpeed-${v}`}>{l}</Pill>)}
              </Ctrl>
            )}
            <Ctrl label={lang === "es" ? "Estilo" : "Look"}>{FILTERS.map((f) => <Pill key={f} active={filter === f} onClick={() => setFilter(f)} testid={`cut-filter-${f}`}>{f}</Pill>)}</Ctrl>
            <Ctrl label={lang === "es" ? "Velocidad" : "Speed"}>{SPEEDS.map(([s, l]) => <Pill key={s} active={speed === s} onClick={() => setSpeed(s)} testid={`cut-speed-${s}`}>{l}</Pill>)}</Ctrl>
            <div>
              <span className="font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500 flex items-center gap-1 mb-1.5"><Music size={11} /> {lang === "es" ? "Música" : "Music"}</span>
              <select value={musicId} onChange={(e) => setMusicId(e.target.value)} data-testid="cut-music"
                className="w-full bg-lumiere-ink border border-white/15 rounded px-2 py-2 text-sm text-white">
                <option value="">{lang === "es" ? "Sin música (audio original)" : "No music (original audio)"}</option>
                {tracks.map((t) => <option key={t.id} value={t.id}>{`${t.title?.[lang] || t.title?.en || ""} · ${t.mood}`}</option>)}
              </select>
              {musicId && <div className="mt-2"><Slider label={`${lang === "es" ? "Volumen música" : "Music volume"} ${Math.round(musicVol * 100)}%`} min={0} max={150} value={musicVol * 100} onChange={(v) => setMusicVol(v / 100)} testid="cut-music-volume" /></div>}
            </div>
            <div className="border-t border-white/10 pt-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500">{lang === "es" ? "Texto en el video" : "Text on video"}</span>
                <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={textOv.enabled} data-testid="cut-text-toggle" onChange={(e) => setTextOv({ ...textOv, enabled: e.target.checked })} /><span className="text-xs text-zinc-300">{lang === "es" ? "Activar" : "Enable"}</span></label>
              </div>
              {textOv.enabled && (
                <div className="mt-2 space-y-2">
                  <input value={textOv.content} onChange={(e) => setTextOv({ ...textOv, content: e.target.value })} data-testid="cut-text-content"
                    placeholder={lang === "es" ? "Escribe el texto…" : "Type your text…"}
                    className="w-full bg-lumiere-ink border border-white/15 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-lumiere-iris" />
                  <div className="flex flex-wrap gap-1.5">
                    {[["top", lang === "es" ? "Arriba" : "Top"], ["center", lang === "es" ? "Medio" : "Center"], ["bottom", lang === "es" ? "Abajo" : "Bottom"]].map(([v, l]) => <Pill key={v} active={textOv.position === v} onClick={() => setTextOv({ ...textOv, position: v })} testid={`cut-text-pos-${v}`}>{l}</Pill>)}
                  </div>
                  <Slider label={`${lang === "es" ? "Tamaño" : "Size"} ${Math.round(textOv.size * 100)}`} min={3} max={14} value={textOv.size * 100} onChange={(v) => setTextOv({ ...textOv, size: v / 100 })} testid="cut-text-size" />
                </div>
              )}
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
            <div className="border-t border-white/10 pt-3" data-testid="cut-inserts-section">
              <span className="font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500 flex items-center gap-1 mb-2"><Film size={11} /> {lang === "es" ? "Insertos B-roll" : "B-roll inserts"}</span>
              {/* AI generate */}
              <div className="flex gap-2">
                <input value={aiPrompt} onChange={(e) => setAiPrompt(e.target.value)} data-testid="cut-insert-ai-prompt"
                  placeholder={lang === "es" ? "Genera con IA: p.ej. amanecer en la montaña" : "Generate with AI: e.g. sunrise over mountains"}
                  className="flex-1 bg-lumiere-ink border border-white/15 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-lumiere-iris" />
                <button onClick={genAi} disabled={insBusy} data-testid="cut-insert-ai-gen"
                  className="inline-flex items-center gap-1 bg-lumiere-gold hover:bg-lumiere-goldHover text-lumiere-ink px-3 rounded font-mono text-[0.6rem] uppercase tracking-widest disabled:opacity-50">
                  {insBusy ? <Loader2 size={12} className="animate-spin" /> : <Sparkles size={12} />} IA
                </button>
              </div>
              {/* Stock search */}
              {stockEnabled ? (
                <div className="mt-2">
                  <div className="flex gap-2">
                    <input value={stockQ} onChange={(e) => setStockQ(e.target.value)} onKeyDown={(e) => e.key === "Enter" && searchStock()} data-testid="cut-insert-stock-q"
                      placeholder={lang === "es" ? "Buscar stock (Pexels)…" : "Search stock (Pexels)…"}
                      className="flex-1 bg-lumiere-ink border border-white/15 rounded px-2 py-1.5 text-sm text-white focus:outline-none focus:ring-1 focus:ring-lumiere-iris" />
                    <button onClick={searchStock} disabled={insBusy} data-testid="cut-insert-stock-search" className="inline-flex items-center gap-1 border border-white/15 px-3 rounded font-mono text-[0.6rem] uppercase tracking-widest text-zinc-300 hover:border-lumiere-iris"><Search size={12} /></button>
                  </div>
                  {stockResults.length > 0 && (
                    <div className="mt-2 grid grid-cols-4 gap-1.5 max-h-32 overflow-y-auto">
                      {stockResults.map((p) => (
                        <button key={p.id} onClick={() => saveStock(p)} data-testid={`cut-stock-${p.id}`} title={lang === "es" ? "Guardar en biblioteca" : "Save to library"}
                          className="relative aspect-video rounded overflow-hidden border border-white/10 hover:border-lumiere-iris group">
                          <img src={p.thumb} alt="" className="w-full h-full object-cover" />
                          <span className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center"><Plus size={16} className="text-white" /></span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <p className="mt-1 text-[0.6rem] text-zinc-500">{lang === "es" ? "Stock (Pexels) desactivado: falta la API key. La IA funciona." : "Stock (Pexels) off: API key missing. AI works."}</p>
              )}
              {/* Library */}
              {library.length > 0 && (
                <div className="mt-3">
                  <span className="font-mono text-[0.55rem] uppercase tracking-widest text-zinc-500">{lang === "es" ? "Tu biblioteca" : "Your library"}</span>
                  <div className="mt-1 grid grid-cols-4 gap-1.5 max-h-32 overflow-y-auto">
                    {library.map((a) => (
                      <button key={a.id} onClick={() => addToCut(a)} data-testid={`cut-lib-${a.id}`} title={lang === "es" ? "Añadir al corte" : "Add to cut"}
                        className="relative aspect-video rounded overflow-hidden border border-white/10 hover:border-lumiere-gold group">
                        <img src={insUrl(a.id)} alt="" className="w-full h-full object-cover" />
                        <span className="absolute top-0.5 left-0.5 text-[0.5rem] font-mono uppercase bg-black/60 px-1 rounded text-white">{a.source}</span>
                        <span className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 flex items-center justify-center"><Plus size={16} className="text-white" /></span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {/* Added to timeline */}
              {cutInserts.length > 0 && (
                <div className="mt-3 space-y-2">
                  {cutInserts.map((ins, i) => (
                    <div key={i} className="flex gap-2 items-center bg-lumiere-ink/60 border border-white/10 rounded p-2" data-testid={`cut-insert-row-${i}`}>
                      <img src={ins.thumb} alt="" className="w-14 h-9 object-cover rounded shrink-0" />
                      <div className="flex-1 space-y-1">
                        <div className="flex flex-wrap gap-1">{INSERT_EFFECTS.map((ef) => <button key={ef} data-testid={`cut-insert-${i}-effect-${ef}`} onClick={() => updateInsert(i, { effect: ef })} className={`px-1.5 py-0.5 font-mono text-[0.5rem] uppercase border rounded ${ins.effect === ef ? "bg-lumiere-gold border-lumiere-gold text-lumiere-ink" : "border-white/15 text-zinc-400"}`}>{ef}</button>)}</div>
                        <div className="flex gap-3">
                          <label className="flex-1 text-[0.55rem] font-mono uppercase tracking-widest text-zinc-500">{lang === "es" ? "En seg" : "At sec"} {ins.at_sec.toFixed(1)}
                            <input type="range" min={0} max={Math.max(1, Math.floor(videoDur))} step={0.5} value={ins.at_sec} data-testid={`cut-insert-${i}-at`} onChange={(e) => updateInsert(i, { at_sec: Number(e.target.value) })} className="w-full accent-lumiere-iris" /></label>
                          <label className="flex-1 text-[0.55rem] font-mono uppercase tracking-widest text-zinc-500">{lang === "es" ? "Dur" : "Dur"} {ins.duration.toFixed(1)}s
                            <input type="range" min={0.8} max={6} step={0.1} value={ins.duration} data-testid={`cut-insert-${i}-dur`} onChange={(e) => updateInsert(i, { duration: Number(e.target.value) })} className="w-full accent-lumiere-iris" /></label>
                        </div>
                      </div>
                      <button onClick={() => removeInsert(i)} data-testid={`cut-insert-${i}-remove`} className="text-zinc-500 hover:text-red-400 shrink-0"><Trash2 size={14} /></button>
                    </div>
                  ))}
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
