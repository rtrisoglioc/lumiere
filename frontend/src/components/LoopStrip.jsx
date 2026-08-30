import { useI18n } from "@/i18n";

const STEPS = ["INTENT", "STORY", "DIRECT", "CAPTURE", "UNDERSTAND", "EVALUATE",
  "DETECT GAP", "GET THE SHOT", "CAPTURE AGAIN", "RE-EVALUATE", "EDIT", "LEARN"];

export function LoopStrip({ dark = false }) {
  const color = dark ? "text-lumiere-ivory/50" : "text-lumiere-ink/45";
  const seq = [...STEPS, ...STEPS];
  return (
    <div className="w-full overflow-hidden py-3 border-y border-current/10" data-testid="loop-strip">
      <div className="marquee-track">
        {seq.map((s, i) => (
          <span key={i} className={`font-mono text-[0.7rem] uppercase tracking-[0.25em] ${color} px-4`}>
            {s}<span className="text-lumiere-gold px-4">/</span>
          </span>
        ))}
      </div>
    </div>
  );
}
