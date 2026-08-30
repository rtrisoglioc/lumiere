import { useI18n } from "@/i18n";
import { bl } from "@/lib/bilingual";
import { Cpu, Plug, Activity } from "lucide-react";

const AGENT_COLORS = {
  director: "text-lumiere-orange",
  cinematographer: "text-amber-400",
  vision: "text-lumiere-cyan",
  evaluator: "text-fuchsia-400",
  editor: "text-emerald-400",
  reviser: "text-sky-400",
};

export function AgentTrace({ runs, agentHealth, partnerHealth }) {
  const { t, lang } = useI18n();
  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 gap-4">
        <div className="border border-white/10 bg-lumiere-surface p-4">
          <div className="flex items-center gap-2 mb-2">
            <Cpu size={15} className="text-lumiere-cyan" />
            <span className="label-mono">{t("orchestration")}</span>
          </div>
          <p className="font-mono text-sm text-white">{agentHealth?.model || "gemini"}</p>
          <p className="font-mono text-xs text-zinc-500 mt-1">backend: {agentHealth?.orchestration_backend}</p>
          <span className="inline-block mt-2 px-2 py-0.5 border border-amber-500/40 text-amber-400 font-mono text-[0.6rem] uppercase tracking-widest">
            Agent Builder: {t("notConnected")}
          </span>
          <p className="text-xs text-zinc-500 mt-2 leading-relaxed">{lang === "es" ? agentHealth?.note_es : agentHealth?.note_en}</p>
        </div>
        <div className="border border-white/10 bg-lumiere-surface p-4">
          <div className="flex items-center gap-2 mb-2">
            <Plug size={15} className="text-lumiere-cyan" />
            <span className="label-mono">{t("partner")}</span>
          </div>
          <p className="font-mono text-sm text-white">{partnerHealth?.selected_track || "—"}</p>
          <span className="inline-block mt-2 px-2 py-0.5 border border-amber-500/40 text-amber-400 font-mono text-[0.6rem] uppercase tracking-widest">
            {t("mock")} · {t("notConnected")}
          </span>
          <p className="text-xs text-zinc-500 mt-2 leading-relaxed">{lang === "es" ? partnerHealth?.message_es : partnerHealth?.message_en}</p>
        </div>
      </div>

      <div className="border border-white/10 bg-black/40">
        <div className="flex items-center gap-2 px-4 py-2 border-b border-white/10">
          <Activity size={14} className="text-lumiere-orange" />
          <span className="label-mono">{t("agentTrace")}</span>
        </div>
        <div className="divide-y divide-white/5 max-h-[420px] overflow-auto">
          {(!runs || runs.length === 0) && (
            <p className="p-4 font-mono text-xs text-zinc-600">{t("noRuns")}</p>
          )}
          {runs?.map((r) => (
            <div key={r.id} className="px-4 py-3 font-mono text-xs" data-testid={`agent-run-${r.agent}`}>
              <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                <span className={`font-bold uppercase tracking-widest ${AGENT_COLORS[r.agent] || "text-white"}`}>{r.agent}</span>
                <span className="text-zinc-500">{t("latency")}: <span className="text-white">{r.latency_ms}ms</span></span>
                <span className="text-zinc-500">{t("confidence")}: <span className="text-lumiere-cyan">{Math.round((r.confidence || 0) * 100)}%</span></span>
                <span className="text-zinc-600 ml-auto">{r.provider}/{r.model?.split("-")[0]}</span>
              </div>
              <p className="text-zinc-500 mt-1 truncate">↳ {r.input_summary}</p>
              {r.evidence?.length > 0 && (
                <p className="text-zinc-600 mt-0.5">evidence: {r.evidence.map((e, i) => (
                  <span key={i}>{e.note ? bl(e.note, lang) : JSON.stringify(e)} </span>
                ))}</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
