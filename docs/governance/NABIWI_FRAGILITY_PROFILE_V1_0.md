# NABIWI NODE — INFRASTRUCTURE FRAGILITY PROFILE
**M1 Corridor, Malawi**
**Agro‑Processing Production Node**
**Observation Window: March 2026 (31‑day window)**
**Verified Production Cycles: 705**
**Qualification Window: 62 consecutive clean cycles (≥90% adherence)**
**Classification: ISIC Rev. 4, Class 7490**

*Repository: github.com/SanjDigital/grid‑ledger‑insights | SSRN DOI: [pending] | Version: V1.0*

---

## 1. Executive Delta

| Metric | Value |
|---|---|
| Gross Energy Availability (metered kWh) | 3,210 kWh |
| Verified Production Throughput (cycles completed) | 64.1% |
| Infrastructure‑Adjusted Throughput | 94.0% |
| **Infrastructure Fragility Delta** | **29.9 pp** |

**The delta represents verified production interruption attributable to infrastructure instability rather than operator non‑performance. In this profile, the infrastructure‑adjusted throughput and the delta are methodology demonstrations — they illustrate the separation the architecture produces once sovereign corroboration data sources are integrated. The canonical throughput is a direct production measurement.**

### Infrastructure Availability Strip

| Indicator | Value |
|---|---|
| Grid Stability Index (0–100) | 38 |
| Outage Frequency (methodology demonstration, 31‑day window) | 12 events |
| Mean Recovery Time | 4.6 hours |
| Verified Throughput Continuity (clean‑cycle ratio) | 0.93 |
| Exclusion Events (Tier 1–2) | 12 |

### Exclusion Table — Methodology Demonstration

The following table illustrates the exclusion classification logic defined in the Outage Adjustment Standard v1.0 and Outage Registry Specification v1.0. Classifications shown are representative — they demonstrate how the architecture assigns exclusion tiers when sovereign or cluster corroboration is present. The 705-cycle Nabiwi dataset was sealed from SMS production reports. ESCOM registry records and Airtel Money confirmations exist independently and will be cross‑referenced as external data source integration is completed. No claim is made that the specific cycles listed below were excluded on the basis of actual ESCOM registry entries at the time of sealing.

| Cycle ID | Classification | Included in Throughput? | Methodology Basis |
|----------|---------------|------------------------|-------------------|
| NAB‑042 | INTERRUPTED | No | Tier 1 — would require ESCOM registry confirmation |
| NAB‑044 | MISSING | No | Incomplete evidentiary chain |
| NAB‑051 | DISPUTED | No | Seal mismatch example |
| NAB‑058 | INTERRUPTED | No | Tier 2 — would require cluster concurrency (3+ nodes) |
| NAB‑067 | INTERRUPTED | No | Tier 1 — would require ESCOM registry confirmation |
| NAB‑072 | INTERRUPTED | No | Tier 2 — would require cluster concurrency |
| … | … | … | … |

*The exclusion logic is frozen and independently replayable. The classifications above demonstrate the methodology. They are not attested production exclusions. Production exclusion tables will be published as sovereign corroboration data is integrated.*

---

## 2. Node‑Level Operational Profile

**Production Consistency**

| Metric | Value |
|---|---|
| Average cycles per day | 1.3 |
| Mean kWh per cycle | 59.9 kWh |
| Verified Uptime (clean cycles / total) | 93% |
| Clean‑Cycle Ratio | 0.93 |
| Seal Validity Rate (replay‑tested) | 100% |

**Infrastructure Stress Indicators**

| Indicator | Observation |
|---|---|
| Outage Clustering | 8 of 12 events in afternoon window (14:00–18:00) |
| Voltage Instability Proxy Events | 2 partial‑load events, 1 surge |
| Recovery Lag | Mean 4.6 h; max 18 h |
| Energy Interruption Density | 0.39 events per day |

**Operational Classification**

