# Nabiwi Cycle Calibration Data
**Extracted from:** `data/raw/nabiwi_node_1/NABIWI NODE INTEL BRIEF.txt`  
**Observation period:** 32 months (July 2023 – March 2026)  
**Account:** MAIZE MILL NABIWI CHITSANZO (Meter 37154463253)  
**Operator:** Tionge Yotamu (+265998265527)

---

## 📊 Q1 2026 Recent Cycle Data (Calibration Window)

| Month | Buckets | Revenue (MWK) | Effective Rate (MWK/bucket) | Effective Rate (MWK/kWh) | Status |
|-------|---------|---------------|----|----|----|
| **2026-01** | 815 | 1,649,000 | 2,023.31 | ⚠️ ANOMALY | Check billing |
| **2026-02** | 1,026 | 1,365,000 | 1,329.04 | ✅ 1,327 | Within band |
| **2026-03** | 761 | 1,027,350 | 1,350.33 | ✅ 1,350 | Within band |

---

## 📈 Rolling 12-Month Effective Rate History (2025–2026)

| Month | Buckets | Revenue (MWK) | Effective Rate/bucket |
|-------|---------|---------------|------|
| 2025-03 | 1,097 | 1,117,850 | 1,018 |
| 2025-04 | 1,020 | 1,037,600 | 1,016 |
| 2025-05 | 1,236 | 1,297,800 | 1,050 |
| 2025-07 | 168 | 210,000 | 1,250 |
| 2025-08 | 927 | 1,158,750 | 1,250 |
| 2025-09 | 774 | 967,500 | 1,250 |
| 2025-10 | 1,130 | 1,412,500 | 1,250 |
| 2025-11 | 1,532 | 1,915,000 | 1,250 |
| 2025-12 | 1,188 | 1,485,000 | 1,250 |
| 2026-01 | 815 | 1,649,000 | **2,023** ⚠️ |
| 2026-02 | 1,026 | 1,365,000 | 1,327 |
| 2026-03 | 761 | 1,027,350 | 1,350 |

---

## 🎯 Effective Rate Band Calibration

### Observed Range (Last 12 Months, Excluding Anomaly)

**Core steady-state range:**
- **Low:** 1,016 MWK/bucket (Apr 2025 – mix-heavy period)
- **High:** 1,350 MWK/bucket (Mar 2026 – current rate)
- **Median:** 1,250 MWK/bucket (Aug 2025 – Nov 2025 stable)

### Recommended Band (GridLedger Phase 1)

| Band | Lower | Upper | Interpretation |
|------|-------|-------|--|
| **Conservative** | 1,100 MWK/bucket | 1,500 MWK/bucket | Accounts for bucket mix variation |
| **Tight** (future) | 1,200 MWK/bucket | 1,350 MWK/bucket | After forensic film (3–5 cycles) |

### Convert to MWK/kWh (at 22.66 kg/kWh verified efficiency)

Nabiwi charges a **milling processing fee**, not commodity wholesale:
- **20L bucket:** ~1 kg (compressed maize flour)
- **Rate:** MWK 1,350/bucket = MWK 1,350/kg
- **At 22.66 kg/kWh:** 22.66 kg × MWK 1,350/kg = **MWK 30,591/kWh** (processing value delivered to grid)

**Alternative logic:** 
- Revenue per kg processed: MWK 67.50 (1,350 ÷ 20L bucket ÷ ~1kg)
- Per kWh basis: 22.66 kg/kWh × MWK 67.50/kg = **MWK 1,530/kWh** (grid value)

---

## 🔍 Forensic Notes from Intel Brief

### Recent Daily Production Pattern (March 2026)

```
Date    Open  Close  Buckets  Revenue/day  Rate/bucket  Notes
------  ----  -----  -------  -----------  -----------  ----
2026-03-01  60  0      60      81,000      1,350       NORMAL
2026-03-02  60  0      60      81,000      1,350       Ma Units Atha (tokens exhausted)
2026-03-03  60  0      60      81,000      1,350       Ma Units Atha
2026-03-04  60  0      60      81,000      1,350       Steady-state
2026-03-06  60  0      60      81,000      1,350       Deduction: MWK 75,000 (sieve parts)
2026-03-08  60  0      60      81,000      1,350       Duplicate SMS (normal)
2026-03-10  60  0      60      81,000      1,350       Steady
2026-03-12  60  20     40      54,000      1,350       Feedstock shortage ("Magets Kulibe")
2026-03-14  60  19     41      55,350      1,350       Recovery
```

**Reading:**
- Operator now reliably processes **60 20L buckets/day** at **MWK 81,000/day** (MWK 1,350/bucket)
- No mix variation visible (all 60-bucket days = large customer segment or standardized pricing)
- Tokens exhaust almost daily → daily repurchase cycle → tight cash flow

### Energy Consumption Pattern

**Recent token purchases (2024–2026):**
- Standard token: ~64.8 kWh for MWK 16,500 = **MWK 254.63/kWh** (electricity cost)
- 2025+ tokens: 59.9 kWh (standard GridLedger allocation unit)

**Operator revenue vs electricity cost:**
- Processing fee: MWK 81,000/day @ 60 buckets
- Electricity cost: ~MWK 16,500/day @ 64.8 kWh/day
- **Net margin per day:** ~MWK 64,500 (79% gross)

---

## 🚨 January 2026 Anomaly (2,023 MWK/bucket)

**Data:** 815 buckets → MWK 1,649,000 revenue

**Analysis:**
- This implies MWK 2,023/bucket (not MWK 1,350)
- OR: Data double-counted or accumulated remittances error

