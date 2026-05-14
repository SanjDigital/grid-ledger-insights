<p align="center">
  <img src="docs/brand/wordmark_dark.png" alt="GridLedger | Enforcement Protocol" width="480"/>
</p>

---

> If you control energy, you control revenue.  
> If you control revenue, you control outcomes.

---

## Security Notice

**This repository contains no secrets.** All API keys and credentials are supplied via environment variables at runtime. See [`.env.example`](.env.example) for required configuration. Never commit `.env`, `.env.local`, or similar files containing actual credentials.

---

## The Problem

Capital cannot reach informal industrial markets — maize mills, agro-processors, cold storage operators across sub-Saharan Africa — because truth cannot be established.

Revenue is cash-based. Operators control their own reporting. No independent production data exists. The fraud surface is structural, not incidental.

This is not a trust problem. It is a data architecture problem.

---

## The Insight

Every prior solution starts from the wrong place: verifying what operators *report*.

GridLedger starts from what operators *cannot forge*: **energy consumption**.

A maize mill processing 10 tonnes of grain consumes a predictable quantity of electricity. That relationship is governed by physics. It cannot be falsified without physically altering the machine.

Energy is the only non-forgeable input in these systems.

---

## The Solution

GridLedger is a physics-first accounting system. It does not record operator reports. It converts energy into enforceable financial commitments:

```
Energy (kWh)  →  Expected Revenue  →  Enforced Compliance
```

By controlling the energy supply, GridLedger makes compliance structurally required — not monitored after the fact.

---

## Mechanism — Per-Cycle Enforcement

Each operational cycle is a closed financial unit:

```
ALLOCATE  →  energy token issued (59.9 kWh)
PRODUCE   →  operator runs on allocated energy
REMIT     →  cash recorded against expectation
RECONCILE →  variance measured (±5% tolerance)
ENFORCE   →  next allocation gated on compliance
```

**No compliance → No energy → No production.**

The gate is not a policy. It is a physical constraint.

### Enforcement Parameters

| Parameter | Value |
|---|---|
| Cycle size | 59.9 kWh |
| Variance tolerance | ±5% |
| Missing cycle timeout | 48 hours |
| Adherence penalty | Quadratic — `adherence²` |
| Latency penalty | Step function (24h / 48h / 72h thresholds) |

The quadratic adherence penalty is deliberate. Small compliance drops produce disproportionate rate reductions — creating behavioural pressure without manual intervention:

| Adherence | Rate Multiplier |
|---|---|
| 100% | 1.000 |
| 95% | 0.903 |
| 85% | 0.723 |
| 70% | 0.490 |
| 55% | 0.303 |

An operator at 55% efficiency faces a 70% capital reduction. Automatically.

---

## Architecture

GridLedger is a control loop, not a reporting tool.

```
Token Allocation
      ↓
Cycle + Revenue Expectation
      ↓
Cash Remittance
      ↓
Variance Detection
      ↓
   CLOSED / DISPUTED
      ↓
Dynamic Advance Rate
(base × trust × adherence² × latency)
      ↓
Next Allocation: ALLOW / REDUCE / BLOCK
```

### Node States

| State | Trigger | Effect |
|---|---|---|
| `PENDING` | Cycle active | Blocks new allocation |
| `CLOSED` | Remittance verified | Feeds capital score |
| `DISPUTED` | Variance > 5% | Blocks allocation, opens review |
| `MISSING` | No remittance after 48h | Blocks allocation, flags breach |

---

## Deployment — No Sensors Required

The CIU (token device) is centrally controlled. All energy passes through GridLedger. Production capacity is physically constrained by allocated energy.

**Financial determinism without hardware dependency.**

This is deployable today, in any market with a controllable energy supply. Phase 2 adds clamp-based sensing — converting assumed determinism to verified determinism. The enforcement architecture does not change.

---

## The Truth Layer

