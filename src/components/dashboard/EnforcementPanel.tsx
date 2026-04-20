import { useState } from "react";
import { CheckCircle2, AlertCircle, ShieldOff, ShieldCheck, FileSearch } from "lucide-react";
import type { EnforcementVerdict, NextTokenState } from "@/lib/forensic-engine";
import { useToast } from "@/hooks/use-toast";

interface EnforcementPanelProps {
  verdict: EnforcementVerdict;
  /** Owner role unlocks override action on BLOCKED state */
  isOwner?: boolean;
}

const STATE_CONFIG: Record<NextTokenState, {
  label: string;
  glyph: string;
  icon: typeof CheckCircle2;
  textClass: string;
  bgClass: string;
  borderClass: string;
  glowClass: string;
}> = {
  CLEARED: {
    label: "CLEARED",
    glyph: "🟢",
    icon: CheckCircle2,
    textClass: "text-[hsl(var(--sovereign))]",
    bgClass: "bg-[hsl(var(--sovereign)/0.08)]",
    borderClass: "border-[hsl(var(--sovereign)/0.35)]",
    glowClass: "shadow-[0_0_20px_-6px_hsl(var(--sovereign)/0.5)]",
  },
  CONDITIONAL: {
    label: "CONDITIONAL",
    glyph: "🟡",
    icon: AlertCircle,
    textClass: "text-[hsl(var(--under-review))]",
    bgClass: "bg-[hsl(var(--under-review)/0.08)]",
    borderClass: "border-[hsl(var(--under-review)/0.35)]",
    glowClass: "shadow-[0_0_20px_-6px_hsl(var(--under-review)/0.5)]",
  },
  BLOCKED: {
    label: "BLOCKED",
    glyph: "🔴",
    icon: ShieldOff,
    textClass: "text-destructive",
    bgClass: "bg-destructive/10",
    borderClass: "border-destructive/40",
    glowClass: "shadow-[0_0_20px_-6px_hsl(var(--destructive)/0.5)]",
  },
};

export function EnforcementPanel({ verdict, isOwner = true }: EnforcementPanelProps) {
  const { toast } = useToast();
  const [overridden, setOverridden] = useState(false);
  const cfg = STATE_CONFIG[verdict.state];
  const Icon = cfg.icon;

  const handleAction = () => {
    if (verdict.state === "BLOCKED" && isOwner && verdict.canOverride) {
      setOverridden(true);
      toast({
        title: "Override approved",
        description: `Next token issuance unlocked for ${verdict.lastEventId ?? "asset"}. Audit trail recorded.`,
      });
    } else {
      toast({
        title: "Review requested",
        description: "Forensic review queued. Floor team will be dispatched within the next cycle.",
      });
    }
  };

  const actionLabel = verdict.state === "BLOCKED" && isOwner && verdict.canOverride
    ? "Approve override"
    : "Request review";

  const ActionIcon = verdict.state === "BLOCKED" && isOwner ? ShieldCheck : FileSearch;

  return (
    <div className={`rounded border p-4 transition-all duration-300 ${cfg.bgClass} ${cfg.borderClass} ${cfg.glowClass}`}>
      <div className="flex items-center justify-between mb-3">
        <p className="text-[10px] font-mono text-muted-foreground tracking-widest uppercase">
          Enforcement · Next Token
        </p>
        <span className="text-[9px] font-mono text-muted-foreground">
          {verdict.lastEventId ?? "—"}
        </span>
      </div>

      <div className="flex items-start gap-3 mb-3">
        <Icon className={`w-7 h-7 shrink-0 mt-0.5 ${cfg.textClass}`} />
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <span className="text-base">{cfg.glyph}</span>
            <span className={`text-lg font-mono font-bold tracking-wide ${cfg.textClass}`}>
              {overridden ? "OVERRIDDEN" : cfg.label}
            </span>
          </div>
          <p className="text-xs font-mono text-foreground mt-1 leading-snug">
            {verdict.reason}
          </p>
        </div>
      </div>

      <p className="text-[10px] font-mono text-muted-foreground leading-relaxed mb-3 pl-10">
        {verdict.detail}
      </p>

      {!overridden && (
        <button
          onClick={handleAction}
          className={`w-full inline-flex items-center justify-center gap-2 px-3 py-2 rounded text-xs font-mono font-semibold transition-all duration-150 active:scale-[0.98] border ${
            verdict.state === "BLOCKED" && isOwner && verdict.canOverride
              ? "bg-destructive/15 hover:bg-destructive/25 text-destructive border-destructive/40"
              : "bg-secondary hover:bg-secondary/70 text-foreground border-border"
          }`}
        >
          <ActionIcon className="w-3.5 h-3.5" />
          {actionLabel}
        </button>
      )}

      {overridden && (
        <p className="text-[10px] font-mono text-[hsl(var(--sovereign))] text-center pt-1">
          ✓ Override recorded — next token unlocked
        </p>
      )}
    </div>
  );
}
