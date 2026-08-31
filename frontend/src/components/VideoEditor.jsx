import { useEffect, useRef, useState } from "react";
import { X, Loader2, Upload, Download, Wand2 } from "lucide-react";
import { toast } from "sonner";
import { api, API, getToken } from "@/lib/api";

const g = (o, lang) => (o ? o[lang] : "");
const ASPECTS = [["16:9", "aspect-video"], ["9:16", "aspect-[9/16]"], ["1:1", "aspect-square"]];
const FILTERS = ["none", "cinematic", "warm", "cool", "bw", "vivid"];
const SPEEDS = [[0.5, "0.5×"], [1, "1×"], [2, "2×"]];
const CSS_FILTER = {
  none: "none", cinematic: "contrast(1.1) saturate(1.2)", warm: "sepia(0.15) saturate(1.1)",
  cool: "hue-rotate(-12deg) saturate(1.05)", bw: "grayscale(1) contrast(1.08)", vivid: "saturate(1.4) contrast(1.08)",
};
const T = {
  title: { en: "Pro Editor", es: "Editor Pro" }, aspect: { en: "Format", es: "Formato" },
  look: { en: "Look", es: "Estilo" }, speed: { en: "Speed", es: "Velocidad" },
  logo: { en: "Logo / Watermark", es: "Logo / Marca de agua" },
  uploadLogo: { en: "Upload logo (PNG)", es: "Subir logo (PNG)" },
  showLogo: { en: "Show logo", es: "Mostrar logo" }, size: { en: "Size", es: "Tamaño" },
  opacity: { en: "Opacity", es: "Opacidad" }, position: { en: "Position", es: "Posición" },
  export: { en: "Export edit", es: "Exportar edición" }, exporting: { en: "Rendering…", es: "Renderizando…" },
};

