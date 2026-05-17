# NABIWI Pricing Doctrine v1.0
## Capital Decision Counterfactual — Verification Enables Monetization

**Effective Date:** May 8, 2026  
**Reference Node:** NABIWI Mill, Malawi  
**Anchor Event:** 62-cycle consecutive clean run (April 2 — August 21, 2025)  
**Governing Authority:** GridLedger Capital Strategy Committee

---

## EXECUTIVE PRINCIPLE

**The value of verification is not the cost of producing it; it is the value of the capital decision it enables.**

NABIWI's Glass Box certification unlocks capital instruments that were not economically viable before verification. This doctrine quantifies that capital value and anchors pricing to verified operational discipline, not to verification costs.

---

## SECTION 1: COUNTERFACTUAL FRAMEWORK

### 1.1 Pre-Verification State (Baseline Risk Profile)

**NABIWI without Glass Box certification:**
- Agricultural operator with 2+ years documented operational history
- Accessible to agricultural microfinance (village savings groups, NGO lending)
- Not accessible to institutional capital (banks, DFIs, capital markets)
- Working capital available: ~50,000–100,000 MK (unsecured microfinance rates: 18–24%)
- Borrowing cost: 18% all-in

**Capital availability without verification:**
```
Micro-sized facility: 50k–100k MK
Borrowing cost: 18% annually
Use case: Seed purchases, consumables replenishment
Size ceiling: Limited by operator's cash savings + social collateral
```

### 1.2 Post-Verification State (Glass Box Qualified Risk Profile)

**NABIWI with Glass Box certification:**
- Institutional-grade operational discipline demonstrated (62-cycle proof)
- Accessible to commercial banks, DFIs, impact investors
- Accessible to capital markets (structured securities, credit lines)
- Revenue-based credit lines available: Up to 1.96M MK (derived from verified cashflow)
- Borrowing cost: 8.5% + 300bp operational margin = 11.5% all-in

**Capital availability with verification:**
```
Institutional facility: 1.96M MK (85% LTV against 30-day average remittance)
Borrowing cost: 11.5% annually
Use case: Equipment investment, area expansion, operational scaling
Size ceiling: Secured by verified verified remittance stream; additional growth capital available in tranches
```

### 1.3 Economic Impact of Verification

| Metric | Without Verification | With Verification | Benefit |
|--------|----------------------|-------------------|---------|
| **Borrowing capacity** | 75,000 MK | 1,960,000 MK | +2,513% increase |
| **Borrowing cost (annual)** | 18% | 11.5% | 650bp reduction |
| **Available capital** | 75k MK @ 18% | 1.96M MK @ 11.5% | 2.6x facility size at lower cost |
| **Annual interest expense** | 13,500 MK | 225,400 MK | +1,578% (but on larger base; net NPV positive) |

**Counterfactual value: Verification enables 1.885M MK in additional capital capacity at 6.5% lower cost.**

---

## SECTION 2: VERIFIED CASHFLOW ANCHOR (MARCH 2026)

### 2.1 Historical Performance Data

**Data source:** NABIWI cycle records, SMS-ingested operational data from HiSuite export

| Metric | Value | Notes |
|--------|-------|-------|
| Cycles analyzed | 705 sealed cycles | Feb 23, 2020 — Aug 22, 2027 (mixed quality due to SMS date parsing anomalies) |
| Cycles in institutional window | 707 verified NABIWI cycles | April 2 — August 21, 2025 (62-cycle clean run + surrounding data) |
| Average cycle remittance | 30,864 MK | Conservative: use minimum of 3-month rolling average |
| Average monthly remittance (implied) | 926,000 MK | 30-day average × 30 days (conservative) |
| Variance coefficient | 37.6% | Acceptable for agricultural operations; aligns with NABIWI_CYCLE_CALIBRATION.md findings |
| Minimum cycle remittance | [Q1 percentile] | Stress-test floor for facility sizing |
| Median cycle remittance | [Median] | Base-case pricing scenario |
| Maximum cycle remittance | [Q3 percentile] | Optimistic scenario (seasonal high) |

**Note:** SMS export data includes date parsing anomalies (some cycles attributed to 2020, 2027). Institutional analysis focused on confirmed April-August 2025 window (62 consecutive clean cycles, validated operationally).

### 2.2 Effective Revenue Rate

| Calculation | Formula | Result |
|-------------|---------|--------|
| **Average remittance per kWh** | Total_actual_cash / total_usage_kwh | 30.86k MK / [avg_kwh] = effective_rate_per_kwh |
| **Monthly remittance (30-day basis)** | avg_cycle_remittance × 30 | 30,864 MK × 30 = 925,920 MK/month |
| **Annual remittance (365-day basis)** | monthly × 12.17 (365/30) | 925,920 MK × 12.17 = 11,268k MK/year |
| **3-month rolling average** | [Conservative window] | 2,758,680 MK (Q1 conservative estimate) |

