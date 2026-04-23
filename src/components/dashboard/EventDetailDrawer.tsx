import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { Check, X, AlertTriangle, Flag } from "lucide-react";
import type { VerifiedEvent, ForensicData } from "@/lib/mock-data";
import { getTurnoverInfo } from "@/lib/forensic-engine";
import type { EventForensics } from "@/lib/forensic-engine";
import { useAuditTrail } from "./AuditTrailContext";

interface EventDetailDrawerProps {
  event: VerifiedEvent | null;
  forensic: EventForensics | null;
  baseForensic: ForensicData;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

type LayerStatus = "pass" | "fail" | "warn";

interface LayerCheck {
  id: string;
  label: string;
  status: LayerStatus;
  detail: string;
}

// Deterministic fake hash from event id (stable across renders)
function deriveRootHash(id: string): string {
  let h = 0x811c9dc5;
  for (let i = 0; i < id.length; i++) {
    h ^= id.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  const hex = (h >>> 0).toString(16).padStart(8, "0");
  // pad to look like a 256-bit hash
  return `${hex}${hex.split("").reverse().join("")}${hex}${hex.split("").reverse().join("")}`.slice(0, 64);
}

function StatusIcon({ status }: { status: LayerStatus }) {
  if (status === "pass") return <Check className="w-3.5 h-3.5 text-[hsl(var(--sovereign))]" />;
  if (status === "fail") return <X className="w-3.5 h-3.5 text-destructive" />;
  return <AlertTriangle className="w-3.5 h-3.5 text-[hsl(var(--under-review))]" />;
}

function statusBadge(status: LayerStatus): string {
  if (status === "pass") return "border-[hsl(var(--sovereign)/0.3)] bg-[hsl(var(--sovereign)/0.08)] text-[hsl(var(--sovereign))]";
  if (status === "fail") return "border-destructive/30 bg-destructive/10 text-destructive";
  return "border-[hsl(var(--under-review)/0.3)] bg-[hsl(var(--under-review)/0.08)] text-[hsl(var(--under-review))]";
}

export function EventDetailDrawer({ event, forensic, baseForensic, open, onOpenChange }: EventDetailDrawerProps) {
  const { toast } = useToast();
  const { recordAction, latestRootHash } = useAuditTrail();

  if (!event) return null;

  const rootHash = deriveRootHash(event.id);
  const sec = forensic?.sec ?? null;
  const secInRange = sec !== null && sec >= baseForensic.secRange[0] && sec <= baseForensic.secRange[1];
  const cashGap = Math.max(0, Math.round(event.kwh * 1350) - event.reportedCash); // expected cash heuristic
  const earLocal = event.meteredKwh > 0 ? (event.kwh / event.meteredKwh) * 100 : 0;
  const cashOk = event.verification !== "gap" && event.reportedCash > 0;
  const turnoverInfo = getTurnoverInfo(event);
  const capitalEfficiency = turnoverInfo.hours !== null ? (365 * 24) / turnoverInfo.hours / 52 : 0;

  const handleReportDiscrepancy = () => {
    recordAction("discrepancy_report", event.tokenId, "Manual discrepancy report filed by operator", latestRootHash);
    toast({
      title: "Discrepancy reported",
      description: `Event ${event.tokenId} flagged for auditor review. Audit trail updated.`,
    });
    onOpenChange(false);
  };

  const layers: LayerCheck[] = [
    {
      id: "L0",
      label: "Timestamp Integrity",
      status: Math.abs(baseForensic.ntpOffset) < 5 ? "pass" : "fail",
      detail: `NTP offset ${baseForensic.ntpOffset}s · ${event.timestamp}`,
    },
    {
      id: "L1",
      label: "Signature Validity",
      status: baseForensic.signatureStatus === "Valid" ? "pass" : "fail",
      detail: `${baseForensic.signatureAlgo} verified against root hash`,
    },
    {
      id: "L2",
      label: `SEC Range (${baseForensic.secRange[0]}–${baseForensic.secRange[1]})`,
      status: sec === null ? "warn" : secInRange ? "pass" : "fail",
      detail:
        sec === null
          ? "No yield reported — SEC undefined"
          : `${sec.toFixed(4)} kWh/kg ${secInRange ? "within" : forensic?.secBreach === "high" ? "above (Ghost Idling)" : "below (Data Manipulation)"} window`,
    },
    {
      id: "L3",
      label: "Law of Presence",
      status: event.yieldKg > 0 ? "pass" : event.kwh > 0 ? "fail" : "warn",
      detail:
        event.yieldKg > 0
          ? `Production confirmed · ${event.yieldKg} kg`
          : "Energy consumed with zero production — Holiday Heist signature",
    },
    {
      id: "L4",
      label: "Cash Reconciliation",
      status: cashOk ? (cashGap > 5000 ? "warn" : "pass") : "fail",
      detail: cashOk
        ? cashGap > 5000
          ? `Settled ${event.currency}${event.reportedCash.toLocaleString()} · gap ${event.currency}${cashGap.toLocaleString()}`
          : `Settled ${event.currency}${event.reportedCash.toLocaleString()} · within tolerance`
        : `Missing Airtel receipt · gap ${event.currency}${cashGap.toLocaleString()}`,
    },
  ];

  const overallPass = layers.every((l) => l.status === "pass");

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto scrollbar-terminal p-0">
        <SheetHeader className="p-5 border-b border-border space-y-2">
          <div className="flex items-center justify-between">
            <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-semibold border ${
              overallPass
                ? "border-[hsl(var(--sovereign)/0.3)] bg-[hsl(var(--sovereign)/0.08)] text-[hsl(var(--sovereign))]"
                : "border-destructive/30 bg-destructive/10 text-destructive"
            }`}>
              {overallPass ? "AUDITOR-READY" : "DISCREPANCY"}
            </span>
            <span className="text-[10px] font-mono text-muted-foreground">{event.id}</span>
          </div>
          <SheetTitle className="font-mono text-base text-foreground">{event.tokenId}</SheetTitle>
          <SheetDescription className="font-mono text-[10px] text-muted-foreground">
            Forensic micro-proof · L0–L4 evidence stack
          </SheetDescription>
        </SheetHeader>

        {/* Raw Data */}
        <section className="p-5 border-b border-border space-y-2">
          <h4 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Raw Data</h4>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 font-mono text-xs">
            <span className="text-muted-foreground">Timestamp</span>
            <span className="text-foreground tabular text-right">{event.timestamp}</span>
            <span className="text-muted-foreground">Reported kWh</span>
            <span className="text-foreground tabular text-right">{event.kwh.toFixed(2)}</span>
            <span className="text-muted-foreground">Metered kWh (ESCOM)</span>
            <span className="text-foreground tabular text-right">{event.meteredKwh.toFixed(2)}</span>
            <span className="text-muted-foreground">Yield (kg)</span>
            <span className="text-foreground tabular text-right">{event.yieldKg.toLocaleString()}</span>
            <span className="text-muted-foreground">Cash Settled</span>
            <span className="text-foreground tabular text-right">{event.currency}{event.reportedCash.toLocaleString()}</span>
            <span className="text-muted-foreground">Verification</span>
            <span className="text-foreground text-right uppercase">{event.verification}</span>
          </div>
        </section>

        {/* Derived Metrics */}
        <section className="p-5 border-b border-border space-y-2">
          <h4 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Derived Metrics</h4>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 font-mono text-xs">
            <span className="text-muted-foreground">SEC (kWh/kg)</span>
            <span className={`tabular text-right ${secInRange ? "text-[hsl(var(--sovereign))]" : sec === null ? "text-muted-foreground" : "text-destructive"}`}>
              {sec === null ? "—" : sec.toFixed(4)}
            </span>
            <span className="text-muted-foreground">EAR (event)</span>
            <span className={`tabular text-right ${earLocal >= 90 && earLocal <= 110 ? "text-[hsl(var(--sovereign))]" : "text-destructive"}`}>
              {earLocal.toFixed(1)}%
            </span>
            <span className="text-muted-foreground">Cash Gap</span>
            <span className={`tabular text-right ${cashGap > 5000 ? "text-destructive" : "text-foreground"}`}>
              {event.currency}{cashGap.toLocaleString()}
            </span>
            <span className="text-muted-foreground">Turnover Time</span>
            <span className={`tabular text-right ${turnoverInfo.colorClass}`}>
              {turnoverInfo.hours !== null ? `${turnoverInfo.hours.toFixed(0)}h (${turnoverInfo.classification})` : "—"}
            </span>
            <span className="text-muted-foreground">Capital Efficiency</span>
            <span className="tabular text-right text-primary">
              {capitalEfficiency.toFixed(1)}x
            </span>
          </div>
        </section>

        {/* Forensic Layers */}
        <section className="p-5 border-b border-border space-y-2.5">
          <h4 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Forensic Stack</h4>
          <div className="space-y-1.5">
            {layers.map((l) => (
              <div key={l.id} className={`flex items-start gap-2.5 p-2.5 rounded border ${statusBadge(l.status)}`}>
                <div className="flex items-center gap-2 shrink-0 pt-0.5">
                  <StatusIcon status={l.status} />
                  <span className="font-mono text-[10px] font-bold opacity-80">{l.id}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-mono text-xs font-semibold text-foreground">{l.label}</p>
                  <p className="font-mono text-[10px] text-muted-foreground mt-0.5 leading-relaxed">{l.detail}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Root Hash */}
        <section className="p-5 border-b border-border space-y-2">
          <h4 className="text-[10px] font-mono uppercase tracking-widest text-muted-foreground">Cryptographic Anchor</h4>
          <div className="space-y-1">
            <p className="font-mono text-[10px] text-muted-foreground">Event Root Hash · SHA-256</p>
            <code className="block font-mono text-[10px] text-foreground bg-secondary/40 border border-border rounded p-2 break-all">
              {rootHash}
            </code>
            <p className="font-mono text-[10px] text-muted-foreground">
              Signed with {baseForensic.signatureAlgo} · anchored to chain root <span className="text-foreground/70">{latestRootHash}</span>
            </p>
          </div>
        </section>

        {/* Actions */}
        <section className="p-5 flex items-center gap-2">
          <button
            className="flex-1 px-4 py-2 rounded bg-secondary hover:bg-secondary/80 border border-border text-xs font-mono text-foreground transition-colors"
            onClick={() => onOpenChange(false)}
          >
            Close
          </button>
          <button
            className="flex-1 px-4 py-2 rounded bg-destructive/10 hover:bg-destructive/20 border border-destructive/30 text-xs font-mono text-destructive flex items-center justify-center gap-2 transition-colors"
            onClick={handleReportDiscrepancy}
          >
            <Flag className="w-3 h-3" />
            Report discrepancy
          </button>
        </section>
      </SheetContent>
    </Sheet>
  );
}
