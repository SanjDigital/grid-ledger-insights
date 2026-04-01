"""
Dynamic Credit Envelope (DCE) Capital Controls Module.

Calculates per-mill credit capacity based on energy accountability,
verified throughput, and historical breach/volatility risk.

DCE = α × VR × EAR × (1 − RiskPenalty)
Where:
  α = advance rate (default 0.6)
  VR = Verified Revenue (VT × ERR)
  EAR = Energy Accountability Ratio
  RiskPenalty = breach-based + volatility-based penalty (capped at 0.5)

FORENSIC CONSTRAINT:
DCE calculations use ONLY audit-verified energy metrics. For Node 02 (Nabiwi),
this means using verified leakage of 6,833 kWh from Phase 2 forensic audit,
NOT historical estimates (10,991 kWh). All DCE inputs derive from reconciliation
records, which reflect verified physical measurements and audit conclusions.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Optional
from sqlmodel import Session, select

from scripts.init_db import (
    engine,
    Mill,
    ReconciliationRecord,
    MillIntegrityState,
    CreditMetrics,
    Cycle,
)
from backend.ear_thresholds import get_ear_interpretation, get_ear_tier


class CapitalControlsError(Exception):
    """Raised when DCE calculation fails."""
    pass


# ============================================================================
# SUSPICION TRACKER — Accumulate Pressure Without Proof
# ============================================================================

class SuspicionTracker:
    """
    Continuous suspicion score that decays slowly and accumulates pressure.
    
    Unlike binary breach flags, suspicion allows gradual pressure to build
    even without definitive proof. The system "watches" for patterns and
    penalizes operators for creating suspicious situations.
    
    Core Mechanism:
    - Score decays by decay_rate each day (0-1, default 0.1 = 10% decay)
    - Suspicious activity adds to score based on severity
    - When score >= threshold, a penalty multiplier (0.8) is applied
    - Penalty is applied to capital factors, reducing capacity
    
    Key Insight: Operators feel constant pressure from suspicious patterns,
    even when evidence isn't conclusive. This incentivizes clean operations.
    
    Example:
        tracker = SuspicionTracker(decay_rate=0.1, threshold=5.0)
        
        Day 1: 2% variance deviation → score = 0.1
        Day 2: Decay 10%, add 0.15 → score ≈ 0.24
        Day 3-7: Pattern continues → score accumulates
        Day 8: Score ≥ 5.0 → penalty_multiplier() = 0.8
               Capital capacity reduced by 20%
        
        Day 15: No more suspicious activity
                Score decays daily over time
        Day 30: Score < 5.0 → penalty_multiplier() = 1.0 (lifted)
    """
    
    def __init__(self, decay_rate: float = 0.1, threshold: float = 5.0):
        """
        Initialize SuspicionTracker.
        
        Args:
            decay_rate: Daily decay rate (0.0-1.0, default 0.1 = 10%)
                       Higher = faster forgetting
                       Lower = longer memory
            threshold: Score threshold to trigger penalty (default 5.0)
                      When score >= threshold, penalty_multiplier() = 0.8
        """
        self.score = 0.0           # Current suspicion score (0-10)
        self.decay_rate = decay_rate
        self.threshold = threshold
        self.max_score = 10.0      # Cap suspicion at 10.0
    
    def update(self, deviation_pct: float = 0.0, pattern_anomaly: bool = False) -> float:
        """
        Update suspicion score based on daily variance and pattern anomalies.
        
        The update combines two risk factors:
        1. VARIANCE DEVIATION: Deviation above natural tolerance (>1.5%)
        2. PATTERN ANOMALY: Evidence of suspicious pattern (entropy, Z-score, etc.)
        
        Formula:
            daily_risk = (max(0, deviation_pct - 1.5) / 10.0) + (0.5 if pattern_anomaly else 0)
            score = score × (1 - decay_rate) + daily_risk
            score = min(score, max_score)
        
        Args:
            deviation_pct: Daily variance percentage (e.g., 2.5 = 2.5% deviation)
                          Natural tolerance: ±1.5%
                          Above this adds to suspicion
            pattern_anomaly: True if entropy monitor, Z-score check, or
                           other pattern detector flags suspicious activity
        
        Returns:
            Updated suspicion score (0.0-10.0)
        
        Examples:
            # Clean day: 1% variance, no anomaly
            update(1.0, False) → minimal increase
            
            # Slightly suspicious: 2% variance, no pattern yet
            update(2.0, False) → score increases by ~0.05
            
            # Highly suspicious: 3% variance + pattern
            update(3.0, True) → score increases by ~0.6
            
            # Very concerning: 5% variance + pattern
            update(5.0, True) → score increases by ~0.7
        """
        # Decay: operator "credit" from previous days
        # Higher decay_rate = system forgives faster
        self.score = self.score * (1.0 - self.decay_rate)
        
        # Calculate daily risk contribution
        # 1. Variance risk: anything above 1.5% tolerance adds pressure
        #    Max contribution from variance: (10-1.5)/10 = 0.85
        variance_risk = max(0.0, deviation_pct - 1.5) / 10.0
        
        # 2. Pattern risk: 0.5 points if anomaly detected
        pattern_risk = 0.5 if pattern_anomaly else 0.0
        
        # Total daily addition
        daily_risk = variance_risk + pattern_risk
        
        # Add to running score
        self.score = self.score + daily_risk
        
        # Cap at maximum
        self.score = min(self.score, self.max_score)
        
        return self.score
    
    def decay_daily(self) -> float:
        """
        Apply daily decay without adding new risk.
        
        Use this on "clean" days where no new suspicious activity occurs.
        Score automatically decays based on decay_rate.
        
        Returns:
            Decayed suspicion score
        """
        self.score = self.score * (1.0 - self.decay_rate)
        return self.score
    
    def penalty_multiplier(self) -> float:
        """
        Calculate penalty multiplier based on suspicion score.
        
        Penalty Logic:
        - If score < threshold: return 1.0 (no penalty)
        - If score >= threshold: return 0.8 (20% capital reduction)
        
        The multiplier is applied to capital factors:
            DCE' = DCE × penalty_multiplier()
        
        A multiplier of 0.8 means:
        - Operator's capital capacity is 20% lower
        - Less buffer for variance
        - Higher scrutiny threshold
        
        Returns:
            Float (1.0 = full capacity, 0.8 = 20% penalty)
        """
        if self.score >= self.threshold:
            return 0.8  # 20% reduction when suspicious
        return 1.0      # No penalty below threshold
    
    def get_status(self) -> Dict[str, float]:
        """
        Get detailed suspicion status.
        
        Returns:
            Dict with current_score, threshold, multiplier, recovery_days_estimate
        """
        # Estimate recovery days (to get below threshold)
        if self.score >= self.threshold:
            # Decay formula: score * (1-decay)^n < threshold
            # Solve for n: n = log(threshold/score) / log(1-decay_rate)
            import math
            if self.decay_rate > 0 and self.score > 0:
                recovery_days = math.log(self.threshold / self.score) / math.log(1.0 - self.decay_rate)
                recovery_days = max(0, int(recovery_days) + 1)
            else:
                recovery_days = float('inf')
        else:
            recovery_days = 0
        
        return {
            "current_score": self.score,
            "threshold": self.threshold,
            "penalty_active": self.score >= self.threshold,
            "penalty_multiplier": self.penalty_multiplier(),
            "estimated_recovery_days": recovery_days,
        }


class CapitalControls:
    """Dynamic Credit Envelope calculator and capital controls enforcer."""

    # Default advance rate (configurable per mill)
    DEFAULT_ADVANCE_RATE = 0.6

    @staticmethod
    def get_mill_advance_rate(mill_id: str) -> float:
        """
        Retrieve configurable advance rate for a mill.
        
        Args:
            mill_id: Mill identifier
        
        Returns:
            Advance rate α (0.6 default, can be overridden per mill)
        
        Note:
            In production, this could read from a MillConfig table.
            Currently returns default.
        """
        # TODO: Implement per-mill advance rate configuration
        return CapitalControls.DEFAULT_ADVANCE_RATE

    @staticmethod
    def calculate_effective_revenue_rate(
        total_cash: float, metered_kwh: float
    ) -> float:
        """
        Calculate Effective Revenue Rate (ERR).
        
        ERR = cash_collected / metered_kwh
        
        Args:
            total_cash: Total cash collected in local currency
            metered_kwh: Physical energy consumed in kWh
        
        Returns:
            ERR (float)
        """
        if metered_kwh <= 0:
            return 0.0
        return total_cash / metered_kwh

    @staticmethod
    def calculate_verified_revenue(vt: float, err: float) -> float:
        """
        Calculate Verified Revenue.
        
        VR = VT × ERR
        
        Args:
            vt: Verified Throughput (kWh)
            err: Effective Revenue Rate
        
        Returns:
            VR (verified revenue in local currency)
        """
        return vt * err

    @staticmethod
    def count_breaches_30d(mill_id: str) -> int:
        """
        Count enforcement breaches for a mill in the last 30 days.
        
        Breaches tracked via state transitions in MillIntegrityState.
        A breach is recorded when state changes to UNDER_REVIEW, COMPROMISED, or SUSPENDED.
        
        Args:
            mill_id: Mill identifier
        
        Returns:
            Count of breaches in last 30 days
        """
        with Session(engine) as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
            
            # Count cycles with breach_breach_detected in last 30 days
            breach_cycles = session.exec(
                select(Cycle)
                .where(Cycle.mill_id == mill_id)
                .where(Cycle.gap_breach_detected == True)
                .where(Cycle.reconciled_at >= cutoff_date)
            ).all()
            
            breach_count = len(breach_cycles)
            
            # TODO: Also count other breaches from enforcement events
            # (temporal breaches, signature failures, etc.)
            
            return breach_count

    @staticmethod
    def calculate_volatility_score(mill_id: str, window_days: int = 30) -> float:
        """
        Calculate historical volatility score based on variance in recent reconciliations.
        
        Volatility measures consistency of energy accounting:
        - Low volatility (close to 0): Stable, consistent reporting
        - High volatility (close to 1): Erratic, unstable reporting
        
        Args:
            mill_id: Mill identifier
            window_days: Historical window to analyze (default 30 days)
        
        Returns:
            Volatility score (0.0 to 1.0)
        """
        with Session(engine) as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)
            
            records = session.exec(
                select(ReconciliationRecord)
                .where(ReconciliationRecord.mill_id == mill_id)
                .where(ReconciliationRecord.created_at >= cutoff_date)
                .order_by(ReconciliationRecord.created_at)
            ).all()
        
        if not records:
            return 0.0
        
        # Calculate coefficient of variation (stddev / mean) of variance_pct
        variances = [r.variance_pct for r in records]
        mean_variance = sum(variances) / len(variances)
        
        if mean_variance == 0:
            return 0.0
        
        # Squared deviations
        sq_deviations = [(v - mean_variance) ** 2 for v in variances]
        variance_of_variance = sum(sq_deviations) / len(sq_deviations)
        stddev = variance_of_variance ** 0.5
        
        # Coefficient of variation (cap at 1.0)
        cv = min(1.0, stddev / mean_variance) if mean_variance > 0 else 0.0
        
        return cv

    @staticmethod
    def calculate_risk_penalty(breach_count: int, volatility: float) -> float:
        """
        Calculate Risk Penalty from breach history and volatility.
        
        RiskPenalty = min(0.5, breach_count × 0.1 + volatility × 0.05)
        
        Logic:
        - Each breach adds 0.1 to penalty
        - Volatility contributes up to 0.05
        - Total capped at 0.5 (50% penalty maximum)
        - If no breaches and low volatility: penalty ≈ 0.0
        
        Args:
            breach_count: Number of breaches in last 30 days
            volatility: Volatility score (0-1)
        
        Returns:
            Risk penalty (0.0 to 0.5)
        """
        breach_penalty = breach_count * 0.1
        volatility_penalty = volatility * 0.05
        total_penalty = breach_penalty + volatility_penalty
        
        return min(0.5, total_penalty)

    @staticmethod
    def get_rolling_efficiency(mill_id: str, days: int = 30) -> float:
        """
        Calculate 30-day rolling average efficiency for a mill.
        
        Efficiency measures how much of expected revenue is actually verified:
        - 1.0 = 100% (perfect accountability)
        - 0.8 = 80% (80 of every 100 is verified)
        - 0.75 = 75% (minimum threshold for avoiding cumulative penalty)
        
        Uses Energy Accountability Ratio (EAR) as the efficiency metric,
        which represents verified energy / physical energy consumed.
        
        Args:
            mill_id: Mill identifier
            days: Historical window (default 30 days)
        
        Returns:
            Average efficiency (0.0 to 2.0), or 1.0 if no data available
        """
        with Session(engine) as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            records = session.exec(
                select(ReconciliationRecord)
                .where(ReconciliationRecord.mill_id == mill_id)
                .where(ReconciliationRecord.created_at >= cutoff_date)
                .order_by(ReconciliationRecord.created_at)
            ).all()
        
        if not records:
            return 1.0  # No data: assume neutral (1.0), not punitive
        
        # Average EAR across all reconciliation records in window
        ear_values = [r.energy_accountability_ratio for r in records if r.energy_accountability_ratio > 0]
        
        if not ear_values:
            return 1.0
        
        rolling_avg = sum(ear_values) / len(ear_values)
        return rolling_avg

    @staticmethod
    def cumulative_penalty(mill_id: str) -> float:
        """
        Calculate cumulative loss pressure penalty based on long-term efficiency.
        
        CUMULATIVE LOSS PRESSURE (30-day Rolling Average):
            If 30-day average efficiency < 75%, a rolling memory penalty is applied.
            This prevents short-term spikes from erasing evidence of prolonged 
            underperformance. The system remembers damage.
        
        Logic:
        - If rolling_efficiency >= 0.75: penalty = 1.0 (no reduction)
        - If rolling_efficiency < 0.75:  penalty = 0.5 (base rate permanently halved)
        
        The base_rate is multiplied by this penalty, so:
        - Normal case: base_rate × 1.0 = no change
        - Prolonged underperformance: base_rate × 0.5 = halved capacity
        
        Recovery: Penalty lifts ONLY when 30-day rolling average ≥ 0.75
        
        Args:
            mill_id: Mill identifier
        
        Returns:
            Penalty multiplier (0.5 or 1.0)
        """
        rolling_efficiency = CapitalControls.get_rolling_efficiency(mill_id, days=30)
        
        if rolling_efficiency < 0.75:
            return 0.5  # Permanent halving until recovery
        
        return 1.0  # No penalty

    @staticmethod
    def get_suspicion_tracker(mill_id: str) -> SuspicionTracker:
        """
        Retrieve or instantiate suspicion tracker for a mill.
        
        Loads the current suspicion score from MillIntegrityState and 
        returns a SuspicionTracker instance. If no state exists, creates
        a new tracker with score 0.0.
        
        Args:
            mill_id: Mill identifier
        
        Returns:
            SuspicionTracker instance with current score
        """
        with Session(engine) as session:
            mill_state = session.get(MillIntegrityState, mill_id)
        
        tracker = SuspicionTracker(decay_rate=0.1, threshold=5.0)
        
        if mill_state:
            tracker.score = mill_state.suspicion_score
        
        return tracker

    @staticmethod
    def update_suspicion(
        mill_id: str,
        deviation_pct: float = 0.0,
        pattern_anomaly: bool = False
    ) -> Dict:
        """
        Update suspicion score for a mill and apply daily decay.
        
        This method:
        1. Loads current suspicion tracker
        2. Applies daily decay
        3. Adds new risk from today's variance/patterns
        4. Saves updated score to database
        5. Returns updated status
        
        Args:
            mill_id: Mill identifier
            deviation_pct: Daily variance percentage (e.g., 2.5 = 2.5%)
            pattern_anomaly: True if suspicious pattern detected
        
        Returns:
            Dict with updated suspicion status
        """
        tracker = CapitalControls.get_suspicion_tracker(mill_id)
        
        # Update suspicion with today's activity
        tracker.update(deviation_pct, pattern_anomaly)
        
        # Save to database
        with Session(engine) as session:
            mill_state = session.get(MillIntegrityState, mill_id)
            
            if not mill_state:
                # Create new state if doesn't exist
                mill_state = MillIntegrityState(
                    mill_id=mill_id,
                    state="VERIFIED",
                    suspicion_score=tracker.score,
                    suspicion_updated_at=datetime.now(timezone.utc)
                )
                session.add(mill_state)
            else:
                # Update existing state
                mill_state.suspicion_score = tracker.score
                mill_state.suspicion_updated_at = datetime.now(timezone.utc)
            
            session.add(mill_state)
            session.commit()
        
        return tracker.get_status()

    @staticmethod
    def suspicion_penalty(mill_id: str) -> float:
        """
        Calculate suspicion-based penalty multiplier.
        
        When suspicion score exceeds threshold (5.0), applies a 20% penalty
        to capital-related factors (DCE, advance rate, etc.).
        
        Suspicion Penalty:
        - If score < 5.0: return 1.0 (no penalty)
        - If score >= 5.0: return 0.8 (20% reduction)
        
        This multiplier stacks with other penalties (cumulative loss, 
        hard floor, structural leakage, etc.).
        
        Args:
            mill_id: Mill identifier
        
        Returns:
            Penalty multiplier (0.8 or 1.0)
        """
        tracker = CapitalControls.get_suspicion_tracker(mill_id)
        return tracker.penalty_multiplier()

    @classmethod
    def calculate_dce(cls, mill_id: str) -> Optional[Dict]:
        """
        Calculate Dynamic Credit Envelope (DCE) for a mill.
        
        DCE = α × VR × EAR × (1 − RiskPenalty)
        
        Where:
        - α = advance rate (default 0.6)
        - VR = Verified Revenue = VT × ERR
        - EAR = Energy Accountability Ratio
        - RiskPenalty = breach-based + volatility-based penalty (capped at 0.5)
        
        Args:
            mill_id: Mill identifier
        
        Returns:
            Dict containing:
            - dce: Final Dynamic Credit Envelope value
            - components: Breakdown of α, VR, EAR, RiskPenalty
            - metrics: Breach count, volatility, ERR
            - recommendation: APPROVE, CONDITIONAL, or DECLINE
        
        Raises:
            CapitalControlsError if mill not found or insufficient data
        """
        with Session(engine) as session:
            mill = session.get(Mill, mill_id)
            if not mill:
                raise CapitalControlsError(f"Mill {mill_id} not found")
            
            # Fetch latest reconciliation record for this mill
            latest_recon = session.exec(
                select(ReconciliationRecord)
                .where(ReconciliationRecord.mill_id == mill_id)
                .order_by(ReconciliationRecord.created_at.desc())
            ).first()
            
            if not latest_recon:
                raise CapitalControlsError(
                    f"No reconciliation record found for mill {mill_id}"
                )
            
            # Extract parameters from reconciliation
            vt = latest_recon.verified_throughput  # Already calculated
            ear = latest_recon.energy_accountability_ratio
            physical_consumed = latest_recon.physical_consumed
            total_cash = latest_recon.total_cash
            
            # Calculate ERR (Effective Revenue Rate)
            err = cls.calculate_effective_revenue_rate(total_cash, physical_consumed)
            
            # Calculate VR (Verified Revenue)
            vr = cls.calculate_verified_revenue(vt, err)
            
            # Calculate RiskPenalty
            breach_count = cls.count_breaches_30d(mill_id)
            volatility = cls.calculate_volatility_score(mill_id)
            risk_penalty = cls.calculate_risk_penalty(breach_count, volatility)
            
            # Calculate Suspicion Penalty
            suspicion_multiplier = cls.suspicion_penalty(mill_id)
            
            # Get advance rate
            alpha = cls.get_mill_advance_rate(mill_id)
            
            # Calculate DCE with all penalties applied
            # DCE = α × VR × EAR × (1 − RiskPenalty) × suspicion_multiplier
            base_dce = alpha * vr * ear * (1.0 - risk_penalty)
            dce = base_dce * suspicion_multiplier
            
            # Determine recommendation
            if dce >= vr * 0.5:  # Can advance 50% of VR
                if breach_count == 0 and volatility < 0.2:
                    recommendation = "APPROVE"
                else:
                    recommendation = "CONDITIONAL"
            else:
                recommendation = "DECLINE"
            
            # Store result
            credit_metric = CreditMetrics(
                mill_id=mill_id,
                timestamp=datetime.now(timezone.utc),
                advance_rate=alpha,
                effective_revenue_rate=err,
                energy_accountability_ratio=ear,
                verified_throughput=vt,
                verified_revenue=vr,
                breach_count_30d=breach_count,
                volatility_score=volatility,
                risk_penalty=risk_penalty,
                dynamic_credit_envelope=dce,
                reconciliation_record_id=latest_recon.id,
                status="CALCULATED",
            )
            session.add(credit_metric)
            session.commit()
            session.refresh(credit_metric)
            
            return {
                "mill_id": mill_id,
                "mill_name": mill.name,
                "location": mill.location,
                "timestamp": credit_metric.timestamp.isoformat(),
                
                # DCE result
                "dynamic_credit_envelope": round(dce, 2),
                
                # Components breakdown
                "components": {
                    "advance_rate_alpha": round(alpha, 4),
                    "verified_revenue_vr": round(vr, 2),
                    "energy_accountability_ratio_ear": round(ear, 4),
                    "risk_penalty": round(risk_penalty, 4),
                },
                
                # Metrics
                "metrics": {
                    "effective_revenue_rate_err": round(err, 4),
                    "verified_throughput_kwh": round(vt, 2),
                    "breaches_30d": breach_count,
                    "volatility_score": round(volatility, 4),
                    "physical_consumed_kwh": round(physical_consumed, 2),
                    "total_cash_collected": round(total_cash, 2),
                },
                
                # Financial recommendation
                "recommendation": recommendation,
                "rationale": cls._generate_recommendation_rationale(
                    dce, vr, ear, risk_penalty, breach_count, volatility
                ),
                
                # Database reference
                "credit_metric_id": credit_metric.id,
                "reconciliation_record_id": latest_recon.id,
            }

    @staticmethod
    def _generate_recommendation_rationale(
        dce: float,
        vr: float,
        ear: float,
        risk_penalty: float,
        breach_count: int,
        volatility: float,
    ) -> str:
        """Generate human-readable rationale for DCE recommendation."""
        reasons = []
        
        if dce >= vr * 0.5:
            reasons.append(f"Strong DCE: {dce:.0f} MK ({dce/vr*100:.1f}% of VR)")
        elif dce >= vr * 0.3:
            reasons.append(f"Moderate DCE: {dce:.0f} MK ({dce/vr*100:.1f}% of VR)")
        else:
            reasons.append(f"Weak DCE: {dce:.0f} MK ({dce/vr*100:.1f}% of VR)")
        
        # Apply Bounded Imperfection Doctrine: EAR < 1.0 can still be acceptable
        ear_interpretation = get_ear_interpretation(ear)
        reasons.append(ear_interpretation)
        
        if risk_penalty > 0.3:
            reasons.append(f"High risk penalty applied: {risk_penalty:.1%}")
        
        if breach_count > 0:
            reasons.append(f"{breach_count} breach(es) in last 30 days")
        
        if volatility > 0.3:
            reasons.append(f"High volatility: {volatility:.1%} (inconsistent reporting)")
        
        return "; ".join(reasons)

    @classmethod
    def get_dce_history(cls, mill_id: str, days: int = 30) -> list:
        """
        Retrieve DCE calculation history for a mill.
        
        Args:
            mill_id: Mill identifier
            days: Historical window (default 30)
        
        Returns:
            List of CreditMetrics records, newest first
        """
        with Session(engine) as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            
            records = session.exec(
                select(CreditMetrics)
                .where(CreditMetrics.mill_id == mill_id)
                .where(CreditMetrics.timestamp >= cutoff_date)
                .order_by(CreditMetrics.timestamp.desc())
            ).all()
            
            return [
                {
                    "timestamp": r.timestamp.isoformat(),
                    "dce": round(r.dynamic_credit_envelope, 2),
                    "vr": round(r.verified_revenue, 2),
                    "ear": round(r.energy_accountability_ratio, 4),
                    "risk_penalty": round(r.risk_penalty, 4),
                    "breach_count": r.breach_count_30d,
                }
                for r in records
            ]
