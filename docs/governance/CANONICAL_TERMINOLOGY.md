# CANONICAL TERMINOLOGY

**GridLedger IP Ltd — Verification Authority**
**Version 1.2 · May 2026**

---

## Mission Statement

| Layer | Formulation |
|-------|-------------|
| **Public** | GridLedger transforms energy‑gated production into replayable financial evidence. |
| **Technical** | An energy‑mediated verification layer for replayable capital formation. |
| **Institutional** | Separating infrastructure instability from operator performance through deterministic production verification. |
| **Operator** | Money only moves when the machine is working. |

---

## Cycle Classifications

| Term | Definition |
|------|------------|
| **SEALED** | A cycle with a valid cryptographic seal, independently replayable. |
| **INTERRUPTED** | A cycle halted by independently corroborated infrastructure unavailability. No penalty. |
| **MISSING** | A cycle where remittance was expected but not received within the detection window. |
| **DISPUTED** | A cycle under active investigation due to evidence conflict. |
| **CORROBORATED_PARTIAL** | A cycle where one external verification rail is confirmed while another is delayed. Sealed with confirmed fields intact; pending fields held open. Not a penalty state. Resolves to SEALED upon full corroboration. |

---

## Verification Classifications

| Term | Definition |
|------|------------|
| **VERIFIED** | Cycle passed all verification checks. |
| **REVIEW** | Cycle under active review. |
| **GAP** | Forensic gap detected — missing evidence. |

---

## Trust & Infrastructure Tiers

| Term | Definition |
|------|------------|
| **CORROBORATED** | Trust tier: evidence from multiple independent sources supports the classification. |
| **INFRASTRUCTURE_STABLE** | Tier A: IAF ≥ 0.70. Standard verification tolerance. |
| **INFRASTRUCTURE_DEGRADED** | Tier B: 0.40 ≤ IAF < 0.70. Widened tolerance. |
| **INFRASTRUCTURE_UNSTABLE** | Tier C: IAF < 0.40. Extended tolerance + audit flag. |

---

## Anomaly Classifications

| Term | Definition |
|------|------------|
| **ZERO‑YIELD ANOMALY** | Energy consumed with zero declared output. |
| **TIMING ANOMALY** | Production cycle that deviates from the expected temporal window. |
| **CORRELATED ANOMALY** | Anomaly detected simultaneously across multiple independent nodes. |

---

## Architectural Terms

| Term | Definition |
|------|------------|
| **Production‑Permission Layer** | The system layer that gates capital deployment against verified energy consumption. Production cannot occur without an energy token; capital cannot be deployed without a verified cycle. The token is the permission. |
| **Infrastructure Fragility Delta** | The difference between canonical throughput and infrastructure‑adjusted throughput, expressed in percentage points. Measures production lost to independently corroborated infrastructure unavailability. |
| **Infrastructure Availability Factor (IAF)** | 1 − (Tier 1–2 interrupted cycles / total attempted cycles). |
| **Replayability Constraint** | If a condition cannot be independently recomputed from sealed inputs, it does not belong inside the verification boundary. |
| **Triple‑Anchor Dispute Resolution** | Any future dispute about a cycle classification is resolved by replaying it against the frozen constitutional state publicly committed at the time. |

---

## Prohibited Vocabulary (External)

The following terms must never appear in GridLedger external documents:

- AI, Artificial Intelligence
- Blockchain
- Fintech
- Tokenisation
- Platform
- Sovereign (except in "sovereign data source," referring to ESCOM/Airtel as independent external inputs)
- Startup
- Predictive lending
- Automated underwriting
- AI scoring

---

## Removed Dashboard Vocabulary

The following terms were present in earlier dashboard versions and have been permanently removed:

- SOVEREIGN → replaced with SEALED
- COMMERCIAL → replaced with CORROBORATED
- SEC BREACH → replaced with PHYSICS ALERT
- FL00R GEN. → replaced with VERIFIED
- HOLIDAY HEIST → replaced with ZERO‑YIELD ANOMALY
- LEADING DAY → replaced with TIMING ANOMALY
- M1 CORRIDOR → removed as anomaly classification; geographic context belongs in node metadata

---

*GridLedger IP Ltd — Verification Authority*
*ISIC Rev. 4, Section M, Division 74, Class 7490 | May 2026*