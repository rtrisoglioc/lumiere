import { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Sparkles, Lock, Loader2, Image as ImageIcon, CalendarClock, Send, Trash2, Wand2, Palette, Upload } from "lucide-react";
import { toast } from "sonner";
import { api, API, getToken } from "@/lib/api";
import { useI18n } from "@/i18n";
import { Header } from "@/components/Header";
import { SocialImageEditor } from "@/components/SocialImageEditor";

const g = (o, lang) => (o ? (typeof o === "string" ? o : o[lang]) : "");
const NETWORKS = ["instagram", "facebook", "x", "linkedin", "tiktok"];
const STYLE_LABELS = {
  infographic: { es: "Infografía educativa", en: "Educational infographic" },
  illustration3d: { es: "Ilustración 3D", en: "3D illustration" },
  flatvector: { es: "Vector plano", en: "Flat vector" },
  minimal: { es: "Minimal corporativo", en: "Minimal corporate" },
  photo: { es: "Foto cinematográfica", en: "Cinematic photo" },
};
const STATUS_COLOR = { draft: "text-lumiere-ink/50 border-lumiere-ink/20", scheduled: "text-lumiere-gold border-lumiere-gold/50", published: "text-lumiere-sage border-lumiere-sage/50" };

const T = {
  title: { en: "AI Social Content Studio", es: "AI Social Content Studio" },
  sub: { en: "Give ideas. Get a content plan, AI copy, designs and a schedule.", es: "Da ideas. Recibe un plan de contenido, copy IA, diseños y programación." },
  brief: { en: "Your ideas / brief", es: "Tus ideas / brief" },
  ph: { en: "e.g. Promote our new cinematic road-trip series across the week, playful and warm tone", es: "ej. Promocionar nuestra nueva serie cinematográfica de road-trip durante la semana, tono cálido y divertido" },
  count: { en: "Posts", es: "Posts" },
  genPlan: { en: "Generate plan", es: "Generar plan" },
  planning: { en: "Planning…", es: "Planeando…" },
  lockedTitle: { en: "Social Studio is a Studio feature", es: "Social Studio es una función de Studio" },
  lockedSub: { en: "Upgrade to Studio to auto-generate posts, designs and schedules.", es: "Mejora a Studio para autogenerar posts, diseños y programación." },
  upgrade: { en: "Upgrade plan", es: "Mejorar plan" },
  design: { en: "Generate design", es: "Generar diseño" },
  schedule: { en: "Schedule", es: "Programar" },
  publish: { en: "Publish (simulated)", es: "Publicar (simulado)" },
  network: { en: "Network", es: "Red" },
  none: { en: "No posts yet. Generate a plan from your ideas.", es: "Aún no hay posts. Genera un plan desde tus ideas." },
  planSummary: { en: "Content plan", es: "Plan de contenido" },
  simNote: { en: "Publishing is simulated — real networks connect later.", es: "La publicación es simulada — las redes reales se conectan después." },
};