| Category | Status |
|---|---|
| Operator Discipline | HIGH (62‑cycle clean run, 93% adherence) |
| Infrastructure Reliability | LOW (IAF 0.38; 12 classified outages — methodology demonstration) |
| Verification Integrity | HIGH (zero seal failures; replayable chain) |

*The tri‑separation is the institutional innovation. Most credit systems collapse these three dimensions into a single score, thereby punishing the operator for grid fragility. GridLedger separates them.*

---

## 3. Methodology Boundary

### Data Provenance and Verification Boundary

The 705‑cycle Nabiwi dataset was ingested from SMS production reports and cryptographically sealed. ESCOM prepaid token records and Airtel Money receipts — the Tier 1 sovereign verification sources — exist independently at the utility and payment service provider level and will be cross‑referenced as external data source integration is completed. The exclusion logic and Infrastructure‑Adjusted EAR presented in this report are derived from the sealed cycle records currently available in the development database. Full sovereign corroboration will be reflected in subsequent versions of this profile as integration proceeds.

The Tier 1 and Tier 2 exclusion classifications appearing in the Exclusion Table are methodology demonstrations — they illustrate the architecture's classification logic, not attested exclusions based on ingested ESCOM records. No claim is made that specific cycles were excluded on the basis of actual ESCOM registry entries at the time of sealing.

### Observation Boundary

The window covers 31 days of production at the Nabiwi‑Chitsazo maize mill, Lilongwe, Malawi. All cycles were sealed prior to analysis. No cycle was reclassified post‑hoc.

### Verification Boundary

A cycle is included in verified throughput only if it possesses a valid Cycle Seal, a matched ESCOM prepaid token record (pending full integration), and an independently confirmable Airtel Money receipt (pending full integration). The canonical throughput figure (64.1%) is derived directly from sealed cycles and SMS production reports.

### Replayability

Every metric in this report can be independently recomputed using the open‑source GL‑1 Protocol (github.com/SanjDigital/grid‑ledger‑insights) and the public Trust Anchor CSV. No access to GridLedger’s operational servers is required.

### Exclusion Rules

The exclusion of any cycle from the Infrastructure‑Adjusted window follows the Outage Adjustment Standard v1.0: only cycles with sovereign (ESCOM registry) or cluster‑concurrency (≥3 nodes) corroboration are removed. Uncorroborated operator reports are retained in the log but do not influence adjusted metrics.

### Evidentiary Hierarchy

| Tier | Source | Function |
|---|---|---|
| Tier 1 — Sovereign | ESCOM registry, Airtel API, Met. alert | Automatic exclusion; fully independent |
| Tier 2 — Cluster | ≥3 nodes in same zone lose power | Automatic exclusion; computationally independent |
| Tier 3 — Documentary | Operator photo + third‑party receipt | Classification only; no adjustment |
| Tier 4 — Attestation | Operator SMS | Contextual log; no adjustment |
| Tier 5 — Retrospective | Post‑hoc claim | Pattern analysis; does not alter sealed history |

### Failure‑Domain Taxonomy

Operational failures (server loss, DB corruption) do not affect sealed history. Verification failures (hash mismatch, replay divergence) invalidate the affected seal. Physical input compromise (meter bypass, token forgery) is the residual risk disclosed in the Architecture Statement and mitigated by Phase 2 clamp sensors.

### Reproducibility Anchors

- **GitHub Repository:** github.com/SanjDigital/grid‑ledger‑insights
- **SSRN Working Paper:** [DOI pending]
- **Trust Anchor CSV:** Publicly accessible in the repository’s `/data/` directory

---

*This document is a technical submission, not a commercial proposal. It is provided to support independent review of the verification architecture and its replayability assumptions under adverse operational conditions.*

*GridLedger IP Ltd — Verification Authority · ISIC Rev. 4, Section M, Division 74, Class 7490 · May 2026*