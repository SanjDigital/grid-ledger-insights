import { mills, type Mill, forensicData, getSystemStateColor, getTrustTierColor } from "@/lib/mock-data";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Activity } from "lucide-react";
import gridledgerIcon from "@/assets/GridLedger_icon_512px.png";

interface AssetSidebarProps {
  selectedMill: Mill;
  onSelectMill: (mill: Mill) => void;
}

export function AssetSidebar({ selectedMill, onSelectMill }: AssetSidebarProps) {
  const stateColor = getSystemStateColor(forensicData.systemState);
  const tierColor = getTrustTierColor(forensicData.trustTier);

  return (
    <aside className="w-72 border-r border-border bg-card flex flex-col shrink-0">
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <img src={gridledgerIcon} alt="GridLedger" className="w-8 h-8 rounded" />
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-foreground">GridLedger</h1>
            <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">Verification Protocol</p>
          </div>
        </div>
      </div>

      {/* Asset Selector */}
      <div className="p-4 border-b border-border">
        <label className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-2 block">
          Fleet Asset
        </label>
        <Select value={selectedMill.id} onValueChange={(v) => {
          const mill = mills.find(m => m.id === v);
          if (mill) onSelectMill(mill);
        }}>
          <SelectTrigger className="bg-secondary border-border text-foreground text-sm">
            <SelectValue />
          </SelectTrigger>
          <SelectContent className="bg-card border-border">
            {mills.map(m => (
              <SelectItem key={m.id} value={m.id} className="text-sm text-foreground">
                {m.name} ({m.operator})
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Asset Details */}
      <div className="p-4 space-y-4 flex-1">
        <div>
          <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-1">Operator</p>
          <p className="text-sm font-medium text-foreground">{selectedMill.operator}</p>
        </div>
        <div>
          <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-1">Meter ID</p>
          <p className="text-sm font-mono text-primary tabular">{selectedMill.meterId}</p>
        </div>
        <div>
          <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-1">Asset Class</p>
          <p className="text-xs font-mono text-foreground">{selectedMill.assetClass}</p>
        </div>
        <div>
          <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-1">Phone</p>
          <p className="text-sm font-mono text-foreground tabular">{selectedMill.phone}</p>
        </div>

        {/* System State */}
        <div className="p-3 rounded bg-secondary/50 border border-border">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">System State</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2 h-2 rounded-full ${forensicData.systemState === "VERIFIED" ? "pip-sovereign" : forensicData.systemState === "UNDER REVIEW" ? "pip-review" : "pip-gap"}`} />
            <span className={`text-xs font-mono font-semibold ${stateColor}`}>{forensicData.systemState}</span>
          </div>
          {forensicData.systemState === "UNDER REVIEW" && (
            <p className="text-[9px] font-mono text-muted-foreground mt-1.5">
              {forensicData.earGap}% EAR gap under active investigation
            </p>
          )}
        </div>

        {/* Trust Tier */}
        <div className="p-3 rounded bg-secondary/50 border border-border">
          <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-1.5">Trust Tier</p>
          <div className="flex items-baseline gap-2">
            <span className={`text-lg font-mono font-bold tabular ${tierColor}`}>{forensicData.trustScore}</span>
            <span className="text-[10px] text-muted-foreground font-mono">/100</span>
            <span className={`text-[10px] font-mono font-semibold ${tierColor}`}>{forensicData.trustTier}</span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <p className="text-[9px] font-mono text-muted-foreground leading-relaxed">
          Fleet of Five · GridLedger v2.4.1
        </p>
        <p className="text-[9px] font-mono text-muted-foreground">
          Last Calibration: {forensicData.lastCalibration}
        </p>
      </div>
    </aside>
  );
}
