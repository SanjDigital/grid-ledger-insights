# Pre-Production Finding: Advance Rate & Gate Safety

## Diagnostic Results (April 1, 2026)

### What We Verified
- ✅ `evaluate_mill_capital("NABIWI", trust_score=85.0)` returns **0.425** (not 0.0)
  - This is 42.5% advance rate, well above the zero gate threshold
  - Formula works: 0.5 × 0.85 × (adherence factor) × (latency penalty) = 0.425
  
### Critical Question: Does Gate Block New Mills?

**Test 1 Failure Analysis**:
- Test created `test_mill_e2e` and called `TrustScorecardGenerator` 
- `evaluate_mill_capital()` returned advance_rate=0.0%
- This caused assertion failure: "First cycle should have positive advance rate"

**Root Cause Unknown**: Could be either:
1. **TrustScorecardGenerator returns 0 for new mill** → 0.5 × 0 × 1.0 × 1.0 = 0.0
2. **`evaluate_mill_capital()` caught exception and returned fail-safe 0.0**

### Production-Critical Risk

If TrustScorecardGenerator returns 0 for a new mill with no event history, then:
- Gate condition triggers: `advance_rate <= 0.0` blocks issuance
- **First-time operators cannot get their first token allocation**
- **This would be a complete blocker for production**

### Investigation Status

Unable to isolate exact root cause due to terminal/logging issues during testing. Key test `test_new_mill_gate.py` created but execution output not visible.

**What Must Happen Before Go-Live**:
1. Confirm TrustScorecardGenerator behavior for mill with zero event history
2. If it returns 0, either:
   - Change TrustScorecardGenerator to return minimum trust (e.g., 50) for new mills
   - Or remove `trust_score` from multiplication (make it additive/threshold instead)
3. Run full E2E tests with visible output confirming new mill can get first allocation

**Current Status**: Code is syntactically correct and logically sound, but untested in the scenario where a brand-new mill with no prior cycles requests its first token.
