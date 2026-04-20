import { useState } from "react";
import { ChevronDown, CheckCircle2, XCircle, MinusCircle, Lock } from "lucide-react";
import type { AuthorityAlignment, AuthorityLayer, LayerStatus } from "@/lib/forensic-engine";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";

interface AuthorityStackPanelProps {
  alignment: AuthorityAlignment;
}

const STATUS_CFG: Record<LayerStatus, {
  icon: typeof CheckCircle2;
  textClass: string;
  borderClass: string;
  bgClass: string;
  glyph: string;
  label: string;
}> = {
  aligned: {
    icon: CheckCircle2,
    textClass: "text-[hsl(var(--sovereign))]",
    borderClass: "border-[hsl(var(--sovereign)/0.4)]",
    bgClass: "bg-[hsl(var(--sovereign)/0.06)]",
    glyph: "✓",
    label: "ALIGNED",
  },
  conflict: {
    icon: XCircle,
    textClass: "text-destructive",
    borderClass: "border-destructive/40",
    bgClass: "bg-destructive/8",
    glyph: "✗",
    label: "CONFLICT",
  },
  missing: {
    icon: MinusCircle,
    textClass: "text-muted-foreground",
    borderClass: "border-border",
    bgClass: "bg-secondary/40",
    glyph: "—",
    label: "MISSING",
  },
};

export function AuthorityStackPanel({ alignment }: AuthorityStackPanelProps) {
  const [open, setOpen] = useState(true);
  const overallOk = alignment.overall === "aligned";

  return (
    <div className="card-terminal animate-slide-up">
      <Collapsible open={open} onOpenChange={setOpen}>
        <CollapsibleTrigger className="w-full flex items-center justify-between px-4 py-3 border-b border-border hover:bg-secondary/30 transition-colors">
          <div className="flex items-center gap-2">
            <Lock className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">
              Authority Stack · Source of Truth
            </span>
            <span
              className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                overallOk
                  ? "text-[hsl(var(--sovereign))] bg-[hsl(var(--sovereign)/0.1)]"
                  : "text-destructive bg-destructive/10"
              }`}
            >
              {overallOk ? "✓ HIERARCHY INTACT" : "✗ HIERARCHY CONFLICT"}
            </span>
          </div>
          <ChevronDown
            className={`w-4 h-4 text-muted-foreground transition-transform duration-200 ${open ? "rotate-180" : ""}`}
          />
        </CollapsibleTrigger>

        <CollapsibleContent className="overflow-hidden data-[state=closed]:animate-accordion-up data-[state=open]:animate-accordion-down">
          <div className="p-4 space-y-2">
            {alignment.layers.map((layer, idx) => (
              <LayerRow key={layer.id} layer={layer} index={idx} total={alignment.layers.length} />
            ))}

            <div className="pt-3 mt-2 border-t border-border">
              <p className="text-[10px] font-mono text-muted-foreground leading-relaxed">
                <span className="text-foreground/80 font-semibold">⚖ Hierarchy Rule:</span>{" "}
                Lower layers cannot override higher layers. ESCOM meter readings are
                cryptographically anchored and supersede operator-reported values when in conflict.
              </p>
              {alignment.lastEventId && (
                <p className="text-[9px] font-mono text-muted-foreground mt-1.5">
                  Evaluated against last cycle: <span className="text-foreground/70">{alignment.lastEventId}</span>
                </p>
              )}
            </div>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </div>
  );
}

function LayerRow({ layer, index, total }: { layer: AuthorityLayer; index: number; total: number }) {
  const cfg = STATUS_CFG[layer.status];
  const Icon = cfg.icon;
  const isLast = index === total - 1;

  return (
    <div className="relative">
      <div
        className={`flex items-start gap-3 p-3 rounded border ${cfg.borderClass} ${cfg.bgClass} transition-all`}
      >
        <Icon className={`w-5 h-5 shrink-0 mt-0.5 ${cfg.textClass}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-2 flex-wrap">
            <span className="text-sm font-mono font-bold text-foreground">{layer.name}</span>
            <span className={`text-[10px] font-mono font-semibold ${cfg.textClass}`}>
              {cfg.glyph} {cfg.label}
            </span>
          </div>
          <p className="text-[10px] font-mono text-muted-foreground mt-0.5">{layer.role}</p>
          <p className={`text-[10px] font-mono mt-1.5 leading-snug ${cfg.textClass} opacity-90`}>
            {layer.detail}
          </p>
        </div>
      </div>
      {!isLast && (
        <div className="flex justify-center py-0.5">
          <div className="w-px h-3 bg-border" />
        </div>
      )}
    </div>
  );
}
