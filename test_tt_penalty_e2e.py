"""
End-to-End Test: Turnover Time (TT) Penalty Integration

Tests the complete flow from cycle latency → turnover classification → advance rate → token allocation decision.

Key Scenarios:
1. FAST cycle (< 24h) → boosted rate (1.05×)
2. NORMAL cycle (24-48h) → standard rate (1.0×)
3. SLOW cycle (48-72h) → penalized rate (0.95×)
4. STALLED cycle (≥ 72h) → blocked (0.0×)

Expected Behavior:
- STALLED cycles result in zero advance rate
- Next token allocation is BLOCKED
- API returns "BLOCKED" status for STALLED last cycle
"""

import pytest
from decimal import Decimal
from backend.policy_execution_engine import (
    compute_per_cycle_advance_rate,
    classify_turnover_time,
    turnover_penalty,
)
from backend.config import BASE_CYCLE_KWH, BASE_ADVANCE_RATE


class TestTurnoverTimeClassification:
    """Test turnover time classification from lag hours."""
    
    def test_fast_classification(self):
        """< 24h → FAST"""
        assert classify_turnover_time(0.0) == "FAST"
        assert classify_turnover_time(12.0) == "FAST"
        assert classify_turnover_time(23.99) == "FAST"
    
    def test_normal_classification(self):
        """24-48h → NORMAL"""
        assert classify_turnover_time(24.0) == "NORMAL"
        assert classify_turnover_time(36.0) == "NORMAL"
        assert classify_turnover_time(47.99) == "NORMAL"
    
    def test_slow_classification(self):
        """48-72h → SLOW"""
        assert classify_turnover_time(48.0) == "SLOW"
        assert classify_turnover_time(60.0) == "SLOW"
        assert classify_turnover_time(71.99) == "SLOW"
    
    def test_stalled_classification(self):
        """≥ 72h → STALLED"""
        assert classify_turnover_time(72.0) == "STALLED"
        assert classify_turnover_time(96.0) == "STALLED"
        assert classify_turnover_time(120.0) == "STALLED"


class TestTurnoverPenaltyMultipliers:
    """Test penalty multiplier calculation for each classification."""
    
    def test_fast_bonus(self):
        """FAST: 1.05× (5% bonus)"""
        assert turnover_penalty("FAST") == 1.05
    
    def test_normal_no_penalty(self):
        """NORMAL: 1.0× (no penalty)"""
        assert turnover_penalty("NORMAL") == 1.0
    
    def test_slow_penalty(self):
        """SLOW: 0.95× (5% penalty)"""
        assert turnover_penalty("SLOW") == 0.95
    
    def test_stalled_block(self):
        """STALLED: 0.0× (complete block)"""
        assert turnover_penalty("STALLED") == 0.0
    
    def test_unknown_classification_defaults_to_normal(self):
        """Unknown classifications default to NORMAL (1.0×)"""
        assert turnover_penalty("UNKNOWN") == 1.0