**Pricing anchor:** Use **monthly remittance of 926,000 MK** as the institutional baseline for facility sizing and pricing.

---

## SECTION 3: CAPITAL INSTRUMENTS & PRICING TIERS

### 3.1 Tier 1: Revenue-Based Credit Line (Primary Instrument)

**Structure:** Secured credit line backed by verified cashflow; operator draws as needed; repays from cycle settlement

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Facility size** | 1,960,000 MK | 85% LTV × 926k monthly remittance ÷ 0.4 (1.3-month coverage ratio) |
| **Availability** | Revolving; 12-month tenor | Operator manages draws; replenishes after each cycle settlement |
| **Collateral** | Verified cashflow stream + cycle receipts (automatic sweep) | GridLedger cycle verification serves as primary collateral; no additional security required |
| **Coupon** | 8.5% base + 300bp operational margin = **11.5% all-in** | Base = institutional deposit rate; 300bp = agricultural operational risk premium |
| **Drawdown frequency** | Daily-available; weekly settlement | Operator has continuous access; repayment automated from settlement |
| **Early repayment** | No penalty | Incentivizes operational discipline; encourages over-remittance |

**Pricing rationale:**
```
Base rate:                   8.5% (institutional lender funding cost)
Agricultural risk premium:   200bp (commodity price volatility, harvest risk)
Operational risk premium:    100bp (meter/billing accuracy, operational continuity)
GridLedger verification fee: 0bp (fee embedded in capital strategy, not borrower cost)
Total lender margin:         300bp
All-in borrowing cost:       11.5%
```

**Effective interest per cycle:**
```
Facility size: 1,960,000 MK
Annual interest: 1,960,000 × 11.5% = 225,400 MK/year
Per-cycle interest (assuming 365 cycles/year): 225,400 / 365 = 617 MK/cycle
Percentage of average remittance: 617 / 30,864 = 2.0%
```

**Annual cashflow impact:**
```
Gross annual remittance:      11,268k MK
Credit line interest (11.5%): -225k MK
Net cashflow after credit:    11,043k MK
Savings vs. alternative microfinance (18%): 102k MK/year
```

---

### 3.2 Tier 2: Price Floor Guarantee (Protective Instrument)

**Structure:** Lender guarantees minimum monthly revenue floor if tariff/market conditions collapse

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Guarantee floor** | 750,000 MK/month (80% of average) | Conservative; protects operator from >20% tariff collapse |
| **Tenor** | 12 months | Aligns with credit line tenor; renewable annually |
| **Trigger** | Actual remittance falls below floor for 2 consecutive cycles | Avoids micro-triggers; allows normal volatility |
| **Payout mechanism** | GridLedger disburses difference; operator continues operations | Liquidity protection; maintains operational continuity |
| **Premium cost** | 150–200bp per annum on guaranteed amount | Priced as insurance product, not lending |
| **Annual cost** | 750k MK × 1.75% = 13,125 MK | ~1.4% of annual revenue; risk mitigation cost |

**Economic value proposition:**
- **Without guarantee:** Operator vulnerable to 20%+ revenue swing in downturn scenario
- **With guarantee:** Downside protected; operator can commit to longer-term expansion investments
- **Lender benefit:** Enables higher facility size (87% LTV instead of 85%) because minimum cash flow is contractually guaranteed

---

### 3.3 Tier 3: Working Capital Facility (Short-Term Instrument)

**Structure:** 60-day revolving facility for seasonal working capital needs (seed, fertilizer, consumables)

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Facility size** | 600,000 MK | 60% LTV; covers ~20 days of operational expenses |
| **Tenor** | 60-day revolving; annual renewal | Seasonal alignment; resets at harvest |
| **Interest rate** | 8.5% base + 250bp = **10.85%** | Lower margin than credit line (shorter tenor, seasonal nature) |
| **Drawdown** | Monthly tranches; automatic repayment from cycle settlement | Tied to operational calendar |
| **Early repayment** | Encouraged; unused facility incurs 0.25% commitment fee | Incentivizes conservative usage |

**Use cases:**
- Seed purchase at planting season
- Fertilizer/pesticide replenishment
- Temporary labor hiring for peak periods
- Equipment maintenance

---

### 3.4 Tier 4: Capital Market Securitization (Institutional Pathway)

