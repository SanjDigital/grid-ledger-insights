import { VerifiedEvent } from "@/lib/mock-data";
import { getTurnoverInfo } from "@/lib/forensic-engine";
import { useToast } from "@/hooks/use-toast";
import { CheckCircle2, AlertCircle, Clock, RotateCcw } from "lucide-react";

interface ReconciliationTimelineProps {
  events: VerifiedEvent[];
}

export function ReconciliationTimeline({ events }: ReconciliationTimelineProps) {
  const { toast } = useToast();

  const handleReconcile = (tokenId: string) => {
    toast({
      title: "Reconciliation Initiated",
      description: `Triggering manual audit for cycle ${tokenId}. Data integrity re-verification in progress.`,
    });
  };

  const getStatusBadge = (verification: VerifiedEvent["verification"]) => {
    switch (verification) {
      case "sovereign":
        return (
          <span className="badge-sovereign px-1.5 py-0.5 rounded text-[9px] font-mono flex items-center gap-1">
            <CheckCircle2 className="w-2.5 h-2.5" /> SOVEREIGN
          </span>
        );
      case "floor-verified":
        return (
          <span className="badge-floor-verified px-1.5 py-0.5 rounded text-[9px] font-mono flex items-center gap-1">
            <CheckCircle2 className="w-2.5 h-2.5" /> VERIFIED
          </span>
        );
      case "review":
        return (
          <span className="badge-review px-1.5 py-0.5 rounded text-[9px] font-mono flex items-center gap-1">
            <AlertCircle className="w-2.5 h-2.5" /> REVIEW
          </span>
        );
      case "gap":
        return (
          <span className="badge-gap px-1.5 py-0.5 rounded text-[9px] font-mono flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" /> GAP
          </span>
        );
      default:
        return null;
    }
  };

  const recentEvents = [...events].sort((a, b) => b.timestamp.localeCompare(a.timestamp)).slice(0, 5);

  return (
    <div className="card-terminal animate-slide-up">
      <div className="p-4 border-b border-border flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-foreground">Reconciliation Timeline</h3>
          <p className="text-[10px] font-mono text-muted-foreground mt-0.5">Recent production cycles & reconciliation status</p>
        </div>
      </div>
      <div className="p-4 space-y-4">
        {recentEvents.map((event) => (
          <div key={event.id} className="flex items-center justify-between gap-4 group">
            <div className="flex items-center gap-3">
              <div className="w-2 h-2 rounded-full bg-border group-hover:bg-primary transition-colors" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-bold text-foreground">{event.tokenId}</span>
                  {getStatusBadge(event.verification)}
                </div>
                <p className="text-[10px] font-mono text-muted-foreground">{event.timestamp}</p>
                {(() => {
                  const turnover = getTurnoverInfo(event);
                  return turnover.hours !== null ? (
                    <span className={`text-[10px] font-mono font-bold ${turnover.colorClass}`}>
                      {turnover.hours.toFixed(0)}h ({turnover.classification})
                    </span>
                  ) : (
                    <span className="text-[10px] font-mono text-muted-foreground">
                      — STALLED
                    </span>
                  );
                })()}
              </div>
            </div>
            
            <button
              onClick={() => handleReconcile(event.tokenId)}
              className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1.5 px-2 py-1 rounded bg-secondary hover:bg-secondary/80 border border-border text-[10px] font-mono text-foreground"
            >
              <RotateCcw className="w-3 h-3" />
              Reconcile
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
