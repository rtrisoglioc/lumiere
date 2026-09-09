import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import {
  ArrowRight, Play, Search, Brain, GitBranch, Sparkles, Check, Star,
  Film, Scissors, Languages, Eye, ChevronRight,
} from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useI18n } from "@/i18n";
import { LanguageToggle } from "@/components/LanguageToggle";
import { LoopStrip } from "@/components/LoopStrip";
import {
  Accordion, AccordionItem, AccordionTrigger, AccordionContent,
} from "@/components/ui/accordion";

const IMG = {
  hero: "https://images.unsplash.com/photo-1644468840310-bf700317c1d0?crop=entropy&cs=srgb&fm=jpg&w=1400&q=85",
  laptop: "https://images.unsplash.com/photo-1531297484001-80022131f5a1?crop=entropy&cs=srgb&fm=jpg&w=1200&q=85",
  t1: "https://images.unsplash.com/photo-1674507887380-f82e9a1eae1a?crop=entropy&cs=srgb&fm=jpg&w=700&q=85",
  t2: "https://images.unsplash.com/photo-1619105182220-b2bb0459c53e?crop=entropy&cs=srgb&fm=jpg&w=700&q=85",
  t3: "https://images.unsplash.com/photo-1674507887725-c50a7c844d7a?crop=entropy&cs=srgb&fm=jpg&w=700&q=85",
};

