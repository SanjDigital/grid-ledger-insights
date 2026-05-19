# BASELINE REPLAY ARTIFACT — REPLAY_001

**Published:** May 2026
**Repository:** [github.com/SanjDigital/grid-ledger-insights](https://github.com/SanjDigital/grid-ledger-insights)

---

## 1. Purpose

This artifact demonstrates that any auditor can independently recompute a GridLedger cycle seal using publicly available inputs. The seal is a SHA‑256 cryptographic hash generated from the immutable fields of a verified production cycle. The recomputation is deterministic—identical inputs produce identical outputs. No access to GridLedger's operational infrastructure is required.

---

## 2. Cycle Record

| Field | Value |
|-------|-------|
| **Cycle ID** | 1 |
| **Node** | NABIWI (M1 Corridor, Malawi) |
| **Cycle Start** | 2026‑03‑14 00:00:00 |
| **Cycle End** | 2026‑03‑15 00:00:00 |
| **Energy Consumed** | 19.0 kWh |
| **Cash Remitted** | MWK 25,650.00 |
| **Expected Revenue** | MWK 25,650.00 |
| **Variance** | 0.0% |
| **Previous Seal** | None (this is a root cycle) |
| **Status** | SEALED |

---

## 3. Seal Computation

### Algorithm

SHA‑256

### Input Fields (Concatenated with `|` Delimiter)

1. `mill_id`
2. `cycle_start`
3. `cycle_end`
4. `total_usage_kwh`
5. `total_actual_cash`
6. `expected_revenue`
7. `previous_seal`

### Canonical Input String

NABIWI|2026-03-14 00:00:00|2026-03-15 00:00:00|19.0|25650.0|25650.0|

### Computed Seal

c7724cb1756f5e9d7bb160c77fe34aaf3d62e5bdeba2877231afedc7006bfffc


### Verification Status

**✓ MATCH** — The seal stored in the operational database matches the independently computed seal. This cycle record is cryptographically intact.

---
---

## 4. How to Independently Verify

### Prerequisites
- Python 3.9+
- No API keys, no backend access, no permissions required

### Replay Command

```bash
python -c "
import hashlib
seal = hashlib.sha256(
    'NABIWI|2026-03-14 00:00:00|2026-03-15 00:00:00|19.0|25650.0|25650.0|'.encode()
).hexdigest()
print(f'Computed seal: {seal}')
print(f'Published seal: c7724cb1756f5e9d7bb160c77fe34aaf3d62e5bdeba2877231afedc7006bfffc')
print(f'Match: {seal == \"c7724cb1756f5e9d7bb160c77fe34aaf3d62e5bdeba2877231afedc7006bfffc\"}')
"

Expected Output

Computed seal: c7724cb1756f5e9d7bb160c77fe34aaf3d62e5bdeba2877231afedc7006bfffc
Published seal: c7724cb1756f5e9d7bb160c77fe34aaf3d62e5bdeba2877231afedc7006bfffc
Match: True

5. Database Provenance
The seal was computed against the local SQLite operational database (gridledger.db) as of May 2026. The cycle record was ingested from SMS production reports. ESCOM token records and Airtel Money receipts for this cycle exist independently and will be cross‑referenced as those external data sources are integrated.

6. Constitutional Guarantee
"Any auditor can fetch the raw events and the open‑source protocol from the public repository and independently recompute every seal."

This artifact demonstrates that the guarantee holds for Cycle 1. The seal is the moat. The repository is the proof. The governance version is the constitutional memory.  

GridLedger IP Ltd — Verification Authority ISIC Rev. 4, Section M, Division 74, Class 7490 | May 2026