import { useState } from "react";
import { mills, type Mill } from "@/lib/mock-data";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Activity, Zap } from "lucide-react";

interface AssetSidebarProps {
  selectedMill: Mill;
  onSelectMill: (mill: Mill) => void;
}

export function AssetSidebar({ selectedMill, onSelectMill }: AssetSidebarProps) {
  return (
    <aside className="w-72 border-r border-border bg-card flex flex-col shrink-0">
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-primary/20 flex items-center justify-center">
            <Zap className="w-4 h-4 text-primary" />
          </div>
          <div>
            <h1 className="text-sm font-semibold tracking-tight text-foreground">GridLedger</h1>
            <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">Audit Console</p>
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
          <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase mb-1">Phone</p>
          <p className="text-sm font-mono text-foreground tabular">{selectedMill.phone}</p>
        </div>

        <div className="mt-6 p-3 rounded bg-secondary/50 border border-border">
          <div className="flex items-center gap-2 mb-2">
            <Activity className="w-3.5 h-3.5 text-primary" />
            <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">Status</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full pip-sovereign" />
            <span className="text-xs font-medium text-primary">Online — Sovereign</span>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border">
        <p className="text-[9px] font-mono text-muted-foreground leading-relaxed">
          Fleet of Five · GridLedger v2.4.1
        </p>
      </div>
    </aside>
  );
}
