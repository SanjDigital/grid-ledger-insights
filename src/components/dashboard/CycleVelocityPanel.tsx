import { useMemo } from "react";
import { VerifiedEvent } from "@/lib/mock-data";
import { getTurnoverInfo } from "@/lib/forensic-engine";
import { Activity, ArrowRightLeft } from "lucide-react";

interface CycleVelocityPanelProps {
  events: VerifiedEvent[];
}

export function CycleVelocityPanel({ events }: CycleVelocityPanelProps) {
  const turnoverData = useMemo(() => {
    const allTurnovers = events
      .map(getTurnoverInfo)
      .filter(info => info.hours !== null)
      .map(info => info.hours as number);

    const averageTurnover = allTurnovers.length > 0
      ? allTurnovers.reduce((sum, hours) => sum + hours, 0) / allTurnovers.length
      : 0;

    let avgClassification: ReturnType<typeof getTurnoverInfo>["classification"] = "STALLED";
    let avgColorClass = "text-muted-foreground";

    if (averageTurnover > 0) {
      if (averageTurnover < 12) { avgClassification = "FAST"; avgColorClass = "text-[hsl(var(--sovereign))]"; }
      else if (averageTurnover < 24) { avgClassification = "NORMAL"; avgColorClass = "text-[hsl(var(--under-review))]"; }
      else if (averageTurnover < 48) { avgClassification = "SLOW"; avgColorClass = "text-destructive"; }
    }

    const capitalEfficiencyMultiplier = averageTurnover > 0 ? (365 * 24) / averageTurnover / 52 : 0; // Assuming 52 weeks in a year, 24 hours a day
    const cyclesPerYear = averageTurnover > 0 ? (365 * 24) / averageTurnover : 0;

    const lastFiveCycles = [...events]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, 5)
      .map(event => ({
        ...getTurnoverInfo(event),
        date: new Date(event.timestamp).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      }));

    return {
      averageTurnover,
      avgClassification,
      avgColorClass,
      capitalEfficiencyMultiplier,
      cyclesPerYear,
      lastFiveCycles,
    };
  }, [events]);

  return (
    <div className="card-terminal animate-slide-up">
      <div className="p-4 border-b border-border">
        <h3 className="text-sm font-semibold text-foreground">Cycle Velocity</h3>
        <p className="text-[10px] font-mono text-muted-foreground mt-0.5">Turnover time & capital efficiency</p>
      </div>
      <div className="p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <ArrowRightLeft className="w-4 h-4 text-muted-foreground" />
            <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">Avg Turnover</span>
          </div>
          <span className={`text-sm font-mono font-bold ${turnoverData.avgColorClass}`}>
            {turnoverData.averageTurnover.toFixed(1)}h ( {turnoverData.avgClassification} )
          </span>
        </div>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-muted-foreground" />
            <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">Capital Efficiency</span>
          </div>
          <span className="text-sm font-mono font-bold text-primary">
            {turnoverData.capitalEfficiencyMultiplier.toFixed(1)}x ({turnoverData.cyclesPerYear.toFixed(0)} cycles/year)
          </span>
        </div>

        <div className="space-y-2 pt-2 border-t border-border">
          <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">Last 5 cycles</p>
          {turnoverData.lastFiveCycles.map((cycle, index) => (
            <div key={index} className="flex items-center justify-between">
              <span className="text-xs font-mono text-foreground">{cycle.date}:</span>
              <span className={`text-xs font-mono font-bold ${cycle.colorClass}`}>
                {cycle.hours !== null ? `${cycle.hours.toFixed(0)}h` : "—"} {cycle.classification}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
