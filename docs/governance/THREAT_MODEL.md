# THREAT MODEL

**GridLedger IP Ltd — Verification Authority**
**Version 1.0 · May 2026**

---

## 1. Failure-Domain Taxonomy

GridLedger distinguishes between three categories of failure, each with distinct institutional implications.

| Failure Domain | Impact on Sealed History | Impact on Operations | Recovery |
|---|---|---|---|
| **Operational Failure** (VPS loss, DB corruption, API downtime, network silence) | None — sealed history is externally anchored | Service interruption for dashboards and APIs | Restore operational layer from backup; verification layer unaffected |
| **Verification Failure** (hash mismatch, Merkle divergence, replay inconsistency) | Seal invalidated — the affected cycle is flagged | Trust in the seal chain is compromised for the affected window | Independent replay identifies the exact point of divergence; affected cycle must be re‑verified or excluded |
| **Physical Input Compromise** (ESCOM token forgery, Airtel collusion, meter bypass) | Seal is valid but based on falsified inputs | Economic loss may occur before statistical detection | Physical audit triggered; clamp sensor integration (Phase 2) is the permanent solution |

---

## 2. Adversarial Threat Taxonomy

| Threat | Conventional Severity | GridLedger Severity | Rationale |
|--------|----------------------|---------------------|-----------|
| SQL injection | Severe | Severe — operational disruption | Standard web application hardening required |
| Credential leak | Severe | Severe — operational compromise | Runtime-bound authentication mitigates; rotation protocol active |
| Seal replay divergence | N/A | Critical — constitutional failure | Any hash mismatch between published seal and independently recomputed seal invalidates the affected cycle |
| Repository/backend merge | N/A | Critical — constitutional failure | Operational code in the Trust Anchor collapses the operational/verification split |
| DDoS | High | High — availability loss | Mitigated by Vercel/Railway infrastructure |
| Hidden proprietary transform | N/A | Admissibility collapse | Any undocumented transformation of data between raw inputs and seal output destroys the replayability guarantee |
| Inaccessible auditor path | N/A | Institutional invalidation | If the Auditor's Toolkit cannot fetch raw inputs from the public repository without credentials, the architecture's central claim fails |
| Force‑push to Trust Anchor | N/A | Critical — historical rewrite | Branch protection rules, required signatures, and external hash logging are mitigations; THREAT_MODEL.md must name this vector explicitly |

---

## 3. Trust Anchor Attack Surface

GitHub does not natively enforce append‑only semantics. A force‑push can rewrite history. The following mitigations are required:

- **Branch protection rules** — restrict force‑push to designated administrators
- **Required commit signatures** — verify authorship of every commit to the Trust Anchor
- **External hash logging** — publish the latest commit hash to an independent channel (e.g., SSRN working paper metadata, institutional transmission cover notes)
- **Independent replication** — any auditor can clone the repository and verify the seal chain against their own recomputation

---

## 4. Silent Corruption Detection

GridLedger does not prevent silent corruption. It guarantees that corruption will produce a hash mismatch that is externally visible.

- A compromised operational database can be altered
- The published seal chain remains independently recomputable from raw inputs
- Any alteration creates a detectable divergence between the published seal and the independently recomputed seal
- The Auditor's Toolkit detects this divergence deterministically

---

## 5. Residual Risk Disclosure

The following risks are acknowledged and documented:

1. **Adversarial Input Risk:** A disciplined operator with a parallel meter can sustain spoofing through Layers 1–2. Statistical detection is active. Physical clamp sensors (Phase 2) are the engineered solution.
2. **Pre‑Phase 2 Physical Verification:** The system does not yet independently verify physical throughput via direct sensor integration.
3. **Detection Latency:** The worst‑case detection window for a missing cycle is 72 hours by design.
4. **Conditional Enforcement Gap:** Full deterministic capital enforcement awaits the Lender Policy Module.

---

*GridLedger IP Ltd — Verification Authority*
*ISIC Rev. 4, Section M, Division 74, Class 7490 | May 2026*