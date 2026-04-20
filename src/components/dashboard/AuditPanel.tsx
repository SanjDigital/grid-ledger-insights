import { type ForensicData } from "@/lib/mock-data";
import { type EventForensics, type EnforcementVerdict } from "@/lib/forensic-engine";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrustGauge } from "./TrustGauge";
import { EnforcementPanel } from "./EnforcementPanel";
import { Lock, FileCheck, Cpu, TrendingDown, Shield, Landmark, Clock, Gauge, BarChart3, AlertTriangle } from "lucide-react";

interface AuditPanelProps {
  data: ForensicData;
  isRedAlert: boolean;
  perEventForensics?: EventForensics[];
  enforcement?: EnforcementVerdict;
}

export function AuditPanel({ data, isRedAlert, perEventForensics = [], enforcement }: AuditPanelProps) {
  const varianceColor = data.physicsVariance > 2.0
    ? "text-destructive"
    : data.physicsVariance > 1.5
    ? "text-[hsl(var(--under-review))]"
    : "text-primary";

  const secInRange = data.currentSEC >= data.secRange[0] && data.currentSEC <= data.secRange[1];
  const earHealthy = data.ear <= 100;
  const ntpHealthy = data.ntpOffset <= 300;
  const secBreaches = perEventForensics.filter(e => e.secBreach !== null);

  return (
    <div className="card-terminal animate-slide-up">
      <Tabs defaultValue="forensic" className="w-full">
        <div className="border-b border-border px-4 pt-3">
          <TabsList className="bg-transparent gap-0 h-auto p-0">
            {[
              { value: "forensic", label: "Forensic L0-4", icon: Cpu },
              { value: "trust", label: "Trust L5", icon: Shield },
              { value: "capital", label: "Capital L6", icon: Landmark },
            ].map(t => (
              <TabsTrigger
                key={t.value}
                value={t.value}
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-transparent data-[state=active]:text-primary text-muted-foreground text-xs font-mono px-4 pb-2.5 pt-1"
              >
                <t.icon className="w-3.5 h-3.5 mr-1.5" />
                {t.label}
              </TabsTrigger>
            ))}
          </TabsList>
        </div>

        <TabsContent value="forensic" className="p-4 mt-0 space-y-3">
          {/* L0 — Temporal Integrity */}
          <div className="p-3 rounded bg-secondary/50 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">L0 · Temporal Integrity (NTP ±5 min)</span>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-sm font-mono font-semibold ${ntpHealthy ? "text-primary" : "text-destructive"}`}>
                {ntpHealthy ? "✓" : "✗"} Δ {data.ntpOffset.toFixed(1)}s
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">
                {ntpHealthy ? "Within tolerance" : "TEMPORAL BREACH"}
              </span>
            </div>
          </div>

          {/* L1 — Root Hash */}
          <div className="p-3 rounded bg-secondary/50 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Lock className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">L1 · Root Hash (SHA-256)</span>
            </div>
            <p className="font-mono text-sm text-foreground break-all">{data.rootHash}</p>
          </div>

          {/* L1 — Signature */}
          <div className="p-3 rounded bg-secondary/50 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <FileCheck className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">L1 · Signature Verification ({data.signatureAlgo})</span>
            </div>
            <span className={`text-sm font-mono font-semibold ${data.signatureStatus === "Valid" ? "text-primary" : "text-destructive"}`}>
              {data.signatureStatus === "Valid" ? "✓" : "✗"} {data.signatureStatus}
            </span>
          </div>

          {/* L2 — SEC (Physics) */}
          <div className="p-3 rounded bg-secondary/50 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Gauge className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">L2 · Specific Energy Consumption (SEC)</span>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-2xl font-mono font-bold tabular ${secInRange ? "text-primary" : "text-destructive"}`}>
                {data.currentSEC.toFixed(4)}
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">kWh/kg</span>
            </div>
            <div className="flex items-center gap-2 mt-1.5">
              <span className="text-[10px] font-mono text-muted-foreground">
                Calibration: {data.secRange[0]} – {data.secRange[1]} kWh/kg (±5%)
              </span>
              <span className={`text-[10px] font-mono font-semibold ${secInRange ? "text-primary" : "text-destructive"}`}>
                {secInRange ? "✓ IN RANGE" : "✗ PHYSICS BREACH"}
              </span>
            </div>
            {secBreaches.length > 0 && (
              <div className="mt-2 space-y-1">
                <div className="flex items-center gap-1.5">
                  <AlertTriangle className="w-3 h-3 text-destructive" />
                  <span className="text-[10px] font-mono text-destructive font-semibold">
                    {secBreaches.length} EVENT{secBreaches.length > 1 ? "S" : ""} WITH SEC BREACH
                  </span>
                </div>
                {secBreaches.map(b => (
                  <div key={b.eventId} className="flex items-center gap-2 pl-4">
                    <span className="text-[9px] font-mono text-muted-foreground">{b.eventId}</span>
                    <span className={`text-[9px] font-mono font-semibold ${b.secBreach === "high" ? "text-[hsl(var(--under-review))]" : "text-destructive"}`}>
                      {b.sec?.toFixed(4)} kWh/kg — {b.secBreach === "high" ? "Ghost Idling" : "Data Manipulation"}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* L3-4 — Physics Variance */}
          <div className="p-3 rounded bg-secondary/50 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <TrendingDown className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">L3-4 · Physics Variance</span>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-2xl font-mono font-bold tabular ${varianceColor}`}>
                {data.physicsVariance.toFixed(1)}%
              </span>
              <span className="text-xs text-muted-foreground font-mono">Threshold: 2.0%</span>
            </div>
            {data.physicsVariance > 2.0 && (
              <p className="text-xs text-destructive mt-2 font-mono">⚠ VARIANCE EXCEEDS THRESHOLD — INTEGRITY COMPROMISED</p>
            )}
          </div>

          {/* L4 — EAR */}
          <div className={`p-3 rounded border ${data.earGap > 5 ? "border-[hsl(var(--under-review))/0.4] bg-[hsl(var(--under-review))/0.05]" : "border-border bg-secondary/50"}`}>
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">L4 · Energy Accountability Ratio (EAR)</span>
            </div>
            <div className="flex items-center gap-3">
              <span className={`text-2xl font-mono font-bold tabular ${earHealthy ? (data.earGap > 5 ? "text-[hsl(var(--under-review))]" : "text-primary") : "text-destructive"}`}>
                {data.ear.toFixed(1)}%
              </span>
              <span className="text-[10px] text-muted-foreground font-mono">Reported / Metered</span>
            </div>
            <div className="flex items-center gap-2 mt-1.5">
              <span className={`text-[10px] font-mono font-semibold ${data.earGap > 5 ? "text-[hsl(var(--under-review))]" : "text-primary"}`}>
                {data.earGap.toFixed(1)}% GAP
              </span>
              {data.earGap > 5 && (
                <span className="text-[9px] font-mono text-[hsl(var(--under-review))]">
                  [UNDER ACTIVE REVIEW] — Invisibility Layer audit in progress
                </span>
              )}
            </div>
          </div>
        </TabsContent>

        <TabsContent value="trust" className="p-4 mt-0">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 items-center">
            <TrustGauge score={data.trustScore} isRedAlert={isRedAlert} />
            {enforcement && <EnforcementPanel verdict={enforcement} isOwner />}
          </div>
        </TabsContent>

        <TabsContent value="capital" className="p-4 mt-0 space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="p-4 rounded bg-secondary/50 border border-border text-center">
              <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-2">BPS Adjustment</p>
              <p className="text-xl font-mono font-bold text-primary tabular">{data.bpsAdjustment}</p>
              <p className="text-[10px] text-muted-foreground mt-1">basis points</p>
            </div>
            <div className="p-4 rounded bg-secondary/50 border border-border text-center">
              <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-2">Leverage Cap</p>
              <p className="text-xl font-mono font-bold text-foreground tabular">{data.leverageCap}x</p>
              <p className="text-[10px] text-muted-foreground mt-1">maximum</p>
            </div>
            <div className="p-4 rounded bg-secondary/50 border border-border text-center">
              <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-2">Grade</p>
              <p className="text-xl font-mono font-bold text-[hsl(var(--under-review))]">{data.institutionalGrade}</p>
              <p className="text-[10px] text-muted-foreground mt-1">{data.trustTier.toLowerCase()}</p>
            </div>
          </div>

          <div className={`p-4 rounded border ${isRedAlert ? "border-destructive/50 bg-destructive/5" : "border-[hsl(var(--under-review))/0.3] bg-[hsl(var(--under-review))/0.05]"}`}>
            <p className="text-[10px] font-mono tracking-widest uppercase mb-1 text-muted-foreground">Investor Verdict</p>
            <p className={`text-lg font-semibold ${isRedAlert ? "text-destructive" : "text-[hsl(var(--under-review))]"}`}>
              {isRedAlert ? "DECLINE / HIGH RISK" : data.trustTier === "INSTITUTIONAL" ? "APPROVE / INVESTMENT GRADE" : "CONDITIONAL / UNDER REVIEW"}
            </p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
