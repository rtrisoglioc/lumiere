export function CircularScore({ value = 0, size = 132, label, testid }) {
  const pct = Math.round((value || 0) * 100);
  const r = (size - 16) / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <div className="relative inline-flex items-center justify-center" data-testid={testid}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#1c1c1c" strokeWidth="8" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke="#E55900" strokeWidth="8" fill="none"
          strokeDasharray={c} strokeDashoffset={offset} strokeLinecap="butt"
          style={{ transition: "stroke-dashoffset 1s ease-in-out" }} />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="font-mono text-3xl font-bold text-white">{pct}</span>
        {label && <span className="label-mono mt-1">{label}</span>}
      </div>
    </div>
  );
}

export function ScoreBar({ label, value = 0 }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="label-mono">{label}</span>
        <span className="font-mono text-xs text-lumiere-cyan">{pct}%</span>
      </div>
      <div className="h-1.5 bg-white/5">
        <div className="h-full bg-lumiere-orange" style={{ width: `${pct}%`, transition: "width 0.9s ease-in-out" }} />
      </div>
    </div>
  );
}
