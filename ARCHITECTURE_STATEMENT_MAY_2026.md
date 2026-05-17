# GRIDLEDGER IP LTD — ARCHITECTURE STATEMENT
**Verification Authority · ISIC 7490**
**May 2026 · Private & Confidential**

---

## I. SYSTEM PURPOSE

GridLedger IP Ltd operates a verification infrastructure that converts physical energy events into cryptographically sealed, independently replayable records. The system does not lend, hold funds, process payments, or serve as the system-of-record for balances. Its sole function is to produce evidence of production and cash realisation that any auditor can verify without trusting the operator, the server, or GridLedger itself.

---

## II. OPERATIONAL INFRASTRUCTURE VS. VERIFICATION INFRASTRUCTURE

GridLedger separates its infrastructure into two architecturally distinct layers. This separation is the foundation of the system's institutional credibility.

| Layer | Function | Storage | Persistence Model |
|---|---|---|---|
| **Operational Infrastructure** | Application logic, APIs, dashboards, mandate submissions, friction analytics, Trust Scorecard computation | SQLite database on a persistent VPS | Routine backup; replaceable |
| **Verification Infrastructure** | Cycle seals, Merkle roots, cryptographic hashes, deterministic replay data | GitHub repository (public, append-only CSV); Trust Anchor (external, independently verifiable) | Immutable; permanently reconstructible |

**Principle:** The operational layer may be upgraded, migrated, or restored from backup. The verification layer must be independently replayable from raw, externally held inputs by any party without access to the operational database.

**Result:** Loss of the VPS, compromise of the application server, or even a complete operational failure does not invalidate sealed history. The verification chain survives operational infrastructure failure intact and independently verifiable.

---

## III. CHAIN OF CUSTODY MODEL

GridLedger's Chain of Custody defines the sequence of transformations that convert a raw physical event into a sealed, independently verifiable record. Each step is hashed, timestamped, and attributable.

```
Step 1 — PHYSICAL EVENT
  59.9 kWh energy token allocated to node.
  Production capacity physically constrained by token.
  Source: ESCOM prepaid token record (utility-originated, independently verifiable).

Step 2 — SIGNED PAYLOAD
  Operator submits event signed with Ed25519 key.
  Canonical JSON normalisation applied.
  Identity verified. Activity not yet trusted.

Step 3 — CONTINUITY CHECK
  previous.meter_close == current.meter_open
  Any break in sequence: GapBreachError raised immediately.
  Missing or reordered events cannot pass this gate.

Step 4 — FINANCIAL TRANSLATION
  Expected Revenue = allocated_kWh × revenue_rate_per_kWh
  Actual Revenue = cash_remitted / kWh_allocated
  Variance computed. Tolerance: ±5%.
  Energy Accountability Ratio = reported_kWh / metered_kWh

Step 5 — FORENSIC ANCHOR (Merkle)
  All window events hashed into Merkle tree.
  Root stored as cryptographic anchor.
  Changing, inserting, deleting, or reordering any event changes the root.
  Auditor can recompute root from raw events at any time.

Step 6 — TRUST SCORECARD
  Reconciliation Score (50%): physical vs. ledger variance
  Consistency Score (30%): statistical anomaly detection
  Governance Score (20%): signature and RBAC enforcement
  EAR Tier applied (TIER 1/2/3) via Bounded Imperfection Doctrine.
  Score drives financing recommendation.

Step 7 — POLICY EXECUTION ENGINE (PXE)
  Verified state → deterministic Capital Action Object (CAO).
  No human interpretation inside execution boundary.
  Identical inputs → identical outputs. Always.
  Capital gate: CLEARED / CONDITIONAL / BLOCKED.
```

Each step produces hashed, timestamped outputs. The Chain of Custody is fully replayable from raw ESCOM token records and Airtel Money receipts — both externally held and independently accessible.

---

## IV. EVENT-SOURCED VERIFICATION LOGIC

GridLedger's verification model is inherently event-sourced. The system does not maintain a mutable "current state" that is overwritten. It maintains an append-only sequence of cycle events, each representing a state transition.

