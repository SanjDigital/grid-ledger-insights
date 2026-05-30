# DATASET CLASSIFICATION STANDARD V1.0

**GridLedger IP Ltd — Verification Authority**
**Version 1.0 · May 2026**
**Repository:** github.com/SanjDigital/grid-ledger-insights

---

## 1. Purpose

This Standard defines the formal hierarchy of dataset tiers produced by the GridLedger verification architecture. Each tier is defined by a specific, reproducible extraction criterion. The purpose is to eliminate ontology leakage — the conflation of different dataset subsets that carry different evidentiary weight — and to ensure that every institutional document references the correct tier by name.

This Standard is a child document of the Node Qualification Standard v1.0 and Canonical Terminology v1.2. Where a definition conflicts with a frozen governance document, the parent document governs.

---

## 2. The Dataset Hierarchy

### 2.1 Operational Corpus

**Definition:** The complete set of all cycle records in the operational database for a given node, regardless of status, classification, or integrity.

**Extraction Criterion:**
```sql
SELECT * FROM cycle WHERE mill_id = '<NODE_ID>'
```

**Institutional Meaning:** The operational corpus is the raw archive. It contains sealed cycles, unsealed cycles, missing cycles, disputed cycles, and records that may be incomplete or corrupted. It is the source from which all other tiers are derived. It is not itself an evidentiary product.

**Example:** The Nabiwi operational corpus contains 709 records.

---

### 2.2 Sealed Cycle

**Definition:** A cycle that has been committed to the operational database with `status = 'SEALED'` and possesses a valid `cycle_seal` hash. A sealed cycle has passed the ingestion pipeline and is cryptographically anchored.

**Extraction Criterion:**
```sql
SELECT * FROM cycle WHERE mill_id = '<NODE_ID>' AND status = 'SEALED' AND cycle_seal IS NOT NULL
```

**Institutional Meaning:** A sealed cycle is the minimum threshold for evidentiary consideration. It has not necessarily passed adherence or variance checks. It has been ingested, hashed, and stored immutably.

**Example:** The Nabiwi sealed corpus contains 705 cycles.

---

### 2.3 Clean Cycle

**Definition:** A sealed cycle whose absolute variance (`|total_actual_cash − expected_revenue| ÷ expected_revenue`) is ≤ 5 %, and which carries no DISPUTED, MISSING, or uncorroborated INTERRUPTED classification.

**Extraction Criterion:**
```sql
SELECT * FROM cycle
WHERE mill_id = '<NODE_ID>'
  AND status = 'SEALED'
  AND cycle_seal IS NOT NULL
  AND ABS(variance) <= 5.0
  AND status NOT IN ('DISPUTED', 'MISSING')
```

**Institutional Meaning:** A clean cycle is the highest‑purity evidentiary unit the architecture currently produces. It exhibits near‑perfect cash‑to‑energy alignment and carries no evidentiary caveats. The clean‑cycle subset is used for calibration baselines and for transmission to institutional reviewers who require the strictest evidence standard.

**Example:** The Nabiwi clean‑cycle subset contains 26 cycles (as of the May 2026 development database extraction).

---

### 2.4 Adherence‑Qualified Cycle

**Definition:** A sealed cycle with adherence ≥ 90 % (`total_actual_cash ÷ expected_revenue ≥ 0.90`) and zero DISPUTED or MISSING flags in the qualification window. This is the Glass Box certification threshold defined in the Node Qualification Standard v1.0.

**Extraction Criterion:**
```sql
SELECT * FROM cycle
WHERE mill_id = '<NODE_ID>'
  AND status = 'SEALED'
  AND (total_actual_cash / expected_revenue) >= 0.90
  AND status NOT IN ('DISPUTED', 'MISSING')
```

**Institutional Meaning:** Adherence‑qualified cycles demonstrate sustained operator discipline. The Glass Box certification requires a minimum of 10 consecutive adherence‑qualified cycles; the Nabiwi node has produced a 62‑cycle adherence‑qualified streak. This tier is broader than the clean‑cycle tier because it permits variance up to 10 % and does not exclude cycles with uncorroborated INTERRUPTED classifications.

**Example:** The Nabiwi adherence‑qualified streak is 62 consecutive cycles.

---

### 2.5 Replay‑Grade Cycle

**Definition:** A sealed cycle whose `cycle_seal` hash matches the SHA‑256 hash independently recomputed from the canonical input string. A replay‑grade cycle has survived independent verification.

**Extraction Criterion:**
```python
canonical = "|".join([mill_id, str(cycle_start), str(cycle_end), str(kwh), str(cash), str(expected), str(previous_seal or "")])
computed = hashlib.sha256(canonical.encode()).hexdigest()
match = (computed == stored_seal)
```

