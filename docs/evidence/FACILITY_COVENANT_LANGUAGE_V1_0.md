# FACILITY COVENANT LANGUAGE — GRID-VERIFIED CYCLE FACILITY (GVCF)

**Purpose:** To illustrate how a regulated lender's credit agreement can reference GridLedger's verification outputs as mechanical drawdown conditions.

**Constitutional Boundary:** GridLedger IP Ltd is not a party to the facility agreement. It provides independently verifiable cycle evidence. The lender makes all credit decisions.

---

## Example Drawdown Conditions

### 1. Adherence Threshold

The Operator must maintain a trailing 10-cycle adherence rate of ≥ 90%. Adherence is calculated as:

$$\text{Adherence} = \frac{\sum \text{total\_actual\_cash}}{\sum \text{total\_expected\_revenue}} \times 100\%$$

across the 10 most recent sealed cycles published in the Trust Anchor repository.

### 2. Infrastructure Availability Gate

The Infrastructure Availability Factor (IAF) for the node must be ≥ 0.40 at the time of drawdown. If IAF < 0.40, the Capital Action Object will carry an `INDETERMINATE` flag, and the Lender shall exercise its discretion before advancing.

IAF is computed as:

$$\text{IAF} = \frac{\text{sum of non-interrupted cycles in trailing 30-day window}}{\text{total expected cycles in 30-day window}}$$

### 3. Seal Validity

Each drawdown must reference a valid Cycle Seal produced by the GridLedger GL-1 Protocol. The Seal is valid if it matches the independently recomputed SHA-256 hash from the raw inputs published in the Trust Anchor repository:

```
canonical_input_string = "{mill_id}|{cycle_start}|{cycle_end}|{usage_kwh}|{actual_cash}|{expected_revenue}|"
computed_seal = SHA256(canonical_input_string)
valid = (computed_seal == seal_hash_in_csv)
```

### 4. Revenue Shortfall Event

If `total_actual_cash < total_expected_revenue × (1 − tolerance_band)` — where `tolerance_band = 5%` — the Lender may suspend further drawdowns until the Operator completes a qualifying clean cycle.

### 5. No Cross-Cycle Compounding

Exposure is bounded per cycle. The maximum advance per cycle is capped at 60% of expected revenue for the node's calibrated baseline. The Lender shall not advance a second cycle at the same node until the prior cycle is sealed and the Capital Action Object clears.

---

## Verification Process

The Lender may independently verify any Seal by:

1. **Obtaining the CSV** — Request `GLASSBOX_62_CLEAN_CYCLES.csv` from the Trust Anchor repository
2. **Copying the canonical input string** — Locate the relevant cycle row and copy the `canonical_input_string` column
3. **Computing the SHA-256 hash** — Use Python, OpenSSL, or any standard SHA-256 tool
4. **Comparing against the CSV seal** — Verify the computed hash matches the `seal_hash` column

**No access to GridLedger's operational infrastructure is required.**

Example verification in Python:

```python
import hashlib
canonical = "NABIWI|2020-02-23 00:00:00|2020-02-24 00:00:00|41.0|40400.0|41385.0|"
computed_seal = hashlib.sha256(canonical.encode()).hexdigest()
csv_seal = "12ff046659f6253c90483e786ed1ba17d442f60b8f474f35f2863631a91fa00c"
print(f"Match: {computed_seal == csv_seal}")
```

---

## Risk Constraints

1. **Single-node exposure cap:** No facility shall exceed 25% of the Operator's total enterprise revenue
2. **Cycle-level haircut:** Advances shall not exceed 60% LTV per cycle
3. **Adhesion barrier:** Cycles must be sealed within 48 hours of period-end; unseal cycles forfeit advance eligibility
4. **Escalation frequency:** If three consecutive cycles show variance > 2%, the Operator enters a review period before further advances

---

## Disclaimer

GridLedger IP Ltd is not a lender, guarantor, or credit advisor. GridLedger provides independently verifiable cycle evidence only. The Lender retains full responsibility for all credit decisions, underwriting standards, and enforcement actions. This language is illustrative and does not constitute legal advice.

---

**Version:** 1.0  
**Date:** May 24, 2026  
**Status:** Institutional Clean