- Token issued → cycle active
- Remittance received → cycle closed
- Seal generated → cycle anchored
- Trust Score updated → next state authorised

The GVCF facility is an event-driven state machine. Each Capital Action Object is the deterministic output of the preceding verified events. There is no "balance" to alter. There is only the next event in the sequence, and it must be consistent with all prior events or it will not seal.

---

## V. INDEPENDENT REPLAYABILITY

The defining property of GridLedger's verification layer is that **any party with access to the raw inputs can independently reproduce every seal, every Merkle root, and every Trust Score that the system has ever produced.**

**Required inputs (all externally held):**
- ESCOM prepaid token purchase records
- Airtel Money remittance confirmations
- Operator-submitted production reports (signed)

**Replay procedure:**
1. Retrieve raw events from the public GitHub repository.
2. Run the open-source Verification Protocol (GL-1) against the event sequence.
3. Recompute all hashes, Merkle roots, and Trust Scores.
4. Compare outputs to the published seal chain.

If the outputs match: the seal chain is verified.
If they diverge: the seal chain has been tampered, and the point of divergence is identified.

**Institutional implication:** A credit committee, auditor, or regulator does not need to trust GridLedger's operational infrastructure. They need only the raw inputs and the open-source protocol. The verification is independently reproducible.

---

## VI. INTEGRITY GUARANTEES

GridLedger does not claim that its servers are impossible to breach. It does not claim that bad data can never enter the system. It claims the following:

1. **Operational compromise does not enable historical rewrite.** A compromised application server can disrupt future cycles but cannot alter sealed history, because the sealed history is anchored externally and can be independently verified against the raw inputs.

2. **Database mutation does not imply proof-chain mutation.** Altering the SQLite database changes the operational record. It does not change the Merkle roots published in the GitHub repository. Any discrepancy between the two is immediately detectable by comparing the operational output to the independently replayable anchor chain.

3. **Silent corruption is not prevented; it is made detectable.** The system does not guarantee that data will never be corrupted. It guarantees that corruption will produce a hash mismatch that is externally visible to any auditor who replays the chain.

4. **The verification chain is epistemically independent of the application layer.** The raw inputs exist outside GridLedger's infrastructure. The protocol is open-source. The anchor chain is publicly accessible. No single party controls all three.

**The canonical formulation:**

> *"GridLedger does not require institutions to trust the operator, the server, or even GridLedger itself. It requires only that the verification chain remain independently replayable."*

---

## VII. SEAL INVALIDITY — FORMAL DEFINITION

A previously issued seal is considered **invalidated** when any of the following conditions is detected during replay verification:

| Condition | Detection Method |
|---|---|
| **Anchor mismatch** | Published Merkle root ≠ recomputed Merkle root from raw events |
| **Merkle divergence** | Intermediate node hash in the published tree does not match the recomputed tree |
| **Replay inconsistency** | Deterministic PXE output from raw inputs does not match the published Capital Action Object |
| **Timestamp discontinuity** | Event timestamp ordering in the published chain violates the sequence established by the raw inputs |
| **Chain discontinuity** | A gap appears in the published seal sequence that is not present in the raw event sequence |

Seal invalidity is a purely technical state. It does not require a legal determination, an admission of fault, or an investigation into intent. It is established by deterministic recomputation alone.

---

## VIII. HONEST LIMITS

The following limitations are acknowledged and documented:

1. **Adversarial input risk.** A disciplined operator with a parallel ledger and consistent meter spoofing can sustain fraudulent reporting through Layers 1 and 2. Detection is deferred to statistical forensics (Layer 3). Physical clamp sensors (Phase 2) are the engineered solution.

2. **Pre-Phase 2 physical verification.** The system does not yet independently verify physical throughput via direct sensor integration. Physical readings are externally supplied and reconciled against ESCOM metering data.

3. **Detection latency.** The worst-case detection window for a missing cycle is 72 hours by design. Leakage can occur within that window before enforcement triggers.

