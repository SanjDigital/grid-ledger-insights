interface TrustGaugeProps {
  score: number;
  isRedAlert: boolean;
}

function getTierLabel(score: number): { tier: string; range: string } {
  if (score >= 85) return { tier: "INSTITUTIONAL", range: "85–100" };
  if (score >= 70) return { tier: "COMMERCIAL", range: "70–84" };
  if (score >= 50) return { tier: "SUBPRIME", range: "50–69" };
  return { tier: "HIGH RISK", range: "<50" };
}

export function TrustGauge({ score, isRedAlert }: TrustGaugeProps) {
  const percentage = score;
  const circumference = 2 * Math.PI * 54;
  const dashOffset = circumference - (percentage / 100) * circumference;
  const { tier, range } = getTierLabel(score);

  const color = isRedAlert
    ? "hsl(var(--gap-detected))"
    : score >= 85
    ? "hsl(var(--sovereign))"
    : score >= 70
    ? "hsl(var(--under-review))"
    : "hsl(var(--gap-detected))";

  return (
    <div className="flex flex-col items-center py-4">
      <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-4">
        L5 · Trust Integrity Score
      </p>

      <div className="relative w-36 h-36">
        <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="54" fill="none" stroke="hsl(var(--border))" strokeWidth="6" />
          <circle
            cx="60" cy="60" r="54" fill="none"
            stroke={color}
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={dashOffset}
            className="transition-all duration-1000 ease-out"
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={`text-3xl font-mono font-bold tabular ${
            isRedAlert ? "text-destructive" : score >= 85 ? "text-primary" : "text-[hsl(var(--under-review))]"
          }`}>
            {score.toFixed(0)}
          </span>
          <span className="text-[10px] text-muted-foreground font-mono">/100</span>
        </div>
      </div>

      <p className={`text-xs font-mono font-semibold mt-4 ${
        isRedAlert ? "text-destructive" : score >= 85 ? "text-primary" : "text-[hsl(var(--under-review))]"
      }`}>
        {tier}
      </p>
      <p className="text-[10px] text-muted-foreground mt-1 font-mono">Score Range: {range}</p>
    </div>
  );
}