const L = {
  navStudio: { en: "Studio", es: "Estudio" },
  navAgent: { en: "Agents", es: "Agentes" },
  navPricing: { en: "Pricing", es: "Precios" },
  signIn: { en: "Sign in", es: "Entrar" },
  kicker: { en: "Agentic Experience Studio", es: "Estudio de Experiencias Agéntico" },
  heroSub: {
    en: "Other AI tools edit what you captured. LUMIÈRE understands the story you want, then directs you to capture cinema.",
    es: "Otras herramientas de IA editan lo que capturaste. LUMIÈRE entiende la historia que quieres y te dirige para capturar cine.",
  },
  ctaGoogle: { en: "Continue with Google", es: "Continuar con Google" },
  ctaWatch: { en: "Watch the loop", es: "Ver el loop" },
  searchPlaceholder: { en: "Describe the story you lived…", es: "Describe la historia que viviste…" },
  gapKicker: { en: "The Narrative Gap", es: "La Brecha Narrativa" },
  gapTitle: { en: "The Narrative Gap", es: "La Brecha Narrativa" },
  gapLead: {
    en: "Your footage is a collection of moments. Understanding turns it into a film — by knowing the intent before you press record.",
    es: "Tu material es una colección de momentos. La comprensión lo convierte en película — sabiendo la intención antes de grabar.",
  },
  gapProblemTitle: { en: "Without direction", es: "Sin dirección" },
  gapP1: { en: "Hours spent scrubbing through irrelevant clips", es: "Horas revisando clips irrelevantes" },
  gapP2: { en: "The original emotion gets lost in the edit", es: "La emoción original se pierde en la edición" },
  gapP3: { en: "Manual storytelling, mapping and busywork", es: "Narrativa manual, mapeo y trabajo tedioso" },
  gapSolTitle: { en: "Storytelling directed by context, not just content", es: "Narrativa dirigida por contexto, no solo contenido" },
  gapS1t: { en: "Real-time Narrative Analysis", es: "Análisis Narrativo en Tiempo Real" },
  gapS1d: { en: "Multimodal understanding of every second of footage", es: "Comprensión multimodal de cada segundo de material" },
  gapS2t: { en: "Automated Continuity Engine", es: "Motor de Continuidad Automatizado" },
  gapS2d: { en: "Detects gaps and tells you what to shoot next", es: "Detecta gaps y te dice qué grabar después" },
  gapS3t: { en: "Predictive Story Arcing", es: "Arco Narrativo Predictivo" },
  gapS3d: { en: "Agentic beats mapped to real cinematic structure", es: "Beats agénticos mapeados a estructura cinematográfica real" },
  gapExplore: { en: "Explore the process", es: "Explorar el proceso" },
  flowKicker: { en: "The Workflow", es: "El Flujo" },
  flowTitle: { en: "From Capture to Cinema", es: "De Captura a Cine" },
  flowLead: {
    en: "A four-step agentic journey. What you lived becomes a polished, provable narrative.",
    es: "Un viaje agéntico de cuatro pasos. Lo que viviste se vuelve una narrativa pulida y demostrable.",
  },
  f1t: { en: "Intent & Index", es: "Intención e Índice" },
  f1d: { en: "Capture your intent; the crew indexes every moment of raw footage", es: "Captura tu intención; el equipo indexa cada momento del material" },
  f2t: { en: "Detect Narrative Gap", es: "Detectar Brecha Narrativa" },
  f2d: { en: "Coverage is scored and missing shots surface instantly", es: "Se puntúa la cobertura y las tomas faltantes aparecen al instante" },
  f3t: { en: "Cinematic Synthesis", es: "Síntesis Cinematográfica" },
  f3d: { en: "A real FFmpeg cut is rendered from usable segments", es: "Un corte real de FFmpeg se renderiza desde segmentos usables" },
  f4t: { en: "Bilingual Export", es: "Exportación Bilingüe" },
  f4d: { en: "Conversational re-edit and export, ES/EN native", es: "Re-edición conversacional y exportación, ES/EN nativo" },
  crewKicker: { en: "Meet Your Crew", es: "Conoce tu Equipo" },
  crewTitle: { en: "Narrative Co-Pilots", es: "Co-Pilotos Narrativos" },
  crewLead: {
    en: "Your production, backed by a specialized crew of agents — each purposefully tuned for a specific cinematic decision.",
    es: "Tu producción, respaldada por un equipo especializado de agentes — cada uno afinado para una decisión cinematográfica específica.",
  },
  crew1n: { en: "Director", es: "Director" }, crew1r: { en: "Intent Lead", es: "Líder de Intención" },
  crew1d: { en: "Turns raw intent into a tight story plan with beats and tone", es: "Convierte la intención en un plan de historia con beats y tono" },
  crew2n: { en: "Cinematographer", es: "Cinematógrafo" }, crew2r: { en: "Capture Specialist", es: "Especialista de Captura" },
  crew2d: { en: "Converts beats into prioritized, filmable shot missions", es: "Convierte beats en misiones de toma priorizadas y grabables" },
  crew3n: { en: "Evaluator", es: "Evaluador" }, crew3r: { en: "Coverage Architect", es: "Arquitecto de Cobertura" },
  crew3d: { en: "Scores completeness and detects the shots you still need", es: "Puntúa la completitud y detecta las tomas que aún faltan" },
  bandTitle: { en: "Detecting what's missing before it's gone.", es: "Detectando lo que falta antes de que se pierda." },
  bandSub: {
    en: "GET THE SHOT missions send you back into the moment with exact, filmable direction — while it still exists.",
    es: "Las misiones CONSIGUE LA TOMA te devuelven al momento con dirección exacta y grabable — mientras aún existe.",
  },
  speakKicker: { en: "Global Cinema", es: "Cine Global" },
  speakTitle: { en: "Speak the World's Cinema", es: "Habla el Cine del Mundo" },
  speakLead: {
    en: "Every story is born bilingual. LUMIÈRE writes premise, beats and captions in natural English and Spanish.",
    es: "Cada historia nace bilingüe. LUMIÈRE escribe premisa, beats y subtítulos en inglés y español natural.",
  },
  speakQ1: { en: "A quiet morning that becomes a spontaneous road trip.", es: "Una mañana tranquila que se vuelve un viaje espontáneo." },
  speakF1t: { en: "Native Bilingual", es: "Bilingüe Nativo" },
  speakF1d: { en: "ES/EN generated together, never machine-translated after", es: "ES/EN generados juntos, nunca traducidos por máquina" },
  speakF2t: { en: "Cultural Tone", es: "Tono Cultural" },
  speakF2d: { en: "Tone and idiom tuned per language, not literal", es: "Tono e idioma afinados por lengua, no literal" },
  pricingKicker: { en: "Studio Membership", es: "Membresía del Estudio" },
  pricingTitle: { en: "Studio Membership", es: "Membresía del Estudio" },
  pricingLead: {
    en: "Choose the scale of agentic partnership that suits your creative pace.",
    es: "Elige la escala de colaboración agéntica que se ajusta a tu ritmo creativo.",
  },
  faqKicker: { en: "FAQ", es: "FAQ" },
  faqTitle: { en: "Questions & Insight", es: "Preguntas y Claridad" },
  faq1q: { en: "How do the agents actually make decisions?", es: "¿Cómo toman decisiones los agentes?" },
  faq1a: { en: "Every stage runs on Google Gemini via Vertex AI, orchestrated as a specialized crew with full traceability.", es: "Cada etapa corre en Google Gemini vía Vertex AI, orquestada como un equipo especializado con trazabilidad total." },
  faq2q: { en: "Can I customize the aesthetic of the agents?", es: "¿Puedo personalizar la estética de los agentes?" },
  faq2a: { en: "Yes — tone, pace and style are driven by your intent and refined through conversational re-editing.", es: "Sí — tono, ritmo y estilo se guían por tu intención y se refinan con re-edición conversacional." },
  faq3q: { en: "Is my footage secure during processing?", es: "¿Mi material está seguro durante el procesamiento?" },
  faq3a: { en: "Originals are never destroyed, stored with checksums, private by default, and every edit is versioned.", es: "Los originales nunca se destruyen, se guardan con checksums, privados por defecto, y cada edición es versionada." },
  faq4q: { en: "How does Gap Detection handle rare shots?", es: "¿Cómo maneja la Detección de Gaps las tomas raras?" },
  faq4a: { en: "It prioritizes critical missing beats and gives you filmable direction to recapture them while possible.", es: "Prioriza los beats críticos faltantes y te da dirección grabable para recuperarlos mientras sea posible." },
  finalTitle: { en: "Your lived story, refined by agents.", es: "Tu historia vivida, refinada por agentes." },
  finalSub: { en: "No credit card. Direct your first film in minutes.", es: "Sin tarjeta. Dirige tu primera película en minutos." },
  footTagline: { en: "You live it. LUMIÈRE directs it.", es: "Tú lo vives. LUMIÈRE lo dirige." },
  footPlatform: { en: "Platform", es: "Plataforma" },
  footCompany: { en: "Company", es: "Compañía" },
  footLegal: { en: "Legal", es: "Legal" },
};

