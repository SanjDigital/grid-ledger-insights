import { useState, useMemo } from "react";
import { mills, generateStreakDays, forensicData, verifiedEvents } from "@/lib/mock-data";
import { computeForensics } from "@/lib/forensic-engine";
import { AssetSidebar } from "@/components/dashboard/AssetSidebar";
import { StreakHeader } from "@/components/dashboard/StreakHeader";
import { AuditPanel } from "@/components/dashboard/AuditPanel";
import { LiveDataFeed } from "@/components/dashboard/LiveDataFeed";
import { EnergyChart } from "@/components/dashboard/EnergyChart";
import { YieldEfficiencyChart } from "@/components/dashboard/YieldEfficiencyChart";
import { ReconciliationTimeline } from "@/components/dashboard/ReconciliationTimeline";
import { AuthorityStackPanel } from "@/components/dashboard/AuthorityStackPanel";
import { EventDetailDrawer } from "@/components/dashboard/EventDetailDrawer";
import { AuditTrailProvider } from "@/components/dashboard/AuditTrailContext";
import { CycleVelocityPanel } from "@/components/dashboard/CycleVelocityPanel";
import type { Mill, VerifiedEvent } from "@/lib/mock-data";

const IndexContent = () => {
  const [selectedMill, setSelectedMill] = useState<Mill>(mills[0]);
  const [varianceOverride, setVarianceOverride] = useState<number | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<VerifiedEvent | null>(null);
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
          {/* Variance Toggle (Demo) — gated behind VITE_SHOW_DEMO */}
          {import.meta.env.VITE_SHOW_DEMO !== "false" && (
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
          )}

          <div className="grid grid-cols-1 xl:grid-cols-2 gap-5">
            <AuditPanel data={currentForensic} isRedAlert={isRedAlert} perEventForensics={computed.perEvent} enforcement={computed.enforcement} />
            <CycleVelocityPanel events={verifiedEvents} />
            <div className="space-y-5">
              <AuthorityStackPanel alignment={computed.authority} />
              <ReconciliationTimeline events={verifiedEvents} />
              <EnergyChart events={verifiedEvents} />
              <YieldEfficiencyChart events={verifiedEvents} currentSEC={computed.currentSEC} />
            </div>
          </div>

          <LiveDataFeed events={verifiedEvents} onSelectEvent={setSelectedEvent} />

          <EventDetailDrawer
            event={selectedEvent}
            forensic={selectedEvent ? computed.perEvent.find(p => p.eventId === selectedEvent.id) ?? null : null}
            baseForensic={currentForensic}
            open={!!selectedEvent}
            onOpenChange={(o) => { if (!o) setSelectedEvent(null); }}
          />

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

const Index = () => {
  return (
    <AuditTrailProvider initialRootHash={forensicData.rootHash}>
      <IndexContent />
    </AuditTrailProvider>
  );
};

export default Index;
