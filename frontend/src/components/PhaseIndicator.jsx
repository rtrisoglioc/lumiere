import { Compass, Radio, Clapperboard } from "lucide-react";

const PHASES = [
  { key: "before", label: "Before", sub: "Plan the story", icon: Compass, color: "lumiere-gold" },
  { key: "during", label: "During", sub: "Direct the capture", icon: Radio, color: "lumiere-iris" },
  { key: "after", label: "After", sub: "Understand & edit", icon: Clapperboard, color: "lumiere-sage" },
];

export function PhaseIndicator({ phase = "before" }) {
  const idx = PHASES.findIndex((p) => p.key === phase);
  return (
    <div className="flex items-center gap-1.5 sm:gap-3" data-testid="phase-indicator" data-phase={phase}>
      {PHASES.map((p, i) => {
        const active = i === idx;
        const done = i < idx;
        const Icon = p.icon;
        return (
          <div key={p.key} className="flex items-center gap-1.5 sm:gap-3">
            <div data-testid={`phase-${p.key}`}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-full border transition-all duration-300 ${
                active ? "border-lumiere-ink bg-lumiere-ink text-lumiere-ivory shadow-md"
                : done ? "border-lumiere-ink/20 text-lumiere-ink/50 bg-lumiere-ink/5"
                : "border-lumiere-ink/15 text-lumiere-ink/35"}`}>
              <Icon size={14} />
              <div className="hidden sm:block leading-none">
                <span className="font-mono text-[0.6rem] uppercase tracking-widest block">{p.label}</span>
                {active && <span className="text-[0.55rem] opacity-70">{p.sub}</span>}
              </div>
              <span className="sm:hidden font-mono text-[0.6rem] uppercase tracking-widest">{p.label}</span>
            </div>
            {i < PHASES.length - 1 && <div className={`h-px w-4 sm:w-8 ${i < idx ? "bg-lumiere-ink/30" : "bg-lumiere-ink/10"}`} />}
          </div>
        );
      })}
    </div>
  );
}
