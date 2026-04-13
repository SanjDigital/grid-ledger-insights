import { useState, useMemo } from "react";
import { mills, generateStreakDays, forensicData, verifiedEvents } from "@/lib/mock-data";
import { computeForensics } from "@/lib/forensic-engine";
import { AssetSidebar } from "@/components/dashboard/AssetSidebar";
import { StreakHeader } from "@/components/dashboard/StreakHeader";
import { AuditPanel } from "@/components/dashboard/AuditPanel";
import { LiveDataFeed } from "@/components/dashboard/LiveDataFeed";
import { EnergyChart } from "@/components/dashboard/EnergyChart";
import { YieldEfficiencyChart } from "@/components/dashboard/YieldEfficiencyChart";
import type { Mill } from "@/lib/mock-data";

const Index = () => {
  const [selectedMill, setSelectedMill] = useState<Mill>(mills[0]);
  const [varianceOverride, setVarianceOverride] = useState<number | null>(null);
  const streakDays = useMemo(() => generateStreakDays(), []);

  const baseForensic = useMemo(() => ({
    ...forensicData,
    physicsVariance: varianceOverride ?? forensicData.physicsVariance,
  }), [varianceOverride]);

  const computed = useMemo(() => computeForensics(verifiedEvents, baseForensic), [baseForensic]);

  const currentForensic = useMemo(() => ({
    ...baseForensic,
    currentSEC: computed.currentSEC,
    ear: computed.ear,
    earGap: computed.earGap,
    systemState: computed.systemState,
    trustTier: computed.trustTier,
    trustScore: computed.trustScore,
  }), [baseForensic, computed]);

  const isRedAlert = currentForensic.physicsVariance > 2.0;

  return (
    <div className="flex min-h-screen bg-background">
      <AssetSidebar selectedMill={selectedMill} onSelectMill={setSelectedMill} />

      <div className="flex-1 flex flex-col min-w-0">
        <StreakHeader days={streakDays} isRedAlert={isRedAlert} />

        <div className="flex-1 overflow-auto p-5 space-y-5 scrollbar-terminal">
          {/* Variance Toggle (Demo) */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setVarianceOverride(v => v === null ? 3.7 : null)}
              className={`px-3 py-1.5 rounded text-xs font-mono transition-all duration-200 active:scale-[0.97] ${
                isRedAlert
                  ? "bg-destructive/20 text-destructive border border-destructive/30 hover:bg-destructive/30"
                  : "bg-secondary text-muted-foreground border border-border hover:bg-secondary/80"
              }`}
            >
              {isRedAlert ? "⚠ Clear Alert Demo" : "⚡ Simulate Red Alert"}
            </button>
            <span className="text-[10px] font-mono text-muted-foreground">Toggle variance to test alert state</span>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <AuditPanel data={currentForensic} isRedAlert={isRedAlert} />
            <div className="space-y-5">
              <EnergyChart />
              <YieldEfficiencyChart />
            </div>
          </div>

          <LiveDataFeed events={verifiedEvents} />

          {/* Disclaimer */}
          <footer className="pt-4 pb-2 border-t border-border">
            <p className="text-[9px] font-mono text-muted-foreground leading-relaxed max-w-3xl">
              <span className="text-foreground/60 font-semibold">Model Basis Disclaimer:</span> All risk assessments, financing advantages, and trust integrity scores presented are indicative and derived from algorithmic models. They do not constitute financial advice or guarantees. BPS adjustments and leverage caps are subject to real-time recalibration based on ongoing forensic audits. GridLedger assumes no liability for investment decisions made on the basis of this data.
            </p>
          </footer>
        </div>
      </div>
    </div>
  );
};

export default Index;