**Institutional Meaning:** Replay‑grade cycles are the evidentiary foundation of the architecture's central claim — that any auditor can independently verify the seal chain. A cycle that is sealed but not yet independently recomputed is admissible; a cycle that has been independently recomputed and confirmed is replay‑grade. The distinction matters for institutional transmission.

**Example:** All 26 clean cycles in the Goldman Sachs data room are replay‑grade.

---

### 2.6 Calibration‑Grade Subset

**Definition:** A subset of clean cycles used to establish the node‑specific SEC baseline for CUSUM drift detection. Calibration‑grade cycles must be drawn from a period of confirmed grid stability (IAF ≥ 0.40) to avoid confounding the baseline with infrastructure‑induced variance.

**Extraction Criterion:**
```sql
SELECT * FROM cycle
WHERE mill_id = '<NODE_ID>'
  AND status = 'SEALED'
  AND ABS(variance) <= 5.0
  AND IAF >= 0.40
  AND status NOT IN ('DISPUTED', 'MISSING')
```

**Institutional Meaning:** Calibration‑grade cycles are the subset of clean cycles used to establish the performance envelope against which future drift is measured. They are the statistical foundation of the Drift Detection Doctrine. They are not themselves an evidentiary product for external transmission; they are an internal calibration input.

**Example:** The Nabiwi calibration‑grade subset is derived from the clean‑cycle window and filtered for IAF ≥ 0.40.

---

### 2.7 Disputed Cycle

**Definition:** A cycle under active investigation due to evidence conflict — seal mismatch, hash divergence, or unresolved classification dispute. The cycle is sealed but its status is `DISPUTED`.

**Extraction Criterion:**
```sql
SELECT * FROM cycle WHERE mill_id = '<NODE_ID>' AND status = 'DISPUTED'
```

**Institutional Meaning:** A disputed cycle is not admissible as standalone evidence. It requires resolution through the triple‑anchor dispute resolution mechanism defined in GAN‑001: replay against the frozen governance state publicly committed at the time of classification.

---

### 2.8 Missing Cycle

**Definition:** A cycle where remittance was expected but not received within the 48‑hour detection window, or where the operator failed to submit a production report. Status is `MISSING`.

**Extraction Criterion:**
```sql
SELECT * FROM cycle WHERE mill_id = '<NODE_ID>' AND status = 'MISSING'
```

**Institutional Meaning:** A missing cycle is a gap in the evidentiary record. It is preserved immutably — not interpolated or estimated — and carries no evidentiary weight for underwriting purposes. It is retained for pattern analysis and infrastructure reliability modelling.

---

### 2.9 Indeterminate Cycle

**Definition:** A sealed cycle where the Drift Classifier has returned `INDETERMINATE_STATE` — the available physical telemetry is insufficient for deterministic classification into State I (Run) or State II (Grid Collapse). The cycle is sealed with the observed data and flagged for human review.

**Extraction Criterion:** The classifier output, as defined in the Drift Classifier Spec v1.0 and Sensing Failure Modes v1.0.

**Institutional Meaning:** An indeterminate cycle is not a failure. It is a declaration of evidentiary insufficiency. The architecture refuses to classify what it cannot deterministically resolve. The cycle is preserved; the human reviewer determines the next step.

---

## 3. Relationship Between Tiers

```
OPERATIONAL CORPUS (709 records)
│
├── SEALED CYCLES (705 records)
│   │
│   ├── ADHERENCE-QUALIFIED CYCLES (62-cycle streak)
│   │   │
│   │   └── CLEAN CYCLES (26 records, ≤5% variance, no flags)
│   │       │
│   │       └── CALIBRATION-GRADE SUBSET (IAF ≥ 0.40 filtered)
│   │
│   ├── DISPUTED CYCLES
│   ├── MISSING CYCLES
│   └── INDETERMINATE CYCLES
│
└── UNSEALED / INCOMPLETE RECORDS
```

**The 62‑cycle adherence window and the 26‑cycle clean‑cycle subset are different tiers serving different institutional purposes.** The 62‑cycle window answers: *"Was the operator consistently disciplined under unstable infrastructure conditions?"* The 26‑cycle subset answers: *"Which cycles exhibit near‑perfect cash‑to‑energy alignment with no evidentiary caveats?"* Both are useful. Neither replaces the other. The distinction must be explicit in every institutional document that references either number.

---

## 4. Replayability

Every extraction criterion in this Standard is expressed as a query or algorithm that can be executed against the public database by any auditor with access to the raw cycle records. The definitions are deterministic. The tiers are reproducible. The ontology is frozen.

---

## 5. Freeze and Amendment

This Standard is frozen as v1.0. Amendments require a version increment, a dated amendment log entry, and consistency verification against the Node Qualification Standard v1.0, Canonical Terminology v1.2, the Drift Classifier Spec v1.0, and the Architecture Statement v1.2.

---

*GridLedger IP Ltd — Verification Authority*
*ISIC Rev. 4, Section M, Division 74, Class 7490 | May 2026*