class TestAdvanceRateWithTTPenalty:
    """Test advance rate calculation with TT penalty applied."""
    
    def test_fast_cycle_with_bonus(self):
        """
        FAST cycle: gets 5% bonus.
        trust=95, adherence=1.0, lag=12h (FAST)
        rate = 0.5 × (95/100) × 1.0² × 1.0 × 1.05 = 0.49875
        """
        rate = compute_per_cycle_advance_rate(
            trust_score=95.0,
            adherence=1.0,
            lag_hours=12.0,
            base_rate=0.5,
            turnover_classification="FAST"
        )
        assert abs(rate - 0.49875) < 0.0001
    
    def test_normal_cycle_no_penalty(self):
        """
        NORMAL cycle: no TT penalty.
        trust=95, adherence=1.0, lag=36h (NORMAL)
        rate = 0.5 × (95/100) × 1.0² × 0.95 × 1.0 = 0.45125
        """
        rate = compute_per_cycle_advance_rate(
            trust_score=95.0,
            adherence=1.0,
            lag_hours=36.0,
            base_rate=0.5,
            turnover_classification="NORMAL"
        )
        assert abs(rate - 0.45125) < 0.0001
    
    def test_slow_cycle_with_penalty(self):
        """
        SLOW cycle: 5% TT penalty applied.
        trust=95, adherence=1.0, lag=60h (SLOW)
        Latency penalty (60h): 0.90
        rate = 0.5 × (95/100) × 1.0² × 0.90 × 0.95 = 0.42638
        """
        rate = compute_per_cycle_advance_rate(
            trust_score=95.0,
            adherence=1.0,
            lag_hours=60.0,
            base_rate=0.5,
            turnover_classification="SLOW"
        )
        assert abs(rate - 0.42638) < 0.0001
    
    def test_stalled_cycle_blocked(self):
        """
        STALLED cycle: complete block (rate = 0.0).
        trust=95, adherence=1.0, lag=96h (STALLED)
        Even with perfect trust and adherence:
        rate = 0.5 × (95/100) × 1.0² × 0.85 × 0.0 = 0.0
        """
        rate = compute_per_cycle_advance_rate(
            trust_score=95.0,
            adherence=1.0,
            lag_hours=96.0,
            base_rate=0.5,
            turnover_classification="STALLED"
        )
        assert rate == 0.0
    
    def test_stalled_blocks_regardless_of_trust_and_adherence(self):
        """
        STALLED classification blocks allocation regardless of trust/adherence.
        Even best-case scenario (trust=100, adherence=1.0) results in 0.0.
        """
        rate = compute_per_cycle_advance_rate(
            trust_score=100.0,
            adherence=1.0,
            lag_hours=72.0,
            base_rate=0.5,
            turnover_classification="STALLED"
        )
        assert rate == 0.0
    
    def test_auto_classification_with_lag_hours(self):
        """
        When turnover_classification is not explicitly passed,
        it should default to NORMAL (no penalty).
        trust=95, adherence=1.0, lag=96h
        Without explicit STALLED classification, uses default NORMAL:
        rate = 0.5 × 0.95 × 1.0 × 0.85 × 1.0 = 0.40375
        """
        rate = compute_per_cycle_advance_rate(
            trust_score=95.0,
            adherence=1.0,
            lag_hours=96.0,
            base_rate=0.5,
            # Defaults to "NORMAL"
        )
        assert abs(rate - 0.40375) < 0.0001


class TestStalledCycleAllocations:
    """Test allocation sizing with STALLED cycles."""
    
    def test_stalled_allocation_is_zero(self):
        """
        When last cycle was STALLED, next allocation should be zero.
        lag_hours=96 → STALLED → advance_rate=0.0 → allocation=0
        """
        stalled_classification = classify_turnover_time(96.0)
        assert stalled_classification == "STALLED"
        
        # Compute allocation
        rate = compute_per_cycle_advance_rate(
            trust_score=90.0,
            adherence=0.95,
            lag_hours=96.0,
            base_rate=0.5,
            turnover_classification=stalled_classification
        )
        allocation_kwh = BASE_CYCLE_KWH * rate
        
        # Should be zero
        assert allocation_kwh == 0.0
    
    def test_fast_allocation_is_boosted(self):
        """
        When last cycle was FAST, allocation should be boosted (1.05×).
        lag_hours=12 → FAST → advance_rate boosted by 1.05×
        """
        fast_classification = classify_turnover_time(12.0)
        assert fast_classification == "FAST"
        
        # Compute allocation
        rate = compute_per_cycle_advance_rate(
            trust_score=90.0,
            adherence=0.95,
            lag_hours=12.0,
            base_rate=0.5,
            turnover_classification=fast_classification
        )
        allocation_kwh = BASE_CYCLE_KWH * rate
        
        # Should be boosted (> what NORMAL would be)
        normal_rate = compute_per_cycle_advance_rate(
            trust_score=90.0,
            adherence=0.95,
            lag_hours=12.0,
            base_rate=0.5,
            turnover_classification="NORMAL"
        )
        normal_kwh = BASE_CYCLE_KWH * normal_rate
        
        assert allocation_kwh > normal_kwh


class TestMixedPenalties:
    """Test TT penalty stacking with other penalties."""
    
    def test_stalled_plus_low_adherence(self):
        """
        STALLED penalty (0.0×) overrides all other penalties.
        Even with adherence penalty, result is blocked.
        """
        rate = compute_per_cycle_advance_rate(
            trust_score=50.0,
            adherence=0.5,
            lag_hours=96.0,
            base_rate=0.5,
            turnover_classification="STALLED"
        )
        # Should still be zero – STALLED blocks regardless
        assert rate == 0.0
    
    def test_slow_plus_latency_plus_low_trust(self):
        """
        SLOW penalty (0.95×) stacks multiplicatively with latency and trust.
        trust=60, adherence=0.85, lag=60h (SLOW)
        rate = 0.5 × (60/100) × 0.85² × 0.90 × 0.95
        """
        rate = compute_per_cycle_advance_rate(
            trust_score=60.0,
            adherence=0.85,
            lag_hours=60.0,
            base_rate=0.5,
            turnover_classification="SLOW"
        )
        expected = 0.5 * 0.60 * (0.85 ** 2) * 0.90 * 0.95
        assert abs(rate - expected) < 0.0001


