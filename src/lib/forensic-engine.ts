import type { VerifiedEvent, ForensicData, SystemState, TrustTier } from "./mock-data";

export interface EventForensics {
  eventId: string;
  sec: number | null; // kWh/kg, null if no yield
  secBreach: "high" | "low" | null;
  earContribution: { reported: number; metered: number };
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

  return {
    currentSEC,
    secBreaches,
    ear,
    earGap,
    systemState,
    trustTier,
    trustScore,
    perEvent,
  };
}
