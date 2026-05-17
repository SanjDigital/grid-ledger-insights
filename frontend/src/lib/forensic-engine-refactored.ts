import type { VerifiedEvent, ForensicData, SystemState, TrustTier } from "./mock-data";
import type { DecisionBasisData } from "@/hooks/useDecisionBasis";

/**
 * REFACTORED v2.0: Display-Only Forensic Engine (Gap 6 Fix)
 * 
 * All computation moved to backend (trust_scorecard.py):
 * - EAR (Energy Accountability Ratio) — consumed from DecisionBasisData
 * - Trust Score — consumed from DecisionBasisData
 * - System State derivation — now simplified, based on fraud_risk_level
 * 
 * Frontend responsibility:
 * - Format and display pre-computed values
 * - Derive supplementary metrics (per-event forensics, authority alignment)
 * - Render forensic stack for audit trail
 */

export interface EventForensics {
  eventId: string;
  sec: number | null; // kWh/kg, null if no yield
  secBreach: "high" | "low" | null;
  earContribution: { reported: number; metered: number };
}

export type NextTokenState = "CLEARED" | "CONDITIONAL" | "BLOCKED";

export interface EnforcementVerdict {
  state: NextTokenState;
  reason: string;
  detail: string;
  lastEventId: string | null;
  canOverride: boolean;
}

export type LayerStatus = "aligned" | "conflict" | "missing";

export interface AuthorityLayer {
  id: "escom" | "airtel" | "operator";
  name: string;
  role: string;
  status: LayerStatus;
  detail: string;
}

export interface AuthorityAlignment {
  layers: AuthorityLayer[];
  overall: "aligned" | "conflict";
  lastEventId: string | null;
}

/**
 * ComputedForensics now receives pre-computed EAR and Trust Score from API
 */
export interface ComputedForensics {
  // Display values from API (not computed here)
  ear: number; // from DecisionBasisData.energy_accountability_ratio
  earGap: number; // 100 - (ear * 100)
  trustScore: number; // from DecisionBasisData.trust_integrity_score
  
  // Derived from event-level forensics
  currentSEC: number;
  secBreaches: EventForensics[];
  
  // System state simplified based on fraud_risk_level
  systemState: SystemState;
  trustTier: TrustTier;
  
  // Authority alignment and enforcement (derived from events + fraud level)
  perEvent: EventForensics[];
  enforcement: EnforcementVerdict;
  authority: AuthorityAlignment;
}

const SEC_RANGE: [number, number] = [0.038, 0.042];

/**
 * REFACTORED: Forensic engine now accepts pre-computed decision basis from API.
 * No longer computes EAR or Trust Score internally.
 * 
 * @param events - VerifiedEvent array for per-event forensics and authority checks
 * @param decisionBasis - Pre-computed values from backend API
 * @param baseForensic - Display template (for backward compatibility with UI)
 */