**Owner SMS (22 Jan 2026):**
> "Ndiye kuti rate yakweraso ESCOM yakwezaso. Kuyambila lero rate 2000"
> = "ESCOM has raised rates. Starting today, rate 2000"

**Interpretation:** Owner announced a price hike to MWK 2,000/bucket but actual reported rate settled at MWK 1,350. Possible explanations:
- Owner ordered rate increase → operator negotiated down
- Owner's SMS was aspirational (wanted 2,000) → Nabiwi market competition kept it at 1,350
- Data entry error (operator recorded in batches, inflated January total)

**Recommendation:** Flag this for next cycle observation. If Jan 2026 was a data artifact, ignore. If genuine pricing variance, it suggests sensitive market pricing.

---

## 📋 Historical Rate Evolution (Full Record)

The rate has tripled over 32 months, tracking ESCOM tariff increases:

```
Jul 2023:  MWK 450/bucket
Aug 2023:  MWK 500/bucket
Jan 2024:  MWK 850/bucket  (+70% after ESCOM tariff hike Oct 2023)
Feb 2025:  MWK 900/bucket
Jul 2025:  MWK 1,250/bucket  (MAJOR step-up)
Feb 2026:  MWK 1,327/bucket  (slight increase)
Mar 2026:  MWK 1,350/bucket  (current)
```

**Most recent stable period:** Aug 2025 – Mar 2026 (8 months), rates 1,250–1,350 MWK/bucket.

---

## 🧪 Recommended Next Steps for Calibration

### Phase 1 (This Week)
- Deploy effective_rate tracking to GridLedger
- Observe 1 cycle (1–2 days) at Nabiwi
- Compare reported `effective_rate_per_kwh` against band (1,100–1,500)
- Expected: ~1,350 MWK/bucket ✅

### Phase 2 (1–2 Weeks)
- Collect 3–5 cycles of effective_rate data
- Conduct forensic film (manual observation 1 cycle):
  - Count actual 20L vs 5L buckets served
  - Verify cash handling matches reported revenue
  - Check electricity token pattern
  
### Phase 3 (After Film)
- Adjust band per mill based on observed operator behaviour
- Add anomaly detection rule: if effective_rate jumps 15%+ → flag for review

---

## 💡 Key Forensic Insights (From Intel Brief)

### Energy-Production Gap

**Expected production (from kWh):**
- 31,329 kWh × 22.66 kg/kWh = 709,915 kg output

**Reported production (from SMS):**
- 25,451 buckets × 20L × 1 kg/L ≈ 509,020 kg

**Gap:** ~200,895 kg = ~10,045 buckets = ~MWK 12–13 million (at 1,250–1,350/bucket)

**Brief's interpretation:**
- Missing SMS reports (operator silent days)
- Maintenance/downtime periods not captured
- ESCOM outage periods genuinely offline

**GridLedger addition:** Meter log correlation will distinguish genuine down-time from unrecorded production leakage.

### Mobile Money Verification

Primary receiver: **Victor Mumba (agent 1123563)**
- Recurring deposits: ~MWK 55,000–75,000/month consistent with grinder output
- Payment pattern: Monthly lump sums (not daily) → operator accumulates, remits monthly

### Maintenance & Wear Pattern

**Feb 2025 critical event:**
> "Roller mill grinding teeth completely exhausted. Hammers worn on all three. Mill switched to hammer mill."

**Cost:** Major repair event (~MWK 250,000 in May 2025 for freza/freezer + push button)

**Implication for rate calibration:**
- Post-maintenance cycles (Feb 2025 onwards) show stable rate increase to 1,250–1,350
- Pre-maintenance (Jan 2025): rate was ~1,000–1,050
- Suggests rate increase was operational recovery (new equipment enabled efficiency gains, not inflation alone)

---

## 📌 Summary for GridLedger Operations

| Field | Value | Source |
|-------|-------|--------|
| **Effective rate band (current)** | 1,100–1,500 MWK/bucket | Observed 12-month data |
| **Expected rate (Mar 2026)** | 1,350 MWK/bucket | Intel brief, recent daily SMS |
| **Anomaly threshold** | > 1,500 or < 1,000 MWK/bucket | Conservative buffer |
| **Energy efficiency** | 22.66 kg/kWh | Field-verified |
| **Daily processing capacity** | ~60 buckets = ~81,000 MWK revenue | Recent SMS patterns |
| **Electricity cost/day** | ~MWK 16,500 @ 64.8 kWh | Recent token history |
| **Gross margin** | ~79% | Revenue – electricity cost |
| **Meter number** | 37154463253 | For ESCOM correlation |

---

## 🎬 Ready for Forensic Film?

The intel brief provides the **macro-level envelope** (accounting truth):
- 32 months of production history ✅
- Rate evolution ✅
- Energy consumption ✅
- Revenue flow ✅

**Now GridLedger adds the micro-level cycle truth** (physics + behaviour):
- Day-by-day allocation ✅
- kWh-to-bucket conversion ✅
- Time-weighted exposure ✅
- Effective rate per cycle ✅ (NEW)

**Forensic film (manual 1–2 cycle observation)** closes the loop:
- Actual bucket mix (20L vs 5L customer ratio)
- Real-time meter reading verification
- Cash handling observation
- Operator strategy (throughput vs margin optimization)

With that ground truth, the band tightens and anomaly detection becomes decisive.

---

**Document Generated:** April 14, 2026  
**Extracted From:** NABIWI NODE INTEL BRIEF (32-month SMS forensic record)  
**Next Review:** After 3–5 cycles of GridLedger observation + 1 forensic film session