Each cycle generates — automatically, as a byproduct of enforcement:

- **Expected Revenue Rate (ERR)**: kWh × node tariff
- **Actual Revenue Rate (ARR)**: cash remitted / kWh allocated
- **Variance**: deviation from expectation

Over time, the true economic profile of each node emerges. Production efficiency. Revenue reliability. Operator behaviour under pressure.

No surveys. No audits. No self-reporting.

This dataset does not exist for informal operators today. GridLedger produces it as a consequence of operating the infrastructure.

**The enforcement mechanism is the data collection mechanism. They are the same thing.**

This is what makes it scalable. Every node added to the network produces a new stream of verified economic data — without additional audit cost.

---

## Glass Box Certification

<p align="left">
  <img src="docs/brand/glass_box_icon.svg" alt="Glass Box Certified" width="80"/>
</p>

Operators who demonstrate sustained compliance earn the **Glass Box Certified** mark.

The name is deliberate. A glass box is the opposite of a black box. Every data point behind the certification is generated automatically by the enforcement system — no auditor, no self-reporting, no subjective judgement.

### Certification Criteria

| Criterion | Threshold |
|---|---|
| Consecutive clean cycles | 10 minimum |
| Cycle adherence (cash / expected) | ≥ 90% |
| Unresolved DISPUTED cycles | 0 open |
| MISSING cycles in window | 0 in last 10 |
| Remittance latency | < 48h average |

### Why It Matters

Certified operators gain a verified performance signal that does not exist anywhere else in their market. This signal travels — to lenders, buyers, development finance institutions, and supply chain partners.

GridLedger does not need a sales team at scale. Certified operators create demand for certification among their peers. The enforcement infrastructure becomes a reputation infrastructure.

**The certification is earned. It cannot be purchased, appealed, or assigned.**

---

## Competitive Position

| Approach | Failure Mode |
|---|---|
| Agent-based monitoring | High cost, low frequency, gameable |
| Self-reported data + audit | Fraud surface too large |
| Mobile money transaction data | Incomplete; misses cash economy |

GridLedger is not a better version of any of these. It is a different category: infrastructure-level enforcement, where compliance is physically required rather than socially monitored.

---

## Deployment Status

**Live: NABIWI Node, Malawi 🇲🇼**

| Component | Status |
|---|---|
| Token custody (CIU control) | ✅ Live |
| Per-cycle enforcement engine | ✅ Live |
| Cash remittance + variance detection | ✅ Live |
| Dynamic advance rate computation | ✅ Live |
| Capital gate | ✅ Live |
| Dispute resolution + audit trail | ✅ Live |
| Missing cycle detection | ✅ Live |
| Glass Box Certification engine | ✅ Live |
| Clamp-based energy sensing | ⏳ Phase 2 |
| Cross-node benchmarking | ⏳ Phase 3 |

---

## Roadmap

**Phase 1 — Control** *(current)*  
Token custody. Per-cycle enforcement. Revenue reconciliation. Capital gating. Glass Box Certification.

**Phase 2 — Verification**  
Independent energy validation via clamp meters. Verified determinism. Glass Box Certification backed by sensor data.

**Phase 3 — Network Intelligence**  
Cross-node benchmarking. Automated capital allocation. Glass Box as a recognised standard for informal industrial infrastructure finance across sub-Saharan Africa.

---

## Stack

Python · FastAPI · SQLModel · SQLite → PostgreSQL

Offline-capable. Single-node deployable. No cloud dependency in Phase 1.

---

## Context

**Geography**: Malawi 🇲🇼 — scalable across sub-Saharan Africa  
**Sector**: Agro-processing  
**Stage**: Live pilot, 2026  
**Structural gap**: Billions in stranded capital cannot move because accountability infrastructure does not exist

GridLedger is the accountability infrastructure.

---

*GridLedger is not a fintech product.*  
*It is the substrate that makes fintech possible where reliable data has never existed.*
