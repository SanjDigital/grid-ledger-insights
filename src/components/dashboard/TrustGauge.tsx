interface TrustGaugeProps {
  score: number;
  isRedAlert: boolean;
}

export function TrustGauge({ score, isRedAlert }: TrustGaugeProps) {
  const percentage = score;
  const circumference = 2 * Math.PI * 54;
  const dashOffset = circumference - (percentage / 100) * circumference;
  const color = isRedAlert ? "hsl(var(--gap-detected))" : "hsl(var(--sovereign))";

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
          <span className={`text-3xl font-mono font-bold tabular ${isRedAlert ? "text-destructive" : "text-primary"}`}>
            {score.toFixed(1)}
          </span>
          <span className="text-[10px] text-muted-foreground font-mono">/100</span>
        </div>
      </div>

      <p className="text-xs text-muted-foreground mt-4 font-mono">Target: 98.2/100</p>
      <p className={`text-xs font-semibold mt-1 ${isRedAlert ? "text-destructive" : "text-primary"}`}>
        {score >= 98 ? "EXCEEDS TARGET" : score >= 95 ? "ON TARGET" : "BELOW THRESHOLD"}
      </p>
    </div>
  );
}
