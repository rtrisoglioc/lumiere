import { useI18n } from "@/i18n";
import { bl } from "@/lib/bilingual";
import { Cpu, Plug, Activity, Search } from "lucide-react";

const AGENT_COLORS = {
  context: "text-lumiere-iris",
  director: "text-lumiere-orange",
  cinematographer: "text-amber-400",
  vision: "text-lumiere-cyan",
  evaluator: "text-fuchsia-400",
  editor: "text-emerald-400",
  reviser: "text-sky-400",
};

function ConnBadge({ ok, labelOk, labelNo }) {
  return (
    <span className={`inline-block px-2 py-0.5 border font-mono text-[0.6rem] uppercase tracking-widest ${ok ? "border-emerald-500/50 text-emerald-400" : "border-amber-500/40 text-amber-400"}`}>
      {ok ? labelOk : labelNo}
    </span>
  );
}

export function AgentTrace({ runs, agentHealth, partnerHealth }) {
  const { t, lang } = useI18n();
  const vertexOk = agentHealth?.vertex_connected;
  const abOk = agentHealth?.agent_builder_connected;
  const partnerOk = partnerHealth?.connected;

  return (
    <div className="space-y-6">
      <div className="grid sm:grid-cols-2 gap-4">
        {/* Google Cloud */}
        <div className="border border-white/10 bg-lumiere-surface p-4" data-testid="trace-google-card">
          <div className="flex items-center gap-2 mb-2">
            <Cpu size={15} className="text-lumiere-cyan" />
            <span className="label-mono text-lumiere-ivory/60">Google Cloud</span>
          </div>
          <p className="font-mono text-sm text-lumiere-ivory">{agentHealth?.model || "gemini"}</p>
          <p className="font-mono text-xs text-lumiere-ivory/40 mt-1">
            service: {agentHealth?.service} {agentHealth?.project ? `· ${agentHealth.project}` : ""} · {agentHealth?.location}
          </p>
          <div className="flex flex-wrap gap-2 mt-2">
            <ConnBadge ok={vertexOk} labelOk="Vertex AI: CONNECTED" labelNo="Vertex AI: NOT CONNECTED" />
            <ConnBadge ok={abOk} labelOk="Agent Builder: CONNECTED" labelNo="Agent Builder: NOT CONNECTED" />
          </div>
          <p className="text-xs text-lumiere-ivory/50 mt-2 leading-relaxed">{lang === "es" ? agentHealth?.note_es : agentHealth?.note_en}</p>
        </div>

        {/* Partner */}
        <div className="border border-white/10 bg-lumiere-surface p-4" data-testid="trace-partner-card">
          <div className="flex items-center gap-2 mb-2">
            <Plug size={15} className="text-lumiere-iris" />
            <span className="label-mono text-lumiere-ivory/60">{t("partner")} · Parallel</span>
          </div>
          <p className="font-mono text-sm text-lumiere-ivory">{partnerHealth?.product || "Parallel Search API"}</p>
          <p className="font-mono text-[0.65rem] text-lumiere-ivory/40 mt-1 break-all">{partnerHealth?.endpoint}</p>
          <div className="mt-2">
            <ConnBadge ok={partnerOk} labelOk="Parallel: CONNECTED" labelNo="Parallel: NOT CONNECTED" />
          </div>
          <p className="text-xs text-lumiere-ivory/50 mt-2 leading-relaxed">{lang === "es" ? partnerHealth?.message_es : partnerHealth?.message_en}</p>
        </div>
      </div>

      <div className="border border-white/10 bg-black/40">
        <div className="flex items-center gap-2 px-4 py-2 border-b border-white/10">
          <Activity size={14} className="text-lumiere-orange" />
          <span className="label-mono text-lumiere-ivory/60">{t("agentTrace")}</span>
        </div>
        <div className="divide-y divide-white/5 max-h-[440px] overflow-auto">
          {(!runs || runs.length === 0) && (
            <p className="p-4 font-mono text-xs text-lumiere-ivory/40">{t("noRuns")}</p>
          )}
          {runs?.map((r) => {
            const isPartner = r.service === "parallel";
            const statusColor = r.status === "ok" ? "text-emerald-400" : r.status === "not_connected" ? "text-amber-400" : "text-red-400";
            return (
              <div key={r.id} className="px-4 py-3 font-mono text-xs" data-testid={`agent-run-${r.agent}`}>
                <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                  <span className={`font-bold uppercase tracking-widest ${AGENT_COLORS[r.agent] || "text-white"}`}>
                    {r.agent}{isPartner && <Search size={11} className="inline ml-1 -mt-0.5" />}
                  </span>
                  <span className="text-lumiere-ivory/40">svc: <span className="text-lumiere-cyan">{r.service}</span></span>
                  <span className="text-lumiere-ivory/40">op: <span className="text-lumiere-ivory/80">{r.operation}</span></span>
                  <span className="text-lumiere-ivory/40">status: <span className={statusColor}>{r.status}</span></span>
                  {r.latency_ms != null && <span className="text-lumiere-ivory/40">{t("latency")}: <span className="text-lumiere-ivory">{r.latency_ms}ms</span></span>}
                  <span className="text-lumiere-ivory/40">{t("confidence")}: <span className="text-lumiere-cyan">{Math.round((r.confidence || 0) * 100)}%</span></span>
                </div>
                <div className="flex flex-wrap items-center gap-x-4 mt-1 text-lumiere-ivory/40">
                  <span>run: {(r.correlation_id || r.id || "").slice(0, 8)}</span>
                  <span>{r.provider}/{(r.model || "").split(":")[0]}</span>
                  <span className="text-lumiere-ivory/30">{(r.timestamp || r.created_at || "").slice(11, 19)}</span>
                </div>
                <p className="text-lumiere-ivory/50 mt-1 truncate">↳ {r.input_summary}</p>
                {r.evidence?.length > 0 && (
                  <p className="text-lumiere-ivory/40 mt-0.5 truncate">evidence: {r.evidence.map((e, i) => (
                    <span key={i}>{e.url ? e.url : e.note ? bl(e.note, lang) : JSON.stringify(e)} </span>
                  ))}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