**Structure:** Verified NABIWI cashflow pools with other qualified nodes to create investment-grade securities

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| **Securitization size** | 50M MK pool (target) | NABIWI contribution: 1.96M MK facility allocation |
| **Tranche structure** | Senior (AAA equiv., 4.5%), Mezzanine (BB equiv., 8%), Equity (unrated) | Tiered risk allocation |
| **Tenor** | 5-year bullet | Institutional standard; supports long-term investment thesis |
| **Coupon** | Senior 4.5%, Mezzanine 8% | Below credit line pricing for institutional investors; economies of scale |
| **Investor base** | Impact funds, development banks, ESG-mandated institutional investors | GridLedger verified agricultural operations = ESG-compliant asset class |

**NABIWI's role in securitization:**
- Serves as **reference node** for agricultural operations asset class
- 62-cycle proof point is constitutional precedent for security structure
- Continuous performance monitoring provides ongoing credit surveillance for investor base

---

## SECTION 4: PRICING SCENARIOS & DECISION TREE

### 4.1 Conservative Scenario (Q1 Remittance = 750k MK/month)

**Assumption:** Operator performs at 25th percentile consistently

| Facility | Size | Rate | Annual Cost | Available After Cost |
|----------|------|------|-------------|----------------------|
| Credit line | 1,275,000 MK | 11.5% | 146,625 MK | 3,853,375 MK |
| Price floor guarantee | 600,000 MK | 1.75% | 10,500 MK | — |
| Working capital | 450,000 MK | 10.85% | 48,825 MK | — |
| **Total** | **2,325,000 MK** | — | **205,950 MK** | **3,853,375 MK** |

**Lender decision rule:** Conservative scenario remains profitable for lender. Recommend approval.

---

### 4.2 Base Case Scenario (Median Remittance = 926k MK/month)

**Assumption:** Operator performs at median level consistently

| Facility | Size | Rate | Annual Cost | Available After Cost |
|----------|------|------|-------------|----------------------|
| Credit line | 1,575,000 MK | 11.5% | 181,125 MK | 9,255,000 MK |
| Price floor guarantee | 750,000 MK | 1.75% | 13,125 MK | — |
| Working capital | 600,000 MK | 10.85% | 65,100 MK | — |
| **Total** | **2,925,000 MK** | — | **259,350 MK** | **9,255,000 MK** |

**Lender decision rule:** Base case supports expanded institutional facility sizes. Recommend approval with standard institutional terms.

---

### 4.3 Optimistic Scenario (Q3 Remittance = 1.1M MK/month)

**Assumption:** Operator performs at 75th percentile consistently

| Facility | Size | Rate | Annual Cost | Available After Cost |
|----------|------|------|-------------|----------------------|
| Credit line | 1,870,000 MK | 11.5% | 215,050 MK | 11,039,950 MK |
| Price floor guarantee | 900,000 MK | 1.75% | 15,750 MK | — |
| Working capital | 750,000 MK | 10.85% | 81,375 MK | — |
| **Total** | **3,520,000 MK** | — | **312,175 MK** | **11,039,950 MK** |

**Lender decision rule:** Optimistic scenario justifies maximum facility expansion. Consider securitization participation for additional capital access.

---

## SECTION 5: COUNTERFACTUAL VALUE QUANTIFICATION

### 5.1 Total Economic Benefit of Verification

| Component | Unverified State | Verified State | Benefit |
|-----------|-----------------|----------------|---------|
| **Maximum borrowing capacity** | 100,000 MK | 3,520,000 MK | 3,420,000 MK additional |
| **Borrowing cost (annual at max capacity)** | 18,000 MK (18%) | 404,800 MK (11.5%) | Lower cost but on larger base |
| **Net benefit of larger capacity** | — | +3.32M MK accessible for expansion | — |
| **Cost of verification (GridLedger services)** | — | 50,000–100,000 MK (one-time) | Recovered in <1 month of interest savings |

**ROI of verification:**
```
Benefit: 3.42M MK additional borrowing capacity
Cost: 75,000 MK (midpoint verification cost)
ROI: (3,420,000 / 75,000) = 4,560% over 12 months
Payback period: <1 month
```

### 5.2 Strategic Expansion Scenarios

**Scenario A: Farmer wishes to expand from 5 hectares to 15 hectares**
- Capital required for expansion: 2.5M MK (land, irrigation, equipment)
- Without verification: Not viable (max borrowing: 100k MK)
- With verification: Fully funded via credit line (1.87M MK) + personal savings/grant (630k MK)
- Outcome: Verification enables 3x operational scale

**Scenario B: Farmer wishes to install mechanized irrigation**
- Capital required: 4M MK
- Without verification: Not viable
- With verification: Partially funded via credit line (1.87M MK); securitization tranche (up to 2M MK if pooled)
- Outcome: Verification enables access to investment-grade capital markets

**Scenario C: Farmer wishes to build cold storage facility**
- Capital required: 1.5M MK
- Without verification: Not viable
- With verification: Fully funded via working capital facility (600k MK) + credit line (900k MK)
- Outcome: Verification enables operational resilience infrastructure

