interface TrustGaugeProps {
  score: number;
  isRedAlert: boolean;
  ear?: number;
}

// Bounded Imperfection Doctrine — tiers anchored to EAR (accountable energy %)
function getEarTier(ear: number): { tier: string; range: string } {
  if (ear >= 95) return { tier: "INSTITUTIONAL", range: "EAR ≥ 95%" };
  if (ear >= 90) return { tier: "COMMERCIAL", range: "EAR 90–95%" };
  if (ear >= 80) return { tier: "SUBPRIME", range: "EAR 80–90%" };
  return { tier: "HIGH RISK", range: "EAR < 80%" };
}

export function TrustGauge({ score, isRedAlert, ear }: TrustGaugeProps) {
  const percentage = score;
  const circumference = 2 * Math.PI * 54;
  const dashOffset = circumference - (percentage / 100) * circumference;
  const effectiveEar = ear ?? score;
  const { tier, range } = getEarTier(effectiveEar);
  const tierColorVar = isRedAlert
    ? "--gap-detected"
    : effectiveEar >= 95
    ? "--sovereign"
    : effectiveEar >= 90
    ? "--under-review"
    : "--gap-detected";

  const color = `hsl(var(${tierColorVar}))`;
  const tierTextClass = `text-[hsl(var(${tierColorVar}))]`;

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
          <span className={`text-3xl font-mono font-bold tabular ${tierTextClass}`}>
            {score.toFixed(0)}
          </span>
          <span className="text-[10px] text-muted-foreground font-mono">/100</span>
        </div>
      </div>

      <p className={`text-xs font-mono font-semibold mt-4 ${tierTextClass}`}>
        {tier}
      </p>
      <p className="text-[10px] text-muted-foreground mt-1 font-mono">{range} · Bounded Imperfection</p>
    </div>
  );
}