export default function SocialStudio() {
  const { lang } = useI18n();
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const [brief, setBrief] = useState("");
  const [count, setCount] = useState(4);
  const [busy, setBusy] = useState(false);
  const [plan, setPlan] = useState(null);
  const [posts, setPosts] = useState([]);
  const [working, setWorking] = useState({});
  const [editing, setEditing] = useState(null);
  const [brand, setBrand] = useState({ name: "", colors: ["#D6A85F", "#111111", "#F5F1E8"], auto_logo: false, image_style: "infographic", website: "" });
  const [brandStyles, setBrandStyles] = useState(["infographic", "illustration3d", "flatvector", "minimal", "photo"]);
  const [savingBrand, setSavingBrand] = useState(false);
  const [hasLogo, setHasLogo] = useState(false);
  const [logoBust, setLogoBust] = useState(Date.now());
  const logoRef = useRef();

  const loadAccount = async () => { try { const r = await api.get("/account"); setAccount(r.data); } catch { /* */ } };
  const loadPosts = async () => { try { const r = await api.get("/social/posts"); setPosts(r.data); } catch { /* */ } };
  const loadBrand = async () => { try { const r = await api.get("/social/brand"); setHasLogo(r.data.has_logo); if (r.data.styles) setBrandStyles(r.data.styles); if (r.data.brand) setBrand((b) => ({ ...b, ...r.data.brand, colors: r.data.brand.colors?.length ? r.data.brand.colors : b.colors })); } catch { /* */ } };
  useEffect(() => { loadAccount(); }, []);
  useEffect(() => { if (account?.entitlements?.social) { loadPosts(); loadBrand(); } }, [account]);

  const saveBrand = async () => {
    setSavingBrand(true);
    try { await api.put("/social/brand", brand); toast.success(lang === "es" ? "Marca guardada" : "Brand saved"); }
    catch { toast.error("Failed"); } finally { setSavingBrand(false); }
  };

  const uploadLogo = async (e) => {
    const f = e.target.files?.[0]; if (!f) return;
    const fd = new FormData(); fd.append("file", f);
    try {
      await api.post("/me/logo", fd, { headers: { "Content-Type": "multipart/form-data" } });
      setHasLogo(true); setLogoBust(Date.now());
      setBrand((b) => ({ ...b, auto_logo: true }));
      await api.put("/social/brand", { auto_logo: true });
      toast.success(lang === "es" ? "Logo subido — se estampará en la esquina" : "Logo uploaded — it will be stamped in the corner");
    } catch { toast.error(lang === "es" ? "Falló la subida (usa PNG)" : "Upload failed (use PNG)"); }
  };
  const logoUrl = `${API}/me/logo?auth=${encodeURIComponent(getToken() || "")}&b=${logoBust}`;

  const entitled = account?.entitlements?.social;

  const makePlan = async () => {
    if (!brief.trim()) return;
    setBusy(true);
    try {
      const r = await api.post("/social/plan", { brief: brief.trim(), count });
      setPlan(r.data.plan);
      toast.success(g(T.planSummary, lang));
      loadPosts();
    } catch (e) {
      toast.error(e?.response?.data?.detail === "social_not_entitled" ? g(T.lockedTitle, lang) : "Failed");
    } finally { setBusy(false); }
  };

  const setW = (id, v) => setWorking((w) => ({ ...w, [id]: v }));

  const genDesign = async (id) => {
    setW(id, "design");
    try { await api.post(`/social/posts/${id}/design`); await loadPosts(); toast.success("Design ready"); }
    catch { toast.error("Design failed"); } finally { setW(id, null); }
  };

  const updatePost = async (id, patch) => {
    setPosts((ps) => ps.map((p) => (p.id === id ? { ...p, ...patch } : p)));
    try { await api.put(`/social/posts/${id}`, patch); } catch { /* */ }
  };

  const doSchedule = async (post) => {
    const dt = post._when;
    if (!dt) { toast.error("Pick date & time"); return; }
    setW(post.id, "schedule");
    try {
      await api.post(`/social/posts/${post.id}/schedule`, { network: post.network, scheduled_at: new Date(dt).toISOString() });
      await loadPosts(); toast.success(g(T.schedule, lang));
    } catch { toast.error("Failed"); } finally { setW(post.id, null); }
  };

  const doPublish = async (id) => {
    setW(id, "publish");
    try { await api.post(`/social/posts/${id}/publish`); await loadPosts(); toast.success("Published (simulated)"); }
    catch { toast.error("Failed"); } finally { setW(id, null); }
  };

  const del = async (id) => { try { await api.delete(`/social/posts/${id}`); loadPosts(); } catch { /* */ } };

  const imgUrl = (id) => `${API}/social/posts/${id}/image?ts=${Date.now()}`;

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink">
      <Header back />
      <main className="px-4 sm:px-8 lg:px-16 py-10 max-w-6xl mx-auto" data-testid="social-studio-page">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-iris mb-2">{g(T.title, lang)}</p>
        <h1 className="font-display text-4xl sm:text-5xl font-black tracking-tight max-w-3xl">{g(T.sub, lang)}</h1>

        {!account ? (
          <div className="mt-10"><Loader2 className="animate-spin text-lumiere-iris" /></div>
        ) : !entitled ? (
          <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
            className="mt-10 rounded-2xl border border-lumiere-iris/40 bg-lumiere-iris/5 p-10 text-center max-w-xl" data-testid="social-locked">
            <Lock size={32} className="mx-auto text-lumiere-iris mb-4" />
            <h2 className="font-display text-2xl">{g(T.lockedTitle, lang)}</h2>
            <p className="text-lumiere-ink/60 mt-3">{g(T.lockedSub, lang)}</p>
            <button data-testid="social-upgrade-button" onClick={() => navigate("/pricing")}
              className="mt-6 inline-flex items-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover text-white px-6 py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              <Sparkles size={14} /> {g(T.upgrade, lang)}
            </button>
          </motion.div>
        ) : (
          <>
            <div className="mt-8 rounded-2xl border border-lumiere-gold/40 bg-lumiere-gold/5 p-6" data-testid="brand-kit">
              <div className="flex items-center gap-2 mb-3">
                <Palette size={16} className="text-lumiere-gold" />
                <span className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/60">{lang === "es" ? "Kit de Marca" : "Brand Kit"}</span>
              </div>
              <div className="grid md:grid-cols-3 gap-4 items-end">
                <div>
                  <label className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40 block mb-1">{lang === "es" ? "Nombre de marca" : "Brand name"}</label>
                  <input value={brand.name || ""} data-testid="brand-name" onChange={(e) => setBrand({ ...brand, name: e.target.value })}
                    placeholder="LUMIÈRE" className="w-full bg-white border border-lumiere-ink/15 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-lumiere-gold" />
                </div>
                <div>
                  <label className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40 block mb-1">{lang === "es" ? "Colores" : "Colors"}</label>
                  <div className="flex items-center gap-2">
                    {brand.colors.map((c, i) => (
                      <input key={i} type="color" value={c} data-testid={`brand-color-${i}`}
                        onChange={(e) => { const cs = [...brand.colors]; cs[i] = e.target.value; setBrand({ ...brand, colors: cs }); }}
                        className="h-9 w-9 rounded-md border border-lumiere-ink/15 cursor-pointer bg-white p-0.5" />
                    ))}
                  </div>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input type="checkbox" checked={!!brand.auto_logo} data-testid="brand-auto-logo" onChange={(e) => setBrand({ ...brand, auto_logo: e.target.checked })} />
                    <span className="text-xs text-lumiere-ink/70">{lang === "es" ? "Logo automático" : "Auto logo"}</span>
                  </label>
                  <button onClick={saveBrand} disabled={savingBrand} data-testid="brand-save"
                    className="inline-flex items-center gap-2 bg-lumiere-gold hover:bg-lumiere-goldHover text-lumiere-ink px-4 py-2 rounded-full font-mono text-[0.6rem] uppercase tracking-widest transition-colors disabled:opacity-50">
                    {savingBrand ? <Loader2 size={13} className="animate-spin" /> : null} {lang === "es" ? "Guardar" : "Save"}
                  </button>
                </div>
              </div>
              <div className="grid md:grid-cols-2 gap-4 mt-4">
                <div>
                  <label className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40 block mb-1">{lang === "es" ? "Estilo visual (IA)" : "Visual style (AI)"}</label>
                  <select value={brand.image_style || "infographic"} data-testid="brand-style" onChange={(e) => setBrand({ ...brand, image_style: e.target.value })}
                    className="w-full bg-white border border-lumiere-ink/15 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-lumiere-gold">
                    {brandStyles.map((s) => <option key={s} value={s}>{STYLE_LABELS[s]?.[lang] || s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40 block mb-1">{lang === "es" ? "Web (pie de imagen)" : "Website (image footer)"}</label>
                  <input value={brand.website || ""} data-testid="brand-website" onChange={(e) => setBrand({ ...brand, website: e.target.value })}
                    placeholder="www.tuempresa.com" className="w-full bg-white border border-lumiere-ink/15 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-lumiere-gold" />
                </div>
              </div>
              <div className="flex items-center gap-4 mt-4 border-t border-lumiere-ink/10 pt-4">
                <div className="h-14 w-14 rounded-lg border border-lumiere-ink/15 bg-white flex items-center justify-center overflow-hidden shrink-0" data-testid="brand-logo-preview">
                  {hasLogo ? <img src={logoUrl} alt="logo" className="max-h-full max-w-full object-contain" /> : <ImageIcon size={18} className="text-lumiere-ink/25" />}
                </div>
                <div className="flex-1">
                  <span className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40 block">{lang === "es" ? "Logo de empresa" : "Company logo"}</span>
                  <p className="text-[0.6rem] text-lumiere-ink/40">{hasLogo ? (lang === "es" ? "Se coloca en la esquina de cada imagen (con Logo automático)." : "Stamped in the corner of every image (with Auto logo).") : (lang === "es" ? "Sube un PNG (fondo transparente recomendado)." : "Upload a PNG (transparent background recommended).")}</p>
                </div>
                <input ref={logoRef} type="file" accept="image/png,image/jpeg,image/webp" onChange={uploadLogo} className="hidden" data-testid="brand-logo-file" />
                <button onClick={() => logoRef.current?.click()} data-testid="brand-logo-upload"
                  className="inline-flex items-center gap-2 border border-lumiere-ink/20 hover:border-lumiere-gold px-4 py-2 rounded-full font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/70 transition-colors shrink-0">
                  <Upload size={13} /> {hasLogo ? (lang === "es" ? "Reemplazar" : "Replace") : (lang === "es" ? "Subir logo" : "Upload logo")}
                </button>
              </div>
              <p className="text-[0.6rem] text-lumiere-ink/40 mt-3">{lang === "es" ? "El estilo define el tipo de imagen IA (infografías/ilustración, no fotos). Con Logo automático se coloca tu logo en la esquina y tu web abajo." : "Style sets the AI image type (infographics/illustration, not photos). Auto logo stamps your logo in the corner and your website at the bottom."}</p>
            </div>

            <div className="mt-6 rounded-2xl border border-lumiere-ink/10 bg-lumiere-warm p-6">
              <label className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50 block mb-2">{g(T.brief, lang)}</label>
              <textarea data-testid="social-brief-input" value={brief} onChange={(e) => setBrief(e.target.value)} rows={3}
                placeholder={g(T.ph, lang)}
                className="w-full bg-white border border-lumiere-ink/15 rounded-xl p-3 text-sm focus:outline-none focus:ring-2 focus:ring-lumiere-iris resize-none" />
              <div className="flex items-center gap-4 mt-4">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs uppercase tracking-widest text-lumiere-ink/50">{g(T.count, lang)}</span>
                  <select data-testid="social-count" value={count} onChange={(e) => setCount(Number(e.target.value))}
                    className="bg-white border border-lumiere-ink/15 rounded-lg px-3 py-1.5 text-sm">
                    {[2, 3, 4, 5, 6].map((n) => <option key={n} value={n}>{n}</option>)}
                  </select>
                </div>
                <button data-testid="social-generate-plan" onClick={makePlan} disabled={busy || !brief.trim()}
                  className="inline-flex items-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover disabled:opacity-50 text-white px-6 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors shadow-[0_0_20px_rgba(114,103,168,0.35)]">
                  {busy ? <Loader2 size={14} className="animate-spin" /> : <Wand2 size={14} />} {busy ? g(T.planning, lang) : g(T.genPlan, lang)}
                </button>
              </div>
              {plan && (
                <div className="mt-5 border-t border-lumiere-ink/10 pt-4">
                  <p className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-gold mb-1">{g(T.planSummary, lang)}</p>
                  <p className="text-sm text-lumiere-ink/70">{g(plan.summary, lang)}</p>
                  {plan.strategy && <p className="text-sm text-lumiere-ink/50 mt-2 italic">{g(plan.strategy, lang)}</p>}
                </div>
              )}
              <p className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/35 mt-4">{g(T.simNote, lang)}</p>
            </div>

            <div className="mt-10">
              {posts.length === 0 ? (
                <div className="border border-dashed border-lumiere-ink/15 rounded-2xl py-16 text-center">
                  <ImageIcon size={32} className="mx-auto text-lumiere-ink/30 mb-2" />
                  <p className="text-lumiere-ink/50">{g(T.none, lang)}</p>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 gap-6" data-testid="social-posts-list">
                  {posts.map((p) => (
                    <div key={p.id} data-testid={`social-post-${p.id}`} className="rounded-2xl border border-lumiere-ink/10 bg-lumiere-warm overflow-hidden flex flex-col">
                      <div className="aspect-video bg-lumiere-ink/5 flex items-center justify-center relative overflow-hidden">
                        {p.image_path ? (
                          <>
                            <img src={imgUrl(p.id)} alt="" className="w-full h-full object-cover" data-testid={`social-image-${p.id}`} />
                            <button data-testid={`social-brand-${p.id}`} onClick={() => setEditing(p)}
                              className="absolute bottom-2 left-2 inline-flex items-center gap-1.5 bg-lumiere-warm/90 border border-lumiere-ink/15 text-lumiere-ink px-3 py-1.5 rounded-full font-mono text-[0.55rem] uppercase tracking-widest hover:border-lumiere-iris transition-colors">
                              <Palette size={12} /> {lang === "es" ? "Diseño" : "Design"}
                            </button>
                          </>
                        ) : (
                          <button data-testid={`social-design-${p.id}`} onClick={() => genDesign(p.id)} disabled={working[p.id] === "design"}
                            className="inline-flex items-center gap-2 bg-lumiere-iris/10 border border-lumiere-iris/40 text-lumiere-iris px-4 py-2 rounded-full font-mono text-xs uppercase tracking-widest hover:bg-lumiere-iris/20 transition-colors">
                            {working[p.id] === "design" ? <Loader2 size={14} className="animate-spin" /> : <ImageIcon size={14} />} {g(T.design, lang)}
                          </button>
                        )}
                        <span className={`absolute top-2 right-2 font-mono text-[0.55rem] uppercase tracking-widest border rounded-full px-2 py-0.5 bg-lumiere-warm ${STATUS_COLOR[p.status] || ""}`}>{p.status}</span>
                      </div>
                      <div className="p-5 flex flex-col flex-1">
                        <h3 className="font-display text-xl">{g(p.title, lang)}</h3>
                        <textarea value={g(p.caption, lang)} onChange={(e) => updatePost(p.id, { caption: { ...(p.caption || {}), [lang]: e.target.value } })}
                          rows={7} data-testid={`social-caption-${p.id}`}
                          className="mt-2 w-full bg-white border border-lumiere-ink/10 rounded-lg p-2.5 text-base leading-relaxed resize-none focus:outline-none focus:ring-1 focus:ring-lumiere-iris" />
                        <div className="flex flex-wrap gap-1.5 mt-2">
                          {(p.hashtags || []).map((h, i) => <span key={i} className="font-mono text-xs text-lumiere-iris">#{h}</span>)}
                        </div>
                        <div className="grid grid-cols-2 gap-2 mt-4">
                          <div>
                            <label className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40 block mb-1">{g(T.network, lang)}</label>
                            <select value={p.network} data-testid={`social-network-${p.id}`} onChange={(e) => updatePost(p.id, { network: e.target.value })}
                              className="w-full bg-white border border-lumiere-ink/15 rounded-lg px-2 py-1.5 text-xs capitalize">
                              {NETWORKS.map((n) => <option key={n} value={n}>{n}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-ink/40 block mb-1">{g(T.schedule, lang)}</label>
                            <input type="datetime-local" data-testid={`social-when-${p.id}`}
                              defaultValue={p.scheduled_at ? p.scheduled_at.slice(0, 16) : ""}
                              onChange={(e) => (p._when = e.target.value)}
                              className="w-full bg-white border border-lumiere-ink/15 rounded-lg px-2 py-1.5 text-xs" />
                          </div>
                        </div>
                        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-lumiere-ink/10">
                          <button data-testid={`social-schedule-${p.id}`} onClick={() => doSchedule(p)} disabled={working[p.id] === "schedule"}
                            className="inline-flex items-center gap-1.5 border border-lumiere-gold text-lumiere-ink hover:bg-lumiere-gold/15 px-3 py-1.5 rounded-full font-mono text-[0.6rem] uppercase tracking-widest transition-colors">
                            {working[p.id] === "schedule" ? <Loader2 size={12} className="animate-spin" /> : <CalendarClock size={12} />} {g(T.schedule, lang)}
                          </button>
                          <button data-testid={`social-publish-${p.id}`} onClick={() => doPublish(p.id)} disabled={working[p.id] === "publish"}
                            className="inline-flex items-center gap-1.5 bg-lumiere-ink text-lumiere-ivory hover:bg-lumiere-ink/85 px-3 py-1.5 rounded-full font-mono text-[0.6rem] uppercase tracking-widest transition-colors">
                            {working[p.id] === "publish" ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />} {g(T.publish, lang)}
                          </button>
                          <button data-testid={`social-delete-${p.id}`} onClick={() => del(p.id)} className="ml-auto text-lumiere-ink/40 hover:text-red-600 transition-colors"><Trash2 size={15} /></button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </main>
      {editing && <SocialImageEditor post={editing} lang={lang} onDone={loadPosts} onClose={() => setEditing(null)} />}
    </div>
  );
}