const PLANS = [
  {
    id: "free", name: "Free", price: "$0",
    tag: { en: "Direct your first stories", es: "Dirige tus primeras historias" },
    features: {
      en: ["Story planning & shot missions", "Detect Gap coverage", "Bilingual ES/EN", "No AI video generation"],
      es: ["Planeación de historia y misiones", "Cobertura Detect Gap", "Bilingüe ES/EN", "Sin generación de video IA"],
    },
    cta: { en: "Get started", es: "Empezar" },
  },
  {
    id: "creator", name: "Creator", price: "$49", rec: true,
    tag: { en: "Real AI video with Vertex Veo", es: "Video IA real con Vertex Veo" },
    features: {
      en: ["Everything in Free", "Golden-hour shot planning", "20 films / month", "Priority rendering"],
      es: ["Todo lo de Free", "Planificación con golden hour", "20 películas / mes", "Renderizado prioritario"],
    },
    cta: { en: "Get Creator", es: "Elegir Creator" },
  },
  {
    id: "studio", name: "Studio", price: "$149",
    tag: { en: "Full agentic loop", es: "Loop agéntico completo" },
    features: {
      en: ["Everything in Creator", "Expanded film quota", "Live Director + Veo reference shots", "Conversational re-editing"],
      es: ["Todo lo de Creator", "Cuota de películas ampliada", "Live Director + tomas de referencia Veo", "Re-edición conversacional"],
    },
    cta: { en: "Get Studio", es: "Elegir Studio" },
  },
];

