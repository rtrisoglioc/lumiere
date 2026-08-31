import { useEffect, useState, useCallback } from "react";
import { Compass, ArrowRight, Loader2, ShieldAlert } from "lucide-react";
import { api } from "@/lib/api";
import { bl } from "@/lib/bilingual";

const ACTION_TAB = {
  create_plan: "story", capture: "capture", wait_analysis: "capture",
  evaluate: "evaluate", get_the_shot: "evaluate", create_cut: "edit",
  deliver: "edit", refine: "edit", recover_impacted: "edit",
};
const ACTION_CTA = {
  create_plan: { en: "Set the intent", es: "Definir intención" },
  capture: { en: "Capture footage", es: "Capturar material" },
  wait_analysis: { en: "View analysis", es: "Ver análisis" },
  evaluate: { en: "Evaluate coverage", es: "Evaluar cobertura" },
  get_the_shot: { en: "Get the shot", es: "Conseguir la toma" },
  create_cut: { en: "Create the cut", es: "Crear el corte" },
  deliver: { en: "Open the cut", es: "Abrir el corte" },
  refine: { en: "Refine the cut", es: "Refinar el corte" },
  recover_impacted: { en: "Resolve impacted cut", es: "Resolver corte afectado" },
};

export function OrchestratorPanel({ expId, lang, onGoTab, refreshKey }) {
  const [d, setD] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await api.get(`/experiences/${expId}/orchestrator`);
      setD(r.data);
    } catch { /* */ } finally { setLoading(false); }
  }, [expId]);

  useEffect(() => { load(); }, [load, refreshKey]);

  if (loading || !d) {
    return (
      <div className="border border-lumiere-iris/30 bg-lumiere-iris/5 p-5 mb-6 flex items-center gap-3" data-testid="orchestrator-loading">
        <Loader2 size={16} className="animate-spin text-lumiere-iris" />
        <span className="font-mono text-xs uppercase tracking-widest text-lumiere-iris">Orchestrator…</span>
      </div>
    );
  }

  const pct = Math.round((d.story_completeness || 0) * 100);
  const tab = ACTION_TAB[d.next_action] || "story";
  const cta = ACTION_CTA[d.next_action] || { en: "Continue", es: "Continuar" };

  return (
    <div data-testid="orchestrator-panel"
      className="relative border border-lumiere-iris/40 bg-gradient-to-br from-lumiere-iris/10 to-transparent p-6 mb-6 overflow-hidden">
      <div className="flex items-start gap-4">
        <span className="w-11 h-11 rounded-full bg-lumiere-iris/20 border border-lumiere-iris/50 flex items-center justify-center shrink-0">
          <Compass size={20} className="text-lumiere-iris" />
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[0.6rem] uppercase tracking-[0.2em] text-lumiere-iris">LUMIÈRE DIRECTS</span>
            {d.user_approval_required && (
              <span className="inline-flex items-center gap-1 font-mono text-[0.55rem] uppercase tracking-widest text-amber-400 border border-amber-400/40 rounded-full px-2 py-0.5">
                <ShieldAlert size={10} /> {lang === "es" ? "Tu decisión" : "Your call"}
              </span>
            )}
          </div>
          <p className="text-white text-lg mt-1 leading-snug" data-testid="orchestrator-reason">{bl(d.reason, lang)}</p>
          <p className="text-zinc-400 text-sm mt-1 font-mono">{bl(d.required_input, lang)}</p>

          <div className="flex flex-wrap items-center gap-4 mt-4">
            <button data-testid="orchestrator-cta" onClick={() => onGoTab?.(tab)}
              className="inline-flex items-center gap-2 bg-lumiere-iris hover:bg-lumiere-irisHover text-white px-5 py-2.5 font-mono text-xs uppercase tracking-widest transition-colors">
              {bl(cta, lang)} <ArrowRight size={14} />
            </button>
            <div className="flex-1 min-w-[160px]">
              <div className="flex items-center justify-between font-mono text-[0.6rem] uppercase tracking-widest text-zinc-500 mb-1">
                <span>{lang === "es" ? "Completitud" : "Completeness"}</span>
                <span className="text-lumiere-iris" data-testid="orchestrator-completeness">{pct}%</span>
              </div>
              <div className="h-1.5 bg-white/10 overflow-hidden rounded-full">
                <div className="h-full bg-lumiere-iris rounded-full" style={{ width: `${pct}%`, transition: "width 0.6s ease" }} />
              </div>
            </div>
          </div>

          <div className="flex flex-wrap gap-2 mt-4">
            {(d.evidence || []).map((e, i) => (
              <span key={i} className="font-mono text-[0.6rem] text-zinc-400 border border-white/10 px-2 py-1">
                {e.metric}: {typeof e.value === "number" ? e.value : String(e.value)}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