4. **Conditional enforcement gap.** Full capital enforcement requires the Lender Policy Module, which is not yet deployed. CONDITIONAL state decisions currently retain lender discretion.

5. **Operator dependency.** The model performs at verified levels under sustained cycle frequency. In low-demand environments or under supply disruption, cycle frequency drops and the yield curve compresses.

These limits are stated in every investor document, every protocol version, and every regulatory brief. A verification authority that overstates its guarantees destroys the only thing it sells.

---

## IX. DATA SOVEREIGNTY POSITION

GridLedger's sealed cycle data remains under the jurisdictional control of the node operator and the host country. The raw inputs — ESCOM records, Airtel receipts, operator reports — are generated and held within Malawi. The verification chain is anchored in a public repository accessible to any auditor. No data is exclusively controlled by GridLedger, by a foreign government, or by any single institution.

This architecture is consistent with Zambia's stated position on data sovereignty, Malawi's regulatory environment, and the principles articulated by UNDP Malawi's Resident Representative regarding "partnership, not aid."

---

## X. FAILURE DOMAINS

GridLedger distinguishes between three categories of failure, each with distinct institutional implications:

| Failure Domain | Impact on Sealed History | Impact on Operations | Recovery |
|---|---|---|---|
| **Operational failure** (VPS loss, DB corruption, API downtime) | None — sealed history is externally anchored | Service interruption for dashboards and APIs | Restore operational layer from backup; verification layer unaffected |
| **Verification failure** (hash mismatch, Merkle divergence, replay inconsistency) | Seal invalidated — the affected cycle is flagged | Trust in the seal chain is compromised for the affected window | Independent replay identifies the exact point of divergence; affected cycle must be re-verified or excluded |
| **Physical input compromise** (ESCOM token forgery, Airtel collusion, meter bypass) | Seal is valid but based on falsified inputs | Economic loss may occur before statistical detection | Physical audit triggered; clamp sensor integration (Phase 2) is the permanent solution |

**Institutional implication:** The system's integrity model does not require all failure modes to be eliminated. It requires that each failure mode produces a detectable signal, and that the signal triggers a defined response.

---

## XI. INFRASTRUCTURE DECISIONS

**Pilot phase (May 2026):**
- **Frontend:** Vercel (global CDN, instant deployment).
- **Backend:** Persistent VPS (DigitalOcean Droplet, Frankfurt region) running FastAPI + Uvicorn.
- **Database:** SQLite (append-oriented, portable, simple snapshotting).
- **Verification anchor:** GitHub public repository (CSV, independently accessible).
- **Backup:** Daily `sqlite3 .dump` to object storage with versioning and delete protection. Weekly off-server checksum-verified snapshots. Quarterly restoration tests.

**Migration triggers:**
- SQLite → PostgreSQL: when concurrent institutional access, multiple writers, or replication requirements emerge.
- Single VPS → distributed: when geographically dispersed nodes require regional API endpoints.
- GitHub anchoring → additional anchors: when institutional requirements demand multiple independent attestation points.

**Principle:** Infrastructure complexity is added only when the existing simplicity demonstrably constrains institutional adoption. Premature distribution is a greater risk than delayed scaling.

---

## XII. INSTITUTIONAL IMPLICATIONS

For any institution evaluating GridLedger — a commercial bank, a development finance institution, an audit firm, or a regulator — the Architecture Statement provides the following assurances:

1. **Operational risk is contained.** Loss of GridLedger's servers does not destroy the verification record.
2. **Historical integrity is independently verifiable.** No institution needs to trust GridLedger's operational assertions; it can verify them directly.
3. **Data sovereignty is preserved.** Raw inputs remain in-country; verification is accessible without exclusive control.
4. **Failure is bounded and defined.** Each failure mode has a known detection method and a defined institutional response.
5. **The system's honest limits are documented.** No capability is claimed that the system does not possess.

---

*GridLedger IP Ltd — Verification Authority*
*ISIC Rev. 4, Section M, Division 74, Class 7490*
*Architecture Statement · May 2026 · Private & Confidential*