export default function Landing() {
  const { user, loading, login } = useAuth();
  const { lang } = useI18n();
  const navigate = useNavigate();
  const g = (o) => o[lang];

  useEffect(() => { if (!loading && user) navigate("/studio", { replace: true }); }, [user, loading, navigate]);

  const fade = (d = 0) => ({
    initial: { opacity: 0, y: 24 }, whileInView: { opacity: 1, y: 0 },
    viewport: { once: true, margin: "-80px" }, transition: { duration: 0.7, delay: d },
  });

  return (
    <div className="min-h-screen bg-lumiere-ivory text-lumiere-ink font-body selection:bg-lumiere-gold/30" data-testid="landing-page">
      {/* NAV */}
      <header className="sticky top-0 z-50 backdrop-blur-xl bg-lumiere-ivory/70 border-b border-lumiere-ink/5">
        <div className="max-w-7xl mx-auto flex items-center justify-between px-6 md:px-12 py-4">
          <span className="font-display text-2xl font-black tracking-tight">LUMIÈRE</span>
          <nav className="hidden md:flex items-center gap-8 font-mono text-xs uppercase tracking-[0.18em] text-lumiere-ink/60">
            <a href="#process" className="hover:text-lumiere-ink transition-colors" data-testid="nav-process">{g(L.navStudio)}</a>
            <a href="#crew" className="hover:text-lumiere-ink transition-colors" data-testid="nav-crew">{g(L.navAgent)}</a>
            <a href="#pricing" className="hover:text-lumiere-ink transition-colors" data-testid="nav-pricing">{g(L.navPricing)}</a>
          </nav>
          <div className="flex items-center gap-4">
            <LanguageToggle />
            <button data-testid="nav-signin-button" onClick={login}
              className="hidden sm:inline-flex items-center gap-2 bg-lumiere-ink text-lumiere-ivory hover:bg-lumiere-ink/85 px-5 py-2.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              {g(L.signIn)}
            </button>
          </div>
        </div>
      </header>

      {/* HERO */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 pt-14 md:pt-20 pb-10 grid lg:grid-cols-[1.05fr_1fr] gap-12 items-center">
        <div>
          <motion.p {...fade()} className="font-mono text-xs uppercase tracking-[0.25em] text-lumiere-ink/50 mb-6">{g(L.kicker)}</motion.p>
          <motion.h1 {...fade(0.05)} className="font-display text-5xl sm:text-6xl lg:text-7xl font-black leading-[0.92] tracking-tighter">
            {lang === "es" ? <>Tú lo vives.<br />LUMIÈRE<br />lo dirige.</> : <>You live it.<br />LUMIÈRE<br />directs it.</>}
          </motion.h1>
          <motion.p {...fade(0.15)} className="mt-7 text-lg text-lumiere-ink/60 max-w-md leading-relaxed">{g(L.heroSub)}</motion.p>
          <motion.div {...fade(0.25)} className="mt-9 flex flex-wrap items-center gap-3">
            <button data-testid="hero-google-button" onClick={login}
              className="group inline-flex items-center gap-3 bg-lumiere-gold hover:bg-lumiere-goldHover text-lumiere-ink px-7 py-3.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              {g(L.ctaGoogle)} <ArrowRight size={15} className="group-hover:translate-x-1 transition-transform duration-300" />
            </button>
            <a href="#process" data-testid="hero-watch-button"
              className="inline-flex items-center gap-2 border border-lumiere-ink/20 hover:bg-lumiere-ink/5 px-6 py-3.5 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              <Play size={13} /> {g(L.ctaWatch)}
            </a>
          </motion.div>
        </div>

        <motion.div {...fade(0.2)} className="relative">
          <div className="relative rounded-3xl overflow-hidden border border-lumiere-ink/10 aspect-[4/5] shadow-[0_30px_80px_-40px_rgba(23,23,20,0.5)]">
            <img src={IMG.hero} alt="" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-lumiere-ink/70 via-transparent to-transparent" />
            <button className="absolute inset-0 m-auto w-16 h-16 rounded-full bg-lumiere-ivory/90 backdrop-blur flex items-center justify-center hover:scale-105 transition-transform" data-testid="hero-play">
              <Play size={22} className="text-lumiere-ink ml-1" fill="currentColor" />
            </button>
            <div className="absolute bottom-5 left-5">
              <span className="font-mono text-[0.6rem] uppercase tracking-[0.25em] text-lumiere-ivory/80">AGENTIC TRAILER 01</span>
            </div>
          </div>
          {/* floating search pill */}
          <div className="absolute -top-5 right-6 hidden md:flex items-center gap-3 bg-lumiere-warm border border-lumiere-ink/10 rounded-full pl-5 pr-2 py-2 shadow-[0_20px_50px_-30px_rgba(23,23,20,0.6)]">
            <Search size={15} className="text-lumiere-ink/40" />
            <span className="text-sm text-lumiere-ink/40 max-w-[180px] truncate">{g(L.searchPlaceholder)}</span>
            <span className="w-8 h-8 rounded-full bg-lumiere-ink flex items-center justify-center"><ArrowRight size={13} className="text-lumiere-ivory" /></span>
          </div>
        </motion.div>
      </section>

      <LoopStrip />

      {/* NARRATIVE GAP */}
      <section id="process" className="max-w-7xl mx-auto px-6 md:px-12 py-20 md:py-28">
        <motion.div {...fade()} className="text-center max-w-2xl mx-auto">
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-lumiere-ink/45 mb-3">{g(L.gapKicker)}</p>
          <h2 className="font-display text-4xl md:text-5xl font-black tracking-tight">{g(L.gapTitle)}</h2>
          <p className="mt-5 text-lumiere-ink/60 leading-relaxed">{g(L.gapLead)}</p>
        </motion.div>

        <div className="grid md:grid-cols-2 gap-6 mt-14 items-stretch">
          <motion.div {...fade(0.05)} className="rounded-2xl border border-lumiere-ink/10 bg-lumiere-warm overflow-hidden">
            <img src={IMG.laptop} alt="" className="w-full h-48 object-cover grayscale" />
            <div className="p-8">
              <p className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-ink/40 mb-4">{g(L.gapProblemTitle)}</p>
              <ul className="space-y-4">
                {[L.gapP1, L.gapP2, L.gapP3].map((x, i) => (
                  <li key={i} className="flex items-start gap-3 text-lumiere-ink/70">
                    <span className="mt-2 w-1.5 h-1.5 rounded-full bg-lumiere-ink/30 shrink-0" /> {g(x)}
                  </li>
                ))}
              </ul>
            </div>
          </motion.div>

          <motion.div {...fade(0.1)} className="rounded-2xl bg-lumiere-ink text-lumiere-ivory p-8 flex flex-col">
            <p className="font-mono text-xs uppercase tracking-[0.2em] text-lumiere-gold mb-2">LUMIÈRE ENGINE</p>
            <h3 className="font-display text-2xl leading-snug mb-6">{g(L.gapSolTitle)}</h3>
            <div className="space-y-5 flex-1">
              {[[Brain, L.gapS1t, L.gapS1d], [GitBranch, L.gapS2t, L.gapS2d], [Sparkles, L.gapS3t, L.gapS3d]].map(([Icon, tt, dd], i) => (
                <div key={i} className="flex items-start gap-4">
                  <span className="w-9 h-9 rounded-lg bg-lumiere-iris/20 border border-lumiere-iris/40 flex items-center justify-center shrink-0">
                    <Icon size={16} className="text-lumiere-iris" />
                  </span>
                  <div>
                    <p className="font-body font-semibold">{g(tt)}</p>
                    <p className="text-sm text-lumiere-ivory/55">{g(dd)}</p>
                  </div>
                </div>
              ))}
            </div>
            <a href="#crew" data-testid="gap-explore" className="mt-7 inline-flex items-center gap-2 text-lumiere-gold font-mono text-xs uppercase tracking-widest hover:gap-3 transition-all">
              {g(L.gapExplore)} <ChevronRight size={14} />
            </a>
          </motion.div>
        </div>
      </section>

      {/* CAPTURE TO CINEMA */}
      <section className="bg-lumiere-warm border-y border-lumiere-ink/10">
        <div className="max-w-7xl mx-auto px-6 md:px-12 py-20 md:py-28 grid lg:grid-cols-2 gap-14 items-center">
          <motion.div {...fade()}>
            <p className="font-mono text-xs uppercase tracking-[0.25em] text-lumiere-ink/45 mb-3">{g(L.flowKicker)}</p>
            <h2 className="font-display text-4xl md:text-5xl font-black tracking-tight">{g(L.flowTitle)}</h2>
            <p className="mt-5 text-lumiere-ink/60 max-w-md leading-relaxed">{g(L.flowLead)}</p>
            <div className="mt-10 space-y-7">
              {[[L.f1t, L.f1d], [L.f2t, L.f2d], [L.f3t, L.f3d], [L.f4t, L.f4d]].map(([tt, dd], i) => (
                <div key={i} className="flex items-start gap-5 border-b border-lumiere-ink/10 pb-6 last:border-0">
                  <span className="font-mono text-sm text-lumiere-gold pt-1">0{i + 1}</span>
                  <div>
                    <p className="font-display text-xl">{g(tt)}</p>
                    <p className="text-sm text-lumiere-ink/55 mt-1">{g(dd)}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
          <motion.div {...fade(0.1)} className="relative rounded-3xl overflow-hidden border border-lumiere-ink/10 aspect-[4/3]">
            <img src={IMG.laptop} alt="" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-tr from-lumiere-ink/30 to-transparent" />
          </motion.div>
        </div>
      </section>

      {/* CREW */}
      <section id="crew" className="max-w-7xl mx-auto px-6 md:px-12 py-20 md:py-28">
        <motion.div {...fade()} className="text-center max-w-2xl mx-auto">
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-lumiere-ink/45 mb-3">{g(L.crewKicker)}</p>
          <h2 className="font-display text-4xl md:text-5xl font-black tracking-tight">{g(L.crewTitle)}</h2>
          <p className="mt-5 text-lumiere-ink/60 leading-relaxed">{g(L.crewLead)}</p>
        </motion.div>
        <div className="grid md:grid-cols-3 gap-6 mt-14">
          {[[IMG.t1, L.crew1n, L.crew1r, L.crew1d], [IMG.t2, L.crew2n, L.crew2r, L.crew2d], [IMG.t3, L.crew3n, L.crew3r, L.crew3d]].map(([img, n, r, d], i) => (
            <motion.div key={i} {...fade(i * 0.08)} className="group rounded-2xl border border-lumiere-ink/10 bg-lumiere-warm overflow-hidden hover:-translate-y-1 transition-transform">
              <div className="aspect-[4/5] overflow-hidden">
                <img src={img} alt="" className="w-full h-full object-cover grayscale group-hover:grayscale-0 transition-all duration-700" />
              </div>
              <div className="p-6">
                <div className="flex items-center justify-between">
                  <h3 className="font-display text-xl">{g(n)}</h3>
                  <span className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-gold">{g(r)}</span>
                </div>
                <p className="text-sm text-lumiere-ink/55 mt-2">{g(d)}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* DARK BAND */}
      <section className="bg-lumiere-ink text-lumiere-ivory">
        <div className="max-w-7xl mx-auto px-6 md:px-12 py-24 md:py-32 grid lg:grid-cols-2 gap-14 items-center">
          <motion.div {...fade()} className="relative rounded-3xl overflow-hidden border border-lumiere-ivory/10 aspect-video order-2 lg:order-1">
            <img src={IMG.hero} alt="" className="w-full h-full object-cover opacity-80" />
            <div className="absolute inset-0 bg-lumiere-ink/40" />
            <span className="absolute top-4 left-4 font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-gold border border-lumiere-gold/40 rounded-full px-3 py-1">DETECT GAP</span>
          </motion.div>
          <motion.div {...fade(0.1)} className="order-1 lg:order-2">
            <Eye size={28} className="text-lumiere-iris mb-6" />
            <h2 className="font-display text-4xl md:text-5xl font-black leading-[1.05] tracking-tight">{g(L.bandTitle)}</h2>
            <p className="mt-6 text-lumiere-ivory/60 max-w-md leading-relaxed">{g(L.bandSub)}</p>
          </motion.div>
        </div>
      </section>

      {/* SPEAK CINEMA */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 py-20 md:py-28 grid lg:grid-cols-2 gap-14 items-center">
        <motion.div {...fade()} className="relative">
          <div className="rounded-3xl overflow-hidden border border-lumiere-ink/10 aspect-[4/3]">
            <img src={IMG.laptop} alt="" className="w-full h-full object-cover" />
          </div>
          <div className="absolute -bottom-6 left-6 bg-lumiere-warm border border-lumiere-ink/10 rounded-xl px-5 py-4 shadow-lg max-w-xs">
            <p className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-gold mb-1">EN</p>
            <p className="font-display text-sm">{L.speakQ1.en}</p>
          </div>
          <div className="absolute -top-6 right-6 bg-lumiere-ink text-lumiere-ivory rounded-xl px-5 py-4 shadow-lg max-w-xs">
            <p className="font-mono text-[0.55rem] uppercase tracking-widest text-lumiere-gold mb-1">ES</p>
            <p className="font-display text-sm">{L.speakQ1.es}</p>
          </div>
        </motion.div>
        <motion.div {...fade(0.1)}>
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-lumiere-ink/45 mb-3">{g(L.speakKicker)}</p>
          <h2 className="font-display text-4xl md:text-5xl font-black tracking-tight">{g(L.speakTitle)}</h2>
          <p className="mt-5 text-lumiere-ink/60 max-w-md leading-relaxed">{g(L.speakLead)}</p>
          <div className="mt-8 space-y-5">
            {[[Languages, L.speakF1t, L.speakF1d], [Film, L.speakF2t, L.speakF2d]].map(([Icon, tt, dd], i) => (
              <div key={i} className="flex items-start gap-4">
                <span className="w-9 h-9 rounded-lg bg-lumiere-sage/15 border border-lumiere-sage/40 flex items-center justify-center shrink-0"><Icon size={16} className="text-lumiere-sage" /></span>
                <div><p className="font-body font-semibold">{g(tt)}</p><p className="text-sm text-lumiere-ink/55">{g(dd)}</p></div>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      {/* PRICING */}
      <section id="pricing" className="bg-lumiere-warm border-y border-lumiere-ink/10">
        <div className="max-w-6xl mx-auto px-6 md:px-12 py-20 md:py-28">
          <motion.div {...fade()} className="text-center max-w-2xl mx-auto">
            <p className="font-mono text-xs uppercase tracking-[0.25em] text-lumiere-ink/45 mb-3">{g(L.pricingKicker)}</p>
            <h2 className="font-display text-4xl md:text-5xl font-black tracking-tight">{g(L.pricingTitle)}</h2>
            <p className="mt-5 text-lumiere-ink/60">{g(L.pricingLead)}</p>
          </motion.div>
          <div className="grid md:grid-cols-3 gap-6 mt-14 items-start">
            {PLANS.map((p, i) => (
              <motion.div key={p.id} {...fade(i * 0.06)} data-testid={`landing-plan-${p.id}`}
                className={`relative rounded-2xl p-8 bg-lumiere-ivory border transition-transform hover:-translate-y-1 ${p.rec ? "border-lumiere-gold shadow-[0_20px_60px_-30px_rgba(214,168,95,0.6)] md:-mt-4 md:mb-4" : "border-lumiere-ink/10"}`}>
                {p.rec && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 inline-flex items-center gap-1 bg-lumiere-gold text-lumiere-ink px-3 py-1 rounded-full font-mono text-[0.6rem] uppercase tracking-widest">
                    <Star size={11} /> {g(L.pricingKicker) && (lang === "es" ? "Recomendado" : "Recommended")}
                  </span>
                )}
                <h3 className="font-display text-2xl">{p.name}</h3>
                <p className="text-sm text-lumiere-ink/55 mt-2 min-h-[2.5rem]">{g(p.tag)}</p>
                <div className="mt-5 flex items-end gap-1">
                  <span className="font-display text-4xl font-black">{p.price}</span>
                  {p.id !== "free" && <span className="font-mono text-sm text-lumiere-ink/50 mb-1">/mo</span>}
                </div>
                <ul className="mt-6 space-y-3">
                  {g(p.features).map((f, j) => (
                    <li key={j} className="flex items-start gap-2 text-sm"><Check size={16} className="text-lumiere-sage mt-0.5 shrink-0" /><span>{f}</span></li>
                  ))}
                </ul>
                <button data-testid={`landing-select-${p.id}`} onClick={login}
                  className={`mt-8 w-full py-3 rounded-full font-mono text-xs uppercase tracking-widest transition-colors ${p.rec ? "bg-lumiere-gold hover:bg-lumiere-goldHover text-lumiere-ink" : "bg-lumiere-ink hover:bg-lumiere-ink/85 text-lumiere-ivory"}`}>
                  {g(p.cta)}
                </button>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* FAQ */}
      <section className="max-w-3xl mx-auto px-6 md:px-12 py-20 md:py-28">
        <motion.div {...fade()} className="text-center mb-10">
          <p className="font-mono text-xs uppercase tracking-[0.25em] text-lumiere-ink/45 mb-3">{g(L.faqKicker)}</p>
          <h2 className="font-display text-4xl md:text-5xl font-black tracking-tight">{g(L.faqTitle)}</h2>
        </motion.div>
        <Accordion type="single" collapsible className="w-full">
          {[[L.faq1q, L.faq1a], [L.faq2q, L.faq2a], [L.faq3q, L.faq3a], [L.faq4q, L.faq4a]].map(([q, a], i) => (
            <AccordionItem key={i} value={`faq-${i}`} className="border-lumiere-ink/10">
              <AccordionTrigger data-testid={`landing-faq-${i}`} className="font-display text-lg text-left hover:no-underline">{g(q)}</AccordionTrigger>
              <AccordionContent className="text-lumiere-ink/60 leading-relaxed">{g(a)}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </section>

      {/* FINAL CTA */}
      <section className="max-w-7xl mx-auto px-6 md:px-12 pb-24">
        <motion.div {...fade()} className="rounded-3xl bg-lumiere-ink text-lumiere-ivory px-8 md:px-16 py-16 md:py-24 text-center relative overflow-hidden">
          <div className="absolute inset-0 opacity-[0.06]" style={{ backgroundImage: `url(${IMG.hero})`, backgroundSize: "cover", backgroundPosition: "center" }} />
          <div className="relative">
            <h2 className="font-display text-4xl md:text-6xl font-black tracking-tight max-w-3xl mx-auto leading-[1.02]">{g(L.finalTitle)}</h2>
            <button data-testid="final-google-button" onClick={login}
              className="mt-9 inline-flex items-center gap-3 bg-lumiere-gold hover:bg-lumiere-goldHover text-lumiere-ink px-8 py-4 rounded-full font-mono text-xs uppercase tracking-widest transition-colors">
              {g(L.ctaGoogle)} <ArrowRight size={15} />
            </button>
            <p className="mt-4 font-mono text-[0.65rem] uppercase tracking-widest text-lumiere-ivory/40">{g(L.finalSub)}</p>
          </div>
        </motion.div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-lumiere-ink/10">
        <div className="max-w-7xl mx-auto px-6 md:px-12 py-14 grid md:grid-cols-4 gap-10">
          <div>
            <span className="font-display text-2xl font-black tracking-tight">LUMIÈRE</span>
            <p className="text-sm text-lumiere-ink/50 mt-3 max-w-xs">{g(L.footTagline)}</p>
          </div>
          {[[L.footPlatform, [g(L.navStudio), g(L.navAgent), g(L.navPricing)]], [L.footCompany, ["About", "Careers", "Blog"]], [L.footLegal, ["Privacy", "Terms", "Security"]]].map(([head, items], i) => (
            <div key={i}>
              <p className="font-mono text-[0.6rem] uppercase tracking-[0.2em] text-lumiere-ink/40 mb-4">{g(head)}</p>
              <ul className="space-y-2">{items.map((it, j) => (<li key={j}><span className="text-sm text-lumiere-ink/60 hover:text-lumiere-ink transition-colors cursor-pointer">{it}</span></li>))}</ul>
            </div>
          ))}
        </div>
        <div className="border-t border-lumiere-ink/10 py-5 text-center">
          <p className="font-mono text-[0.6rem] uppercase tracking-widest text-lumiere-ink/40">© 2026 LUMIÈRE · Agentic Experience Studio</p>
        </div>
      </footer>
    </div>
  );
}
