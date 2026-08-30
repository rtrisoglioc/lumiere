import { useI18n } from "@/i18n";

const STAGES = ["uploading", "processing", "analyzing", "analyzed"];
const MAP = { processing: 1, analyzed: 3, failed: -1 };

export function StatusBadge({ status }) {
  const { t } = useI18n();
  const map = {
    processing: { txt: t("processing"), cls: "text-lumiere-cyan border-lumiere-cyan/40" },
    analyzing: { txt: t("analyzing"), cls: "text-lumiere-cyan border-lumiere-cyan/40" },
    analyzed: { txt: t("analyzed"), cls: "text-emerald-400 border-emerald-500/40" },
    failed: { txt: t("failed"), cls: "text-red-400 border-red-500/40" },
    rendering: { txt: t("rendering"), cls: "text-lumiere-cyan border-lumiere-cyan/40" },
    ready: { txt: t("cutReady"), cls: "text-emerald-400 border-emerald-500/40" },
  };
  const s = map[status] || map.processing;
  const pulse = status === "processing" || status === "analyzing" || status === "rendering";
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 border font-mono text-[0.62rem] uppercase tracking-widest ${s.cls}`} data-testid="status-badge">
      {pulse && <span className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" />}
      {s.txt}
    </span>
  );
}

export function ProcessTimeline({ status }) {
  const active = MAP[status] ?? 0;
  return (
    <div className="flex items-center gap-1 mt-2">
      {STAGES.map((s, i) => (
        <div key={s} className={`h-0.5 flex-1 ${active < 0 ? "bg-red-500/50" : i <= active ? "bg-lumiere-orange" : "bg-white/10"}`} />
      ))}
    </div>
  );
}
