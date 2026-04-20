import { useState } from "react";
import { type VerifiedEvent, type AnomalyType } from "@/lib/mock-data";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import { AlertTriangle, Calendar, Clock, TrendingDown } from "lucide-react";

interface LiveDataFeedProps {
  events: VerifiedEvent[];
  onSelectEvent?: (event: VerifiedEvent) => void;
}

const ANOMALY_CONFIG: Record<AnomalyType, { icon: typeof AlertTriangle; colorClass: string; bgClass: string; borderClass: string }> = {
  "holiday-heist": {
    icon: Calendar,
    colorClass: "text-destructive",
    bgClass: "bg-destructive/10",
    borderClass: "border-destructive/30",
  },
  "leading-day": {
    icon: Clock,
    colorClass: "text-[hsl(var(--under-review))]",
    bgClass: "bg-[hsl(var(--under-review)/0.10)]",
    borderClass: "border-[hsl(var(--under-review)/0.30)]",
  },
  "m1-corridor": {
    icon: TrendingDown,
    colorClass: "text-[hsl(var(--gap-detected))]",
    bgClass: "bg-[hsl(var(--gap-detected)/0.10)]",
    borderClass: "border-[hsl(var(--gap-detected)/0.30)]",
  },
};

type FilterKey = AnomalyType | "all";

export function LiveDataFeed({ events, onSelectEvent }: LiveDataFeedProps) {
  const [activeFilter, setActiveFilter] = useState<FilterKey>("all");

  const anomalyCounts = events.reduce<Record<AnomalyType, number>>(
    (acc, evt) => {
      evt.anomalies?.forEach((a) => { acc[a.type] = (acc[a.type] || 0) + 1; });
      return acc;
    },
    { "holiday-heist": 0, "leading-day": 0, "m1-corridor": 0 },
  );

  const totalAnomalies = Object.values(anomalyCounts).reduce((s, n) => s + n, 0);

  const filteredEvents = activeFilter === "all"
    ? events
    : events.filter((e) => e.anomalies?.some((a) => a.type === activeFilter));

  const filters: { key: FilterKey; label: string; count: number }[] = [
    { key: "all", label: "ALL", count: events.length },
    { key: "holiday-heist", label: "HOLIDAY HEIST", count: anomalyCounts["holiday-heist"] },
    { key: "leading-day", label: "LEADING DAY", count: anomalyCounts["leading-day"] },
    { key: "m1-corridor", label: "M1 CORRIDOR", count: anomalyCounts["m1-corridor"] },
  ];

  return (
    <div className="card-terminal animate-slide-up">
      {/* Header */}
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Verified Events</h3>
          <p className="text-[10px] font-mono text-muted-foreground mt-0.5">
            Live transaction feed
            {totalAnomalies > 0 && (
              <span className="ml-2 text-destructive">
                — {totalAnomalies} anomal{totalAnomalies === 1 ? "y" : "ies"} detected
              </span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse-glow" />
          <span className="text-[10px] font-mono text-muted-foreground">LIVE</span>
        </div>
      </div>

      {/* Anomaly Filter Bar */}
      <div className="px-4 py-2.5 border-b border-border flex items-center gap-2 overflow-x-auto scrollbar-terminal">
        <AlertTriangle className="w-3 h-3 text-muted-foreground shrink-0" />
        {filters.map((f) => (
          <button
            key={f.key}
            onClick={() => setActiveFilter(f.key)}
            className={`px-2.5 py-1 rounded text-[10px] font-mono font-semibold transition-all duration-150 border whitespace-nowrap ${
              activeFilter === f.key
                ? f.key === "all"
                  ? "bg-secondary text-foreground border-border"
                  : f.key === "holiday-heist"
                    ? "bg-destructive/15 text-destructive border-destructive/30"
                    : f.key === "leading-day"
                      ? "bg-[hsl(var(--under-review)/0.15)] text-[hsl(var(--under-review))] border-[hsl(var(--under-review)/0.3)]"
                      : "bg-[hsl(var(--gap-detected)/0.15)] text-[hsl(var(--gap-detected))] border-[hsl(var(--gap-detected)/0.3)]"
                : "bg-transparent text-muted-foreground border-transparent hover:border-border hover:text-foreground"
            }`}
          >
            {f.label}
            {f.count > 0 && (
              <span className="ml-1.5 opacity-70">{f.count}</span>
            )}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="overflow-auto max-h-80 scrollbar-terminal">
        <TooltipProvider delayDuration={200}>
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                {["Timestamp", "Token ID", "kWh", "Reported Cash", "Verification", "Anomalies"].map((h) => (
                  <TableHead key={h} className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase h-8">
                    {h}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredEvents.map((evt) => {
                const hasAnomaly = evt.anomalies && evt.anomalies.length > 0;
                return (
                  <TableRow
                    key={evt.id}
                    onClick={() => onSelectEvent?.(evt)}
                    className={`border-border transition-colors duration-150 cursor-pointer ${
                      hasAnomaly
                        ? "hover:bg-destructive/10 bg-destructive/[0.02]"
                        : "hover:bg-secondary/40"
                    }`}
                  >
                    <TableCell className="font-mono text-xs tabular text-muted-foreground py-2.5">
                      {evt.timestamp}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-foreground py-2.5">
                      {evt.tokenId}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular text-foreground py-2.5">
                      {evt.kwh.toFixed(1)}
                    </TableCell>
                    <TableCell className="font-mono text-xs tabular text-foreground py-2.5">
                      {evt.currency}{evt.reportedCash.toLocaleString()}
                    </TableCell>
                    <TableCell className="py-2.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono font-semibold ${
                        evt.verification === "sovereign" ? "badge-sovereign" :
                        evt.verification === "floor-verified" ? "badge-floor-verified" :
                        evt.verification === "review" ? "badge-review" :
                        "badge-gap"
                      }`}>
                        {evt.verification === "sovereign" ? "SOVEREIGN" :
                         evt.verification === "floor-verified" ? "FLOOR GEN." :
                         evt.verification === "review" ? "REVIEW" : "GAP"}
                      </span>
                    </TableCell>
                    <TableCell className="py-2.5">
                      {hasAnomaly ? (
                        <div className="flex items-center gap-1.5">
                          {evt.anomalies!.map((anomaly) => {
                            const cfg = ANOMALY_CONFIG[anomaly.type];
                            const Icon = cfg.icon;
                            return (
                              <Tooltip key={anomaly.type}>
                                <TooltipTrigger asChild>
                                  <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono font-semibold border cursor-help ${cfg.bgClass} ${cfg.colorClass} ${cfg.borderClass}`}>
                                    <Icon className="w-3 h-3" />
                                    {anomaly.label}
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent side="top" className="max-w-xs font-mono text-[11px]">
                                  <p className="font-semibold mb-1">{anomaly.label}</p>
                                  <p className="text-muted-foreground">{anomaly.detail}</p>
                                </TooltipContent>
                              </Tooltip>
                            );
                          })}
                        </div>
                      ) : (
                        <span className="text-[10px] font-mono text-muted-foreground/50">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
              {filteredEvents.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-xs font-mono text-muted-foreground py-8">
                    No events match the selected filter.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TooltipProvider>
      </div>
    </div>
  );
}