class TestBlockedStateTransitions:
    """Test state transitions when STALLED cycles occur."""
    
    def test_stalled_to_normal_recovery(self):
        """
        After a STALLED cycle, next cycle that is NORMAL restores allocation.
        Cycle 1: 96h (STALLED) → rate=0.0
        Cycle 2: 36h (NORMAL) → rate normal
        """
        stalled_rate = compute_per_cycle_advance_rate(
            trust_score=90.0,
            adherence=0.95,
            lag_hours=96.0,
            base_rate=0.5,
            turnover_classification="STALLED"
        )
        assert stalled_rate == 0.0
        
        # Next cycle with better TT
        normal_rate = compute_per_cycle_advance_rate(
            trust_score=90.0,
            adherence=0.95,
            lag_hours=36.0,
            base_rate=0.5,
            turnover_classification="NORMAL"
        )
        assert normal_rate > 0.0
        assert normal_rate > stalled_rate
    
    def test_slow_to_stalled_progression(self):
        """
        Degradation: SLOW → STALLED progressively blocks capital.
        SLOW (60h): Some allocation
        STALLED (72h): Zero allocation
        """
        slow_rate = compute_per_cycle_advance_rate(
            trust_score=90.0,
            adherence=0.95,
            lag_hours=60.0,
            base_rate=0.5,
            turnover_classification="SLOW"
        )
        
        stalled_rate = compute_per_cycle_advance_rate(
            trust_score=90.0,
            adherence=0.95,
            lag_hours=72.0,
            base_rate=0.5,
            turnover_classification="STALLED"
        )
        
        assert slow_rate > 0.0
        assert stalled_rate == 0.0
        assert slow_rate > stalled_rate


# ============================================================================
# INTEGRATION TEST: Full E2E Flow
# ============================================================================

class TestEndToEndFlow:
    """Full end-to-end integration test."""
    
    def test_stalled_cycle_results_in_blocked_next_token(self):
        """
        Main integration test: STALLED cycle → BLOCKED next token.
        
        Scenario:
        1. Mill has last cycle with 96h lag (STALLED)
        2. classify_turnover_time detects STALLED
        3. compute_per_cycle_advance_rate returns 0.0
        4. Next token allocation is 0 kWh (BLOCKED)
        """
        # Step 1: Identify stalled cycle
        lag_hours = 96.0  # Extreme delay
        classification = classify_turnover_time(lag_hours)
        assert classification == "STALLED"
        
        # Step 2: Compute advance rate
        rate = compute_per_cycle_advance_rate(
            trust_score=85.0,  # Even with decent trust
            adherence=0.90,     # And decent adherence
            lag_hours=lag_hours,
            base_rate=BASE_ADVANCE_RATE,
            turnover_classification=classification
        )
        
        # Step 3: Verify blocked
        assert rate == 0.0
        
        # Step 4: Verify allocation is zero
        allocation_kwh = BASE_CYCLE_KWH * Decimal(rate)
        assert allocation_kwh == Decimal(0)
    
    def test_all_classifications_end_to_end(self):
        """
        Test all classifications in sequence.
        Verify rate progression: FAST > NORMAL > SLOW > STALLED
        """
        trust = 90.0
        adherence = 0.95
        
        rates = {}
        for lag_hours, expected_class in [
            (12.0, "FAST"),
            (36.0, "NORMAL"),
            (60.0, "SLOW"),
            (96.0, "STALLED"),
        ]:
            classification = classify_turnover_time(lag_hours)
            assert classification == expected_class
            
            rate = compute_per_cycle_advance_rate(
                trust_score=trust,
                adherence=adherence,
                lag_hours=lag_hours,
                base_rate=0.5,
                turnover_classification=classification
            )
            
            rates[classification] = rate
            print(f"{classification} (lag={lag_hours}h): rate={rate:.6f}")
        
        # Verify ordering: FAST > NORMAL > SLOW > STALLED
        assert rates["FAST"] > rates["NORMAL"]
        assert rates["NORMAL"] > rates["SLOW"]
        assert rates["SLOW"] > rates["STALLED"]
        assert rates["STALLED"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
