"""
GridLedger Configuration Constants

Per-cycle token allocation control system configuration.
All tolerances, timeouts, and penalty functions defined here.
"""

# ============================================================================
# PER-CYCLE TOKEN ALLOCATION CONFIG
# ============================================================================

TOLERANCE_PERCENT = 5.0               # ±5% variance allowed on cash receipts
DISPUTED_ADHERENCE_PENALTY = 0.0      # 0% advance rate for disputed cycles
MISSING_CYCLE_TIMEOUT_HOURS = 48      # Mark cycles MISSING after 48h without receipt
CONSERVATIVE_LAG_HOURS = 72.0         # Fallback lag for disputed/missing cycles

# Base advance rate (starting point before penalties)
BASE_ADVANCE_RATE = 0.5               # 50% default, adjusted by trust and adherence

# ============================================================================
# LATENCY PENALTY STEP FUNCTION
# ============================================================================

# Step function: (hours_threshold, penalty_multiplier)
# Upper bound is exclusive; matches first threshold where lag_hours < threshold
# Last entry has None threshold (matches everything >= previous threshold)
LATENCY_BOUNDARIES = [
    (24,  1.00),   # lag < 24h  → no penalty
    (48,  0.95),   # 24 ≤ lag < 48h → 5% penalty
    (72,  0.90),   # 48 ≤ lag < 72h → 10% penalty
    (None, 0.85),  # lag ≥ 72h → 15% penalty
]

# ============================================================================
# OPERATIONAL INTENT (Design Rationale)
# ============================================================================

"""
WHY THIS DESIGN (Operational Intent)

1. **Quadratic penalty on adherence (adherence²), not linear**
   - Linear: 0.9 adherence → 0.9× multiplier (10% penalty)
   - Quadratic: 0.9 adherence → 0.81× multiplier (19% penalty)
   → Non-linearity drives behavior change faster
   → Operators at 90% adherence faced only 10% rate cut (linear) → insufficient motivation
   → Operators at 90% adherence now face 19% rate cut (quadratic) → forces urgent improvement
   → Edge case: operators at 55% efficiency now see 70% capital cut → effectively removed from starvation zone

2. **48-hour missing cycle timeout, not 24 or 72**
   - 24h too aggressive: regional cash collection (MTN, Airtel) legitimately takes 24–36h
   - 72h too lenient: allows operator to hide cycles, claim "cash in transit"
   - 48h sweet spot: acknowledges real logistics, prevents indefinite ambiguity
   → Encourages daily remittance behavior without false positives on slow networks

3. **±5% variance tolerance, not ±2% or ±10%**
   - 2% too tight: meter drift, rounding, exchange rate fluctuations trigger false disputes
   - 10% too loose: 10% variance on 80k MK is 8k MK — could hide significant cash diversion
   - 5% range: ~4k MK on typical cycle, catches intentional underreporting, excuses honest measurement error
   → Conservative: when in doubt, close cycle, but audit resolved disputes

4. **Latency penalty step function, not linear decay**
   - Linear: complex time-dependent math, unexpected marginal rates
   - Step function: <24h(1.0), 24–48(0.95), 48–72(0.90), ≥72(0.85)
   → Clear, auditable, no surprise marginal rates
   → Operators understand: "24h = no penalty; 72h = 15% cut"
   → Easy to justify operationally, not a black box formula

These aren't arbitrary. They came from modeling edge cases:
- Starvation zone dynamics (why quadratic helps)
- Network latency in regional payment systems (why 48h not 24h)
- Currency volatility and meter measurement error (why ±5%)
- Operator behavior response times (why step function)
"""
