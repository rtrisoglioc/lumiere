import { useEffect, useRef, useState } from "react";
import { X, Loader2, Upload, Wand2, Type } from "lucide-react";
import { toast } from "sonner";
import { api, API, getToken } from "@/lib/api";

const POSITIONS = [["top", "Top"], ["center", "Center"], ["bottom", "Bottom"]];
const COLORS = ["#FFFFFF", "#FFD400", "#111111", "#D6A85F", "#7267A8", "#C81E1E"];

export function SocialImageEditor({ post, lang, onDone, onClose }) {
  const [logo, setLogo] = useState({ enabled: false, x: 0.95, y: 0.95, scale: 0.2, opacity: 0.95 });
  const [headline, setHeadline] = useState({ enabled: false, content: "", position: "top", color: "#FFD400", size: 0.09 });
  const [subline, setSubline] = useState({ enabled: false, content: "", position: "bottom", color: "#FFFFFF", size: 0.055 });
  const [hasLogo, setHasLogo] = useState(false);
  const [busy, setBusy] = useState(false);
  const [logoBust, setLogoBust] = useState(Date.now());
  const fileRef = useRef();

  useEffect(() => {
    api.get("/me/preferences").then((r) => setHasLogo(r.data.has_logo)).catch(() => {});
    const o = post.overlay_opts || {};
    if (o.logo) setLogo((l) => ({ ...l, ...o.logo }));
    const ts = o.texts || (o.text ? [o.text] : []);
    if (ts[0]) setHeadline((h) => ({ ...h, ...ts[0], enabled: true }));
    if (ts[1]) setSubline((s) => ({ ...s, ...ts[1], enabled: true }));
  }, []);

  const imgUrl = `${API}/social/posts/${post.id}/image?ts=${logoBust}`;
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
      const texts = [headline, subline].filter((t) => t.enabled && t.content.trim());
      await api.post(`/social/posts/${post.id}/overlay`, { logo, texts }, { timeout: 60000 });
      toast.success(lang === "es" ? "Diseño actualizado" : "Design updated");
      onDone?.(); onClose?.();
    } catch (e) { toast.error(e?.response?.data?.detail || (lang === "es" ? "Falló" : "Failed")); }
    finally { setBusy(false); }
  };

  const layerStyle = (t) => ({
    position: "absolute", left: 0, right: 0, textAlign: "center", color: t.color,
    fontWeight: 800, padding: "0 6%", pointerEvents: "none", lineHeight: 1.05,
    fontSize: `clamp(14px, ${t.size * 100}px, 52px)`,
    textShadow: "0 2px 5px rgba(0,0,0,0.85), 0 0 3px rgba(0,0,0,0.85)",
    ...(t.position === "top" ? { top: "5%" } : t.position === "center" ? { top: "50%", transform: "translateY(-50%)" } : { bottom: "5%" }),
  });

  return (
    <div className="fixed inset-0 z-[70] bg-black/70 flex items-center justify-center p-4" onClick={() => !busy && onClose?.()}>
      <div className="bg-lumiere-warm text-lumiere-ink border border-lumiere-ink/15 rounded-2xl max-w-3xl w-full max-h-[92vh] overflow-y-auto" onClick={(e) => e.stopPropagation()} data-testid="social-image-editor">
        <div className="flex items-center justify-between p-5 border-b border-lumiere-ink/10 sticky top-0 bg-lumiere-warm z-10 rounded-t-2xl">
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-iris">{lang === "es" ? "Editar diseño" : "Edit design"}</span>
          <button onClick={onClose} data-testid="social-image-editor-close" className="text-lumiere-ink/50 hover:text-lumiere-ink"><X size={18} /></button>
        </div>
        <div className="grid md:grid-cols-2 gap-6 p-6">
          <div>
            <div className="relative aspect-square bg-lumiere-ink/5 rounded-lg overflow-hidden" data-testid="social-image-editor-preview">
              {post.image_path && <img src={imgUrl} alt="" className="w-full h-full object-cover" />}
              {logo.enabled && hasLogo && (
                <img src={logoUrl} alt="" style={{ position: "absolute", width: `${logo.scale * 100}%`, opacity: logo.opacity, left: `calc((100% - ${logo.scale * 100}%) * ${logo.x})`, top: `calc((100% - ${logo.scale * 100}%) * ${logo.y})`, pointerEvents: "none" }} />
              )}
              {[headline, subline].map((t, i) => t.enabled && t.content && <div key={i} style={layerStyle(t)}>{t.content}</div>)}
            </div>
          </div>
          <div className="space-y-5">
            {/* text layers */}
            <Layer label={lang === "es" ? "Titular (arriba)" : "Headline (top)"} val={headline} set={setHeadline} lang={lang} idp="headline" />
            <Layer label={lang === "es" ? "Subtítulo (abajo)" : "Subline (bottom)"} val={subline} set={setSubline} lang={lang} idp="subline" />
            </div>
            {/* logo */}
            <div className="border-t border-lumiere-ink/10 pt-4">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50">Logo</span>
                {hasLogo && <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={logo.enabled} data-testid="social-logo-toggle" onChange={(e) => setLogo({ ...logo, enabled: e.target.checked })} /><span className="text-xs">{lang === "es" ? "Mostrar" : "Show"}</span></label>}
              </div>
              <input ref={fileRef} type="file" accept="image/png" onChange={uploadLogo} className="hidden" data-testid="social-logo-file" />
              <button onClick={() => fileRef.current?.click()} data-testid="social-logo-upload" className="mt-2 inline-flex items-center gap-2 border border-lumiere-ink/15 px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/70 hover:border-lumiere-iris rounded-full"><Upload size={12} /> {hasLogo ? (lang === "es" ? "Reemplazar" : "Replace") : (lang === "es" ? "Subir logo" : "Upload logo")}</button>
              {hasLogo && logo.enabled && (
                <div className="mt-3 space-y-2">
                  <div className="grid grid-cols-3 gap-1 w-20">
                    {[0, 0.5, 1].map((yy) => [0, 0.5, 1].map((xx) => (
                      <button key={`${xx}-${yy}`} data-testid={`social-logo-pos-${xx}-${yy}`} onClick={() => setLogo({ ...logo, x: xx, y: yy })}
                        className={`h-6 border ${Math.abs(logo.x - xx) < 0.01 && Math.abs(logo.y - yy) < 0.01 ? "bg-lumiere-iris border-lumiere-iris" : "border-lumiere-ink/15"}`} />)))}
                  </div>
                  <Slider label={`${lang === "es" ? "Tamaño" : "Size"} ${Math.round(logo.scale * 100)}%`} min={5} max={50} value={logo.scale * 100} onChange={(v) => setLogo({ ...logo, scale: v / 100 })} testid="social-logo-size" />
                  <Slider label={`${lang === "es" ? "Opacidad" : "Opacity"} ${Math.round(logo.opacity * 100)}%`} min={20} max={100} value={logo.opacity * 100} onChange={(v) => setLogo({ ...logo, opacity: v / 100 })} testid="social-logo-opacity" />
                </div>
              )}
            </div>
            <button onClick={apply} disabled={busy} data-testid="social-image-apply"
              className="w-full inline-flex items-center justify-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover disabled:opacity-50 text-white py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              {busy ? <Loader2 size={15} className="animate-spin" /> : <Wand2 size={15} />} {busy ? (lang === "es" ? "Aplicando…" : "Applying…") : (lang === "es" ? "Aplicar diseño" : "Apply design")}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

const Pill = ({ active, onClick, children, testid }) => (
  <button data-testid={testid} onClick={onClick} className={`px-3 py-1.5 font-mono text-[0.6rem] uppercase tracking-widest border rounded-full transition-colors ${active ? "bg-lumiere-iris border-lumiere-iris text-white" : "border-lumiere-ink/15 text-lumiere-ink/60 hover:border-lumiere-ink/40"}`}>{children}</button>
);
const Slider = ({ label, min, max, value, onChange, testid }) => (
  <div><span className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40">{label}</span>
    <input type="range" min={min} max={max} value={value} data-testid={testid} onChange={(e) => onChange(Number(e.target.value))} className="w-full accent-lumiere-iris" /></div>
);

const Layer = ({ label, val, set, lang, idp }) => (
  <div className="border-t border-lumiere-ink/10 pt-3 first:border-t-0 first:pt-0">
    <div className="flex items-center justify-between">
      <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/50 flex items-center gap-1"><Type size={12} /> {label}</span>
      <label className="flex items-center gap-2 cursor-pointer"><input type="checkbox" checked={val.enabled} data-testid={`social-${idp}-toggle`} onChange={(e) => set({ ...val, enabled: e.target.checked })} /><span className="text-xs">{lang === "es" ? "Mostrar" : "Show"}</span></label>
    </div>
    {val.enabled && (
      <div className="mt-2 space-y-2">
        <input value={val.content} onChange={(e) => set({ ...val, content: e.target.value })} data-testid={`social-${idp}-content`}
          placeholder={lang === "es" ? "Escribe el texto…" : "Type your text…"}
          className="w-full bg-white border border-lumiere-ink/15 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-lumiere-iris" />
        <div className="flex flex-wrap gap-1.5">{POSITIONS.map(([v, l]) => <Pill key={v} active={val.position === v} onClick={() => set({ ...val, position: v })} testid={`social-${idp}-pos-${v}`}>{l}</Pill>)}</div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40">{lang === "es" ? "Color" : "Color"}</span>
          {COLORS.map((c) => <button key={c} data-testid={`social-${idp}-color-${c}`} onClick={() => set({ ...val, color: c })} className={`h-6 w-6 rounded-full border-2 ${val.color === c ? "border-lumiere-iris" : "border-lumiere-ink/15"}`} style={{ background: c }} />)}
        </div>
        <Slider label={`${lang === "es" ? "Tamaño" : "Size"} ${Math.round(val.size * 100)}`} min={3} max={18} value={val.size * 100} onChange={(v) => set({ ...val, size: v / 100 })} testid={`social-${idp}-size`} />
      </div>
    )}
  </div>
);
