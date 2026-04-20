import type { VerifiedEvent, ForensicData, SystemState, TrustTier } from "./mock-data";

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

export interface ComputedForensics {
  currentSEC: number;
  secBreaches: EventForensics[];
  ear: number;
  earGap: number;
  systemState: SystemState;
  trustTier: TrustTier;
  trustScore: number;
  perEvent: EventForensics[];
  enforcement: EnforcementVerdict;
  authority: AuthorityAlignment;
}

const SEC_RANGE: [number, number] = [0.038, 0.042];

export function computeForensics(
  events: VerifiedEvent[],
  baseForensic: ForensicData
): ComputedForensics {
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

  // Aggregate SEC: total kWh / total kg (excluding zero-yield events)
  const productiveEvents = events.filter((e) => e.yieldKg > 0);
  const totalKwh = productiveEvents.reduce((s, e) => s + e.kwh, 0);
  const totalKg = productiveEvents.reduce((s, e) => s + e.yieldKg, 0);
  const currentSEC = totalKg > 0 ? totalKwh / totalKg : 0;

  // EAR: reported / metered
  const totalReported = events.reduce((s, e) => s + e.kwh, 0);
  const totalMetered = events.reduce((s, e) => s + e.meteredKwh, 0);
  const ear = totalMetered > 0 ? (totalReported / totalMetered) * 100 : 100;
  const earGap = 100 - ear;

  // Breaches
  const secBreaches = perEvent.filter((e) => e.secBreach !== null);
  const hasPhysicsBreach = currentSEC < SEC_RANGE[0] || currentSEC > SEC_RANGE[1];
  const hasEarBreach = ear > 100;
  const breachCount = secBreaches.length;

  // System state derivation
  let systemState: SystemState;
  if (hasPhysicsBreach && hasEarBreach) systemState = "COMPROMISED";
  else if (hasPhysicsBreach || breachCount >= 3) systemState = "COMPROMISED";
  else if (earGap > 5 || breachCount >= 1) systemState = "UNDER REVIEW";
  else systemState = "VERIFIED";

  if (baseForensic.physicsVariance > 2.0) systemState = "SUSPENDED";

  // Trust score: start at 100, deductions
  let trustScore = 100;
  trustScore -= breachCount * 4; // -4 per SEC breach
  trustScore -= Math.max(0, earGap - 3) * 2; // -2 per % gap beyond 3%
  trustScore -= baseForensic.physicsVariance > 2.0 ? 20 : 0;
  trustScore = Math.max(0, Math.min(100, trustScore));

  let trustTier: TrustTier;
  if (trustScore >= 85) trustTier = "INSTITUTIONAL";
  else if (trustScore >= 70) trustTier = "COMMERCIAL";
  else if (trustScore >= 50) trustTier = "SUBPRIME";
  else trustTier = "HIGH RISK";

  // Enforcement / Next Token derivation
  // Inspect most recent event (events assumed sorted desc by timestamp; otherwise pick max)
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

  return {
    currentSEC,
    secBreaches,
    ear,
    earGap,
    systemState,
    trustTier,
    trustScore,
    perEvent,
    enforcement,
  };
}