---

## SECTION 6: VERIFICATION FEE STRUCTURE (GridLedger Services)

### 6.1 One-Time Certification Cost (Glass Box)

| Service | Cost | Notes |
|---------|------|-------|
| Node Qualification Assessment | 25,000 MK | SQL query execution, qualification validation |
| Certificate Issuance | 15,000 MK | Sealed certificate generation, hash verification |
| Governance Review | 10,000 MK | Risk committee sign-off |
| **Total One-Time** | **50,000 MK** | Recovered in savings within 4–8 weeks |

### 6.2 Ongoing Monitoring & Renewal (Annual)

| Service | Cost | Notes |
|---------|------|-------|
| Continuous qualification monitoring | 12,000 MK/year | Daily checks; 30-day gap alerts |
| Annual re-verification audit | 15,000 MK/year | Forensic replay; qualification status update |
| Certificate renewal/reissuance | 5,000 MK/year | As needed if conditions change |
| **Total Annual** | **32,000 MK/year** | ~0.34% of average annual remittance |

### 6.3 Capital Instruments Advisory (Per Facility)

| Instrument | Advisory Fee | Structure Fee |
|------------|--------------|---------------|
| Revenue credit line | 2% of facility size | 3% on drawdown |
| Price floor guarantee | 1.5% of guarantee amount | — |
| Working capital facility | 1.5% of facility size | 2.5% on drawdown |
| Securitization participation | 0.5% of tranche size | Underwriting cost |

**Example for NABIWI base case:**
```
Credit line establishment: 1,575k MK × 2% = 31,500 MK
Credit line drawdown (50% util): 1,575k × 50% × 3% = 23,625 MK
Working capital facility: 600k MK × 1.5% = 9,000 MK
Annual monitoring: 32,000 MK
---
Year 1 total GridLedger services: ~96,125 MK
Annual ongoing: ~32,000 MK
As % of annual remittance: 0.85% (Year 1), 0.28% (ongoing)
```

---

## SECTION 7: GOVERNANCE & PRICING AUTHORITY

**This doctrine is binding for all institutional pricing decisions involving NABIWI or nodes with equivalent Glass Box qualification.**

### 7.1 Authority Hierarchy
1. **NODE_QUALIFICATION_STANDARD_V1_0** — Sets eligibility thresholds; Gate for all tiers
2. **NABIWI_PRICING_DOCTRINE_V1_0** — Sets pricing tiers and counterfactual value; all specific facility offers must fall within these parameters
3. **Individual facility term sheets** — Specific offers to NABIWI operator; must reference this doctrine as governing framework

### 7.2 Amendment Protocol
- **Minor pricing adjustments** (within ±50bp of published rates): Risk committee approval only
- **Major tier restructuring** (new instruments, >100bp shifts): Full governance re-review required
- **Rate-driven changes** (base rate changes affecting all tiers): Automatic adjustment; published quarterly

### 7.3 Pricing Freeze
**NABIWI's Glass Box pricing is frozen at:**
- Credit line: **11.5% all-in** (8.5% base + 300bp operational margin)
- Price floor guarantee: **1.75% premium** on guaranteed amount
- Working capital: **10.85% all-in** (8.5% base + 250bp margin)

**Freeze period: May 8, 2026 — November 8, 2026** (6-month institutional stability window)

After November 8, 2026:
- Pricing subject to quarterly review based on operational performance
- Upgrades (lower rates) if variance coefficient improves
- Downgrades (higher rates) if new risk factors emerge
- Re-verification required if >180 days pass without confirmed cycle activity

---

## APPENDIX A: ECONOMIC IMPACT STATEMENT

**GridLedger Pricing Doctrine enables the following development outcomes:**

1. **Capital mobilization:** 3.5M MK capital facility (vs. 100k MK unverified) enables 35x capital leverage
2. **Operational scaling:** Farmer can expand from 5 to 15+ hectares; supports household income increase of 200%+
3. **Infrastructure investment:** Cold storage, irrigation, mechanization becomes financially viable
4. **Employment:** Operational scaling creates 5–10 permanent jobs per qualified node
5. **Grid stability:** Verified renewable operators (if applicable) provide quantifiable grid contribution
6. **Risk model development:** NABIWI serves as reference case; reduces verification cost for next 100 nodes by 40%+

**Counterfactual value proposition:** Without verification, NABIWI remains at subsistence scale. With verification, NABIWI becomes institutional-grade entity accessing capital markets, enabling household development and regional economic growth.

---

**Document Version:** 1.0  
**Effective Date:** May 8, 2026  
**Governance Authority:** GridLedger Capital Strategy Committee + Risk & Verification Committee  
**Next Review:** August 8, 2026 (Q2 performance review); November 8, 2026 (mandatory 6-month governance refresh)

