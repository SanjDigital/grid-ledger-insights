import { type StreakDay } from "@/lib/mock-data";
import { Shield, AlertTriangle } from "lucide-react";

interface StreakHeaderProps {
  days: StreakDay[];
  isRedAlert: boolean;
}

export function StreakHeader({ days, isRedAlert }: StreakHeaderProps) {
  const sovereignCount = days.filter(d => d.status === "sovereign").length;

  return (
    <div className={`p-5 border-b border-border ${isRedAlert ? "red-alert-bg" : ""}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {isRedAlert ? (
            <AlertTriangle className="w-5 h-5 text-destructive animate-pulse-glow" />
          ) : (
            <Shield className="w-5 h-5 text-primary" />
          )}
          <div>
            <h2 className="text-lg font-semibold tracking-tight text-foreground leading-none">
              30-Day Integrity Streak
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5 font-mono">
              {sovereignCount}/30 Sovereign · {isRedAlert ? "ALERT ACTIVE" : "Nominal"}
            </p>
          </div>
        </div>
        <div className={`px-3 py-1.5 rounded text-xs font-mono font-semibold ${
          isRedAlert ? "badge-gap" : "badge-sovereign"
        }`}>
          {isRedAlert ? "RED ALERT" : "SOVEREIGN"}
        </div>
      </div>

      <div className="flex gap-1">
        {days.map((d) => (
          <div
            key={d.day}
            title={`Day ${d.day}: ${d.status}`}
            className={`h-6 flex-1 rounded-sm transition-all duration-200 ${
              d.status === "sovereign" ? "pip-sovereign" :
              d.status === "review" ? "pip-review" :
              d.status === "gap" ? "pip-gap" :
              "pip-empty"
            }`}
          />
        ))}
      </div>

      <div className="flex gap-4 mt-3">
        {[
          { label: "Sovereign", cls: "pip-sovereign" },
          { label: "Under Review", cls: "pip-review" },
          { label: "Gap Detected", cls: "pip-gap" },
          { label: "Pending", cls: "pip-empty" },
        ].map(l => (
          <div key={l.label} className="flex items-center gap-1.5">
            <span className={`w-2 h-2 rounded-sm ${l.cls}`} />
            <span className="text-[10px] text-muted-foreground font-mono">{l.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