export function VideoEditor({ job, lang, onDone, onClose }) {
  const [aspect, setAspect] = useState(job.options?.aspect_ratio || "16:9");
  const [filter, setFilter] = useState("cinematic");
  const [speed, setSpeed] = useState(1);
  const [logo, setLogo] = useState({ enabled: false, x: 0.95, y: 0.95, scale: 0.18, opacity: 0.85 });
  const [hasLogo, setHasLogo] = useState(false);
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [logoBust, setLogoBust] = useState(Date.now());
  const fileRef = useRef();

  useEffect(() => {
    api.get("/me/preferences").then((r) => {
      setHasLogo(r.data.has_logo);
      if (r.data.logo) setLogo((l) => ({ ...l, ...r.data.logo }));
    }).catch(() => {});
  }, []);

  const aspectClass = ASPECTS.find((a) => a[0] === aspect)?.[1] || "aspect-video";
  const videoSrc = `${API}/video/${job.id}/download?auth=${encodeURIComponent(getToken() || "")}`;
  const logoUrl = `${API}/me/logo?auth=${encodeURIComponent(getToken() || "")}&b=${logoBust}`;

  const uploadLogo = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    setUploading(true);
    const fd = new FormData(); fd.append("file", f);
    try {
      await api.post("/me/logo", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setHasLogo(true); setLogo((l) => ({ ...l, enabled: true })); setLogoBust(Date.now());
      toast.success("Logo saved");
    } catch { toast.error("Upload failed"); } finally { setUploading(false); }
  };

  const doExport = async () => {
    setBusy(true);
    let before = [];
    try { before = (await api.get("/video/jobs")).data.map((j) => j.id); } catch { /* */ }
    try {
      const r = await api.post(`/video/jobs/${job.id}/edit`, { aspect, filter, speed, logo }, { timeout: 180000 });
      toast.success(lang === "es" ? "Edición lista" : "Edit ready");
      onDone?.(r.data); onClose?.();
    } catch (e) {
      // ffmpeg can take 30-70s; a transient proxy hiccup must not show a false failure
      // if the edit job was actually created server-side.
      await new Promise((res) => setTimeout(res, 3000));
      try {
        const after = (await api.get("/video/jobs")).data;
        const created = after.find((j) => j.kind === "edit" && j.parent_job === job.id && !before.includes(j.id));
        if (created) { toast.success(lang === "es" ? "Edición lista" : "Edit ready"); onDone?.(created); onClose?.(); return; }
      } catch { /* */ }
      toast.error(e?.response?.data?.detail || (lang === "es" ? "Falló la exportación" : "Export failed"));
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-[70] bg-black/80 flex items-center justify-center p-4" onClick={() => !busy && onClose?.()}>
      <div className="bg-lumiere-surface border border-white/15 max-w-4xl w-full max-h-[92vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="video-editor">
        <div className="flex items-center justify-between p-5 border-b border-white/10 sticky top-0 bg-lumiere-surface">
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-iris">{g(T.title, lang)}</span>
          <button onClick={onClose} data-testid="editor-close" className="text-zinc-400 hover:text-white"><X size={18} /></button>
        </div>
        <div className="grid md:grid-cols-2 gap-6 p-6">
          {/* preview */}
          <div>
            <div className={`relative ${aspectClass} bg-black rounded-lg overflow-hidden max-h-[60vh] mx-auto`} data-testid="editor-preview">
              <video src={videoSrc} controls loop className="w-full h-full object-cover" style={{ filter: CSS_FILTER[filter] }} />
              {logo.enabled && hasLogo && (
                <img src={logoUrl} alt="logo" data-testid="editor-logo-preview"
                  style={{ position: "absolute", width: `${logo.scale * 100}%`, opacity: logo.opacity,
                           left: `calc((100% - ${logo.scale * 100}%) * ${logo.x})`,
                           top: `calc((100% - ${logo.scale * 100}%) * ${logo.y})`, pointerEvents: "none" }} />
              )}
            </div>
          </div>
          {/* controls */}
          <div className="space-y-5">
            <Ctrl label={g(T.aspect, lang)}>
              {ASPECTS.map(([a]) => (
                <Pill key={a} active={aspect === a} onClick={() => setAspect(a)} testid={`editor-aspect-${a}`}>{a}</Pill>
              ))}
            </Ctrl>
            <Ctrl label={g(T.look, lang)}>
              {FILTERS.map((f) => (
                <Pill key={f} active={filter === f} onClick={() => setFilter(f)} testid={`editor-filter-${f}`}>{f}</Pill>
              ))}
            </Ctrl>
            <Ctrl label={g(T.speed, lang)}>
              {SPEEDS.map(([s, lbl]) => (
                <Pill key={s} active={speed === s} onClick={() => setSpeed(s)} testid={`editor-speed-${s}`}>{lbl}</Pill>
              ))}
            </Ctrl>

            <div className="border-t border-white/10 pt-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500">{g(T.logo, lang)}</span>
                {hasLogo && (
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={logo.enabled} data-testid="editor-logo-toggle"
                      onChange={(e) => setLogo({ ...logo, enabled: e.target.checked })} />
                    <span className="text-xs text-zinc-300">{g(T.showLogo, lang)}</span>
                  </label>
                )}
              </div>
              <input ref={fileRef} type="file" accept="image/png" onChange={uploadLogo} className="hidden" data-testid="editor-logo-file" />
              <button onClick={() => fileRef.current?.click()} disabled={uploading} data-testid="editor-logo-upload"
                className="mt-2 inline-flex items-center gap-2 border border-white/15 px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-widest text-zinc-300 hover:border-lumiere-iris transition-colors">
                {uploading ? <Loader2 size={12} className="animate-spin" /> : <Upload size={12} />} {hasLogo ? "Replace logo" : g(T.uploadLogo, lang)}
              </button>

              {hasLogo && logo.enabled && (
                <div className="mt-4 space-y-3">
                  <div>
                    <span className="font-mono text-[0.55rem] uppercase tracking-widest text-zinc-500">{g(T.position, lang)}</span>
                    <div className="grid grid-cols-3 gap-1 w-24 mt-1">
                      {[0, 0.5, 1].map((yy) => [0, 0.5, 1].map((xx) => (
                        <button key={`${xx}-${yy}`} data-testid={`editor-logo-pos-${xx}-${yy}`}
                          onClick={() => setLogo({ ...logo, x: xx, y: yy })}
                          className={`h-7 border transition-colors ${Math.abs(logo.x - xx) < 0.01 && Math.abs(logo.y - yy) < 0.01 ? "bg-lumiere-iris border-lumiere-iris" : "border-white/15 hover:border-white/40"}`} />
                      )))}
                    </div>
                  </div>
                  <Slider label={`${g(T.size, lang)} ${Math.round(logo.scale * 100)}%`} min={3} max={50} value={logo.scale * 100}
                    onChange={(v) => setLogo({ ...logo, scale: v / 100 })} testid="editor-logo-size" />
                  <Slider label={`${g(T.opacity, lang)} ${Math.round(logo.opacity * 100)}%`} min={10} max={100} value={logo.opacity * 100}
                    onChange={(v) => setLogo({ ...logo, opacity: v / 100 })} testid="editor-logo-opacity" />
                  <Slider label={`X ${Math.round(logo.x * 100)}%`} min={0} max={100} value={logo.x * 100}
                    onChange={(v) => setLogo({ ...logo, x: v / 100 })} testid="editor-logo-x" />
                  <Slider label={`Y ${Math.round(logo.y * 100)}%`} min={0} max={100} value={logo.y * 100}
                    onChange={(v) => setLogo({ ...logo, y: v / 100 })} testid="editor-logo-y" />
                </div>
              )}
            </div>

            <button onClick={doExport} disabled={busy} data-testid="editor-export"
              className="w-full inline-flex items-center justify-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover disabled:opacity-50 text-white py-3 font-mono text-xs uppercase tracking-widest transition-colors">
              {busy ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />} {busy ? g(T.exporting, lang) : g(T.export, lang)}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const Ctrl = ({ label, children }) => (
  <div>
    <span className="font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500 block mb-1.5">{label}</span>
    <div className="flex flex-wrap gap-1.5">{children}</div>
  </div>
);
const Pill = ({ active, onClick, children, testid }) => (
  <button data-testid={testid} onClick={onClick}
    className={`px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-widest border transition-colors capitalize ${active ? "bg-lumiere-iris border-lumiere-iris text-white" : "border-white/15 text-zinc-400 hover:border-white/40"}`}>{children}</button>
);
const Slider = ({ label, min, max, value, onChange, testid }) => (
  <div>
    <span className="font-mono text-[0.55rem] uppercase tracking-widest text-zinc-500">{label}</span>
    <input type="range" min={min} max={max} value={value} data-testid={testid}
      onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-lumiere-iris" />
  </div>
);