export function computeForensics(
  events: VerifiedEvent[],
  decisionBasis: DecisionBasisData,
  baseForensic: ForensicData
): ComputedForensics {
  // Per-event forensics (event-level SEC calculations)
  const perEvent: EventForensics[] = events.map((evt) => {
    const sec = evt.yieldKg > 0 ? evt.kwh / evt.yieldKg : null;
    let secBreach: "high" | "low" | null = null;
    if (sec !== null) {
      if (sec > SEC_RANGE[1]) secBreach = "high";
      else if (sec < SEC_RANGE[0]) secBreach = "low";
    }
    return {
      eventId: evt.id,
      sec,
      secBreach,
      earContribution: { reported: evt.kwh, metered: evt.meteredKwh },
    };
  });

  // Aggregate SEC (local computation — event-level metric, not API)
  const productiveEvents = events.filter((e) => e.yieldKg > 0);
  const totalKwh = productiveEvents.reduce((s, e) => s + e.kwh, 0);
  const totalKg = productiveEvents.reduce((s, e) => s + e.yieldKg, 0);
  const currentSEC = totalKg > 0 ? totalKwh / totalKg : 0;

  // **API-PROVIDED VALUES (No longer computed here)**
  // EAR comes from decisionBasis.energy_accountability_ratio
  const ear = (decisionBasis.energy_accountability_ratio || 1.0) * 100; // Convert to percentage
  const earGap = 100 - ear;
  const trustScore = decisionBasis.trust_integrity_score || 0;

  // Breaches (event-level)
  const secBreaches = perEvent.filter((e) => e.secBreach !== null);

  // System state derivation (simplified, based on fraud_risk_level from API)
  let systemState: SystemState;
  const fraudLevel = decisionBasis.fraud_risk_level;
  const hasPhysicsBreach = currentSEC < SEC_RANGE[0] || currentSEC > SEC_RANGE[1];
  const breachCount = secBreaches.length;

  if (fraudLevel === "HIGH" || (hasPhysicsBreach && breachCount >= 2)) {
    systemState = "COMPROMISED";
  } else if (fraudLevel === "MEDIUM" || hasPhysicsBreach || breachCount >= 1) {
    systemState = "UNDER REVIEW";
  } else {
    systemState = "VERIFIED";
  }

  if (baseForensic.physicsVariance > 2.0) systemState = "SUSPENDED";

  // Trust tier (derived from API trust score)
  let trustTier: TrustTier;
  if (trustScore >= 85) trustTier = "INSTITUTIONAL";
  else if (trustScore >= 70) trustTier = "CORROBORATED";
  else if (trustScore >= 50) trustTier = "SUBPRIME";
  else trustTier = "HIGH RISK";

  // Enforcement verdict (based on event forensics + fraud level)
  const sorted = [...events].sort((a, b) => b.timestamp.localeCompare(a.timestamp));
  const last = sorted[0] ?? null;
  const lastForensic = last ? perEvent.find((p) => p.eventId === last.id) ?? null : null;

  let enforcement: EnforcementVerdict;

  if (baseForensic.physicsVariance > 2.0) {
    enforcement = {
      state: "BLOCKED",
      reason: "Variance >2% — manual review required",
      detail: `Physics variance ${baseForensic.physicsVariance.toFixed(1)}% exceeds 2.0% threshold. Next token issuance suspended pending site audit.`,
      lastEventId: last?.id ?? null,
      canOverride: true,
    };
  } else if (systemState === "COMPROMISED" || hasPhysicsBreach) {
    enforcement = {
      state: "BLOCKED",
      reason: "Physics breach on last cycle",
      detail: `Aggregate SEC ${currentSEC.toFixed(4)} kWh/kg outside calibration window ${SEC_RANGE[0]}–${SEC_RANGE[1]}. Next token blocked until reconciliation.`,
      lastEventId: last?.id ?? null,
      canOverride: true,
    };
  } else if (last && last.verification === "gap") {
    enforcement = {
      state: "BLOCKED",
      reason: "Missing reconciliation (48h breach)",
      detail: `Last cycle ${last.tokenId} flagged GAP — no production confirmation received. Next token blocked.`,
      lastEventId: last.id,
      canOverride: true,
    };
  } else if (lastForensic?.secBreach) {
    enforcement = {
      state: "CONDITIONAL",
      reason: lastForensic.secBreach === "high" ? "Ghost Idling on last cycle" : "Data Manipulation on last cycle",
      detail: `Last event ${last?.tokenId} SEC ${lastForensic.sec?.toFixed(4)} kWh/kg breach. Next token requires operator confirmation.`,
      lastEventId: last?.id ?? null,
      canOverride: false,
    };
  } else if (last && last.verification === "review") {
    enforcement = {
      state: "CONDITIONAL",
      reason: "Last cycle UNDER REVIEW",
      detail: `Token ${last.tokenId} pending floor verification. Next token issuance conditional on review outcome.`,
      lastEventId: last.id,
      canOverride: false,
    };
  } else if (earGap > 5) {
    enforcement = {
      state: "CONDITIONAL",
      reason: `EAR gap ${earGap.toFixed(1)}% — Invisibility Layer audit`,
      detail: `Reported energy trails metered authority by ${earGap.toFixed(1)}%. Next token conditional on reconciliation.`,
      lastEventId: last?.id ?? null,
      canOverride: false,
    };
  } else {
    enforcement = {
      state: "CLEARED",
      reason: "Last cycle VERIFIED",
      detail: `Token ${last?.tokenId ?? "—"} cleared all forensic layers. Next token approved for issuance.`,
      lastEventId: last?.id ?? null,
      canOverride: false,
    };
  }

  // Authority alignment (requires event data — kept from original)
  const authority: AuthorityAlignment = (() => {
    if (!last) {
      return {
        lastEventId: null,
        overall: "conflict",
        layers: [
          { id: "escom", name: "ESCOM Meter", role: "Root of truth · tamper-proof", status: "missing", detail: "No cycle on record" },
          { id: "airtel", name: "Airtel Money", role: "Settlement layer", status: "missing", detail: "No settlement reference" },
          { id: "operator", name: "Operator Logs", role: "Conditional · only if aligned", status: "missing", detail: "No SMS report received" },
        ],
      };
    }

    const escomOk = !!last.tokenId && last.meteredKwh > 0;
    const airtelOk = last.reportedCash > 0 && last.verification !== "gap";
    const lastEar = last.meteredKwh > 0 ? (last.kwh / last.meteredKwh) * 100 : 0;
    const operatorAligned =
      last.verification !== "gap" &&
      lastEar >= 90 &&
      lastEar <= 110 &&
      !(last.kwh > 0 && last.yieldKg === 0);

    const escomLayer: AuthorityLayer = {
      id: "escom",
      name: "ESCOM Meter",
      role: "Root of truth · tamper-proof",
      status: escomOk ? "aligned" : "conflict",
      detail: escomOk
        ? `Token ${last.tokenId} · ${last.meteredKwh.toFixed(1)} kWh metered`
        : "Missing token or zero metered reading",
    };

    const airtelLayer: AuthorityLayer = {
      id: "airtel",
      name: "Airtel Money",
      role: "Settlement layer",
      status: airtelOk ? "aligned" : "conflict",
      detail: airtelOk
        ? `${last.currency} ${last.reportedCash.toLocaleString()} settled`
        : last.verification === "gap"
        ? "ESCOM token consumed but no Airtel receipt"
        : "No settlement record",
    };

    const operatorLayer: AuthorityLayer = {
      id: "operator",
      name: "Operator Logs",
      role: "Conditional · only if aligned",
      status: !escomOk
        ? "missing"
        : operatorAligned
        ? "aligned"
        : "conflict",
      detail: !escomOk
        ? "ESCOM root layer in conflict"
        : last.verification === "gap"
        ? "SMS report missing — 48h reconciliation breach"
        : last.kwh > 0 && last.yieldKg === 0
        ? "Energy reported with zero yield — Holiday Heist signature"
        : lastEar < 90 || lastEar > 110
        ? `Reported ${last.kwh.toFixed(1)} kWh vs metered ${last.meteredKwh.toFixed(1)} kWh (${lastEar.toFixed(1)}%)`
        : `Aligned within tolerance (${lastEar.toFixed(1)}% EAR)`,
    };

    const layers = [escomLayer, airtelLayer, operatorLayer];
    const overall = layers.some((l) => l.status === "conflict") ? "conflict" : "aligned";

    return { layers, overall, lastEventId: last.id };
  })();

  return {
    // API-provided values
    ear,
    earGap,
    trustScore,
    
    // Event-level forensics (computed locally)
    currentSEC,
    secBreaches,
    
    // Derived
    systemState,
    trustTier,
    
    // Authority and enforcement
    perEvent,
    enforcement,
    authority,
  };
}

/**
 * Display formatter: Convert EAR (percentage) to tier classification
 * @param earPercent - EAR as percentage (e.g., 98.5)
 */
export function getEARTier(earPercent: number): TrustTier {
  const earRatio = earPercent / 100;
  if (earRatio >= 0.95) return "INSTITUTIONAL";
  if (earRatio >= 0.90) return "CORROBORATED";
  if (earRatio >= 0.50) return "SUBPRIME";
  return "HIGH RISK";
}

/**
 * Display formatter: Format EAR for display
 */
export function formatEARDisplay(earPercent: number): string {
  return `${earPercent.toFixed(1)}%`;
}

/**
 * Display formatter: Get trust tier label
 */
export function getTrustTierLabel(tier: TrustTier): string {
  const labels: Record<TrustTier, string> = {
    INSTITUTIONAL: "Institutional Grade",
    CORROBORATED: "Corroborated",
    SUBPRIME: "Subprime",
    "HIGH RISK": "High Risk",
  };
  return labels[tier] || tier;
}
