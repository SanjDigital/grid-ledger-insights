import { type ForensicData } from "@/lib/mock-data";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TrustGauge } from "./TrustGauge";
import { Lock, FileCheck, Cpu, TrendingDown, Shield, Landmark } from "lucide-react";

interface AuditPanelProps {
  data: ForensicData;
  isRedAlert: boolean;
}

export function AuditPanel({ data, isRedAlert }: AuditPanelProps) {
  const varianceColor = data.physicsVariance > 2.0
    ? "text-destructive"
    : data.physicsVariance > 1.5
    ? "text-under-review"
    : "text-primary";

  return (
    <div className="card-terminal animate-slide-up">
      <Tabs defaultValue="forensic" className="w-full">
        <div className="border-b border-border px-4 pt-3">
          <TabsList className="bg-transparent gap-0 h-auto p-0">
            {[
              { value: "forensic", label: "Forensic L1-4", icon: Cpu },
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

        <TabsContent value="forensic" className="p-4 mt-0 space-y-4">
          {/* Root Hash */}
          <div className="p-3 rounded bg-secondary/50 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <Lock className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">L1 · Root Hash (SHA-256)</span>
            </div>
            <p className="font-mono text-sm text-foreground break-all">{data.rootHash}</p>
          </div>

          {/* Signature */}
          <div className="p-3 rounded bg-secondary/50 border border-border">
            <div className="flex items-center gap-2 mb-2">
              <FileCheck className="w-3.5 h-3.5 text-muted-foreground" />
              <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">L2 · Signature Verification ({data.signatureAlgo})</span>
            </div>
            <span className={`text-sm font-mono font-semibold ${data.signatureStatus === "Valid" ? "text-primary" : "text-destructive"}`}>
              {data.signatureStatus === "Valid" ? "✓" : "✗"} {data.signatureStatus}
            </span>
          </div>

          {/* Physics Variance */}
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
        </TabsContent>

        <TabsContent value="trust" className="p-4 mt-0">
          <TrustGauge score={data.trustScore} isRedAlert={isRedAlert} />
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
              <p className="text-xl font-mono font-bold text-primary">{data.institutionalGrade}</p>
              <p className="text-[10px] text-muted-foreground mt-1">institutional</p>
            </div>
          </div>

          <div className={`p-4 rounded border ${isRedAlert ? "border-destructive/50 bg-destructive/5" : "border-primary/30 bg-primary/5"}`}>
            <p className="text-[10px] font-mono tracking-widest uppercase mb-1 text-muted-foreground">Investor Verdict</p>
            <p className={`text-lg font-semibold ${isRedAlert ? "text-destructive" : "text-primary"}`}>
              {isRedAlert ? "DECLINE / HIGH RISK" : "APPROVE / INVESTMENT GRADE"}
            </p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
