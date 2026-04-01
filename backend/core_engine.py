import json
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_BUDGETED_RATE_MWK = 1600.0  # MWK/kWh
STANDARD_BUY_MWK = 20000.0
GOLDEN_STANDARD_KWH = 59.9
GOLD_ZONE_VARIANCE_PCT = 0.05  # 5%


class AssetStatus(Enum):
    LOCKED = "LOCKED"
    UNLOCKED = "UNLOCKED"
    BLOCKED = "BLOCKED"


class EngineStatus(Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


def _engine_status_from_score(score: float) -> EngineStatus:
    if score >= 95:
        return EngineStatus.GREEN
    if score >= 80:
        return EngineStatus.YELLOW
    return EngineStatus.RED


@dataclass
class ReceiptRecord:
    meter_id: str
    date: datetime
    amount_mwk: float
    units_kwh: float
    rate_mwk_per_kwh: float
    raw_text: str


class ESCOMReceiptParser:
    """Parser for ESCOM SMS / receipt manual entry for Malawi energy tokens."""

    meter_re = re.compile(r"(?:Meter(?:\s+ID)?[:]?\s*)(37\d{9})")
    date_re = re.compile(r"(?:Date[:]?\s*)(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})")
    amount_re = re.compile(r"(?:MWK\s*)?([0-9][0-9,]*\.?[0-9]*)\s*(?:MWK)?")
    units_re = re.compile(r"([0-9]+\.?[0-9]*)\s*(?:kWh|KWH|kwh)")
    rate_re = re.compile(r"([0-9]+\.?[0-9]*)\s*(?:MWK/kWh|MWK\s*/\s*kWh)")

    @classmethod
    def _normalize_number(cls, raw: str) -> float:
        return float(raw.replace(",", ""))

    @classmethod
    def parse(cls, raw_receipt_text: str) -> ReceiptRecord:
        text = raw_receipt_text.strip()

        meter_match = cls.meter_re.search(text)
        if not meter_match:
            raise ValueError("Meter ID not found in receipt")
        meter_id = meter_match.group(1)

        date_match = cls.date_re.search(text)
        if date_match:
            date_raw = date_match.group(1)
            if "-" in date_raw:
                date_val = datetime.fromisoformat(date_raw)
            else:
                date_val = datetime.strptime(date_raw, "%d/%m/%Y")
        else:
            date_val = datetime.now(timezone.utc)

        units_match = cls.units_re.search(text)
        if not units_match:
            raise ValueError("Units (kWh) not found in receipt")
        units_kwh = cls._normalize_number(units_match.group(1))

        # amount could be several numbers; pick first MWK-like token that is not also units
        amount_match = None
        for m in re.finditer(r"MWK\s*([0-9][0-9,]*\.?[0-9]*)", text, flags=re.IGNORECASE):
            amount_match = m
            break

        if amount_match:
            amount_mwk = cls._normalize_number(amount_match.group(1))
        else:
            # fallback: first numeric value > 0 and not units
            numeric_tokens = [cls._normalize_number(v) for v in re.findall(r"([0-9][0-9,]*\.?[0-9]*)", text)]
            if len(numeric_tokens) >= 2:
                amount_mwk = max(numeric_tokens)
            elif numeric_tokens:
                amount_mwk = numeric_tokens[0]
            else:
                raise ValueError("Amount (MWK) not found in receipt")

        rate_match = cls.rate_re.search(text)
        if rate_match:
            rate = cls._normalize_number(rate_match.group(1))
        else:
            rate = DEFAULT_BUDGETED_RATE_MWK

        return ReceiptRecord(
            meter_id=meter_id,
            date=date_val,
            amount_mwk=amount_mwk,
            units_kwh=units_kwh,
            rate_mwk_per_kwh=rate,
            raw_text=text,
        )

    @classmethod
    def expected_units_for_standard_buy(cls, rate_mwk_per_kwh: Optional[float] = None) -> float:
        rate = rate_mwk_per_kwh or DEFAULT_BUDGETED_RATE_MWK
        if rate <= 0:
            raise ValueError("Rate must be greater than 0")
        return STANDARD_BUY_MWK / rate


class AnomalyDetection:
    """
    The Red Flag Engine: Enforces the 'Golden Standard' of industrial integrity.
    
    This class is the primary defense against 'Micro-Skimming'—a behavior 
    identified in the Mkwinda pilot where operators utilized small, unauthorized 
    energy buys to mask production yield.
    """

    def __init__(self, golden_standard_kwh=59.9):
        # 59.9 kWh is the 'Golden Standard' derived from the MWK 20,000 baseline.
        # This represents a full, auditable production cycle.
        self.golden_standard = golden_standard_kwh
        self.rejection_log: List[Dict[str, Any]] = []

    def check_micro_skimming(self, reported_kwh):
        """
        Validates the energy ingest against the Fiduciary Baseline.
        
        Logic:
        - Exact Match (59.9): High Integrity. Asset is cleared for production.
        - Deviation (>5%): Potential Anomaly. Triggers a 'Red Flag' for management.
        - Micro-Buy (<15 kWh): High Risk. Categorized as a 'Skimming Signature'.
        
        Mathematical Variance:
        V = abs((K_reported - K_standard) / K_standard) * 100
        """
        if reported_kwh < 0:
            raise ValueError("Reported kWh cannot be negative")

        deviation = abs(reported_kwh - self.golden_standard) / self.golden_standard

        # CATEGORIZATION LOGIC
        # We don't just return a boolean; we return the 'Risk Profile' of the cycle.
        if reported_kwh < 15.0:
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reported_kwh": reported_kwh,
                "golden_standard_kwh": self.golden_standard,
                "deviation_pct": deviation * 100,
                "status": "BLOCKED",
                "risk_level": "CRITICAL",
                "reason": "Micro-Skimming Signature detected (Ref: Jan 12/23 Anomalies)."
            }
            self.rejection_log.append(event)
            return {
                "status": "BLOCKED",
                "risk_level": "CRITICAL",
                "reason": "Micro-Skimming Signature detected (Ref: Jan 12/23 Anomalies)."
            }

        if deviation > 0.05:
            event = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "reported_kwh": reported_kwh,
                "golden_standard_kwh": self.golden_standard,
                "deviation_pct": deviation * 100,
                "status": "FLAGGED",
                "risk_level": "MODERATE",
                "reason": f"Variance of {deviation:.2%} exceeds 5% Fiduciary Threshold."
            }
            self.rejection_log.append(event)
            return {
                "status": "FLAGGED",
                "risk_level": "MODERATE",
                "reason": f"Variance of {deviation:.2%} exceeds 5% Fiduciary Threshold."
            }

        return {
            "status": "VERIFIED",
            "risk_level": "LOW",
            "reason": "Compliance with Golden Standard confirmed."
        }


class TripleEngine:
    """Triple Engine: Conservation, Yield, Leakage."""

    @staticmethod
    def enforce_wallet_separation(revenue_wallet_id: str, opex_wallet_id: str) -> bool:
        return revenue_wallet_id != opex_wallet_id

    @staticmethod
    def conservation_score(reported_kwh: float, token_kwh: float) -> float:
        if token_kwh <= 0:
            raise ValueError("token_kwh must be greater than 0")
        if reported_kwh < 0:
            raise ValueError("reported_kwh cannot be negative")

        mismatch_pct = min(100.0, abs(reported_kwh - token_kwh) / token_kwh * 100.0)
        score = max(0.0, 100.0 - mismatch_pct)
        return round(score, 2)

    @staticmethod
    def yield_score(actual_revenue_mwk: float, expected_revenue_mwk: float) -> float:
        if expected_revenue_mwk <= 0:
            raise ValueError("expected_revenue_mwk must be greater than 0")

        ratio_pct = actual_revenue_mwk / expected_revenue_mwk * 100.0
        score = round(min(max(ratio_pct, 0.0), 100.0), 2)
        return score

    @staticmethod
    def leakage_score(opex_mwk: float, gross_mwk: float) -> float:
        if gross_mwk <= 0:
            raise ValueError("gross_mwk must be greater than 0")
        if opex_mwk < 0:
            raise ValueError("opex_mwk cannot be negative")

        leakage_pct = min(100.0, (opex_mwk / gross_mwk) * 100.0)
        score = max(0.0, 100.0 - leakage_pct)
        return round(score, 2)

    @staticmethod
    def overall_score(conservation_pct: float, yield_pct: float, leakage_pct: float) -> float:
        for x in (conservation_pct, yield_pct, leakage_pct):
            if x < 0 or x > 100:
                raise ValueError("All component scores must be within [0, 100]")

        return round((conservation_pct + yield_pct + leakage_pct) / 3.0, 2)

    @staticmethod
    def status_from_score(score: float) -> EngineStatus:
        return _engine_status_from_score(score)

    def evaluate_cycle(
        self,
        reported_kwh: float,
        token_kwh: float,
        actual_revenue_mwk: float,
        expected_revenue_mwk: float,
        opex_mwk: float,
        gross_mwk: float,
        revenue_wallet_id: str,
        opex_wallet_id: str,
    ) -> Dict[str, Any]:
        if not self.enforce_wallet_separation(revenue_wallet_id, opex_wallet_id):
            return {
                "overall_score": 0.0,
                "status": EngineStatus.RED.value,
                "reason": "Wallets are merged. Revenue and OpEx must be strictly separated.",
            }

        conservation_pct = self.conservation_score(reported_kwh, token_kwh)
        yield_pct = self.yield_score(actual_revenue_mwk, expected_revenue_mwk)
        leakage_pct = self.leakage_score(opex_mwk, gross_mwk)
        overall = self.overall_score(conservation_pct, yield_pct, leakage_pct)
        status = self.status_from_score(overall)

        return {
            "conservation_pct": conservation_pct,
            "yield_pct": yield_pct,
            "leakage_pct": leakage_pct,
            "overall_score": overall,
            "status": status.value,
        }


class FiduciaryYieldCalculator:
    """Revenue projection from ingested units."""

    def __init__(self, budgeted_rate_mwk: float = DEFAULT_BUDGETED_RATE_MWK):
        if budgeted_rate_mwk <= 0:
            raise ValueError("Budgeted rate must be > 0")
        self.budgeted_rate_mwk = budgeted_rate_mwk

    def expected_revenue(self, units_ingested: float) -> float:
        if units_ingested < 0:
            raise ValueError("units_ingested cannot be negative")
        return round(units_ingested * self.budgeted_rate_mwk, 2)


@dataclass
class ReconciliationReport:
    cash_collected_mwk: float
    expected_revenue_mwk: float
    timestamp: datetime = field(default_factory=datetime.utcnow)


class Gatekeeper:
    """Asset status state machine enforcing No-Reconcile, No-Power."""

    def __init__(self):
        self.asset_status = AssetStatus.LOCKED
        self.history: List[ReconciliationReport] = []
        self.rejection_log: List[Dict[str, Any]] = []
        self.fiscal_incident_log: List[Dict[str, Any]] = []
        self.incident_handler = None

    def token_authorization_allowed(self) -> bool:
        return self.asset_status == AssetStatus.UNLOCKED

    def set_incident_handler(self, handler):
        """Set a custom incident webhook handler (callable)."""
        self.incident_handler = handler

    def trigger_fiscal_lock_incident(
        self,
        site_id: str,
        score: float,
        reason: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        incident = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "site_id": site_id,
            "score": score,
            "reason": reason,
            "payload": payload,
        }
        self.fiscal_incident_log.append(incident)

        if callable(self.incident_handler):
            try:
                self.incident_handler(incident)
            except Exception:
                # keep system resilient; incident still recorded
                pass

        return incident

    def reconcile(
        self,
        cash_collected_mwk: float,
        expected_revenue_mwk: float,
        site_id: Optional[str] = None,
        conservation_score: Optional[float] = None,
        opex_mwk: Optional[float] = None,
        gross_mwk: Optional[float] = None,
    ) -> AssetStatus:
        if cash_collected_mwk < 0 or expected_revenue_mwk <= 0:
            self.asset_status = AssetStatus.BLOCKED
            return self.asset_status

        variance = abs(cash_collected_mwk - expected_revenue_mwk) / expected_revenue_mwk
        report = ReconciliationReport(cash_collected_mwk=cash_collected_mwk,
                                      expected_revenue_mwk=expected_revenue_mwk)
        self.history.append(report)

        score_pct = max(0.0, 100.0 - abs(variance) * 100.0)

        if score_pct >= 95.0:
            self.asset_status = AssetStatus.UNLOCKED
        elif score_pct >= 80.0:
            self.asset_status = AssetStatus.LOCKED
        else:
            self.asset_status = AssetStatus.BLOCKED

        if self.asset_status != AssetStatus.UNLOCKED:
            self.rejection_log.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "cash_collected_mwk": cash_collected_mwk,
                "expected_revenue_mwk": expected_revenue_mwk,
                "variance_pct": variance * 100,
                "score_pct": score_pct,
                "status": self.asset_status.value,
            })

        if self.asset_status == AssetStatus.BLOCKED and site_id:
            leakage_ratio = None
            if opex_mwk is not None and gross_mwk is not None and gross_mwk > 0:
                leakage_ratio = opex_mwk / gross_mwk

            self.trigger_fiscal_lock_incident(
                site_id=site_id,
                score=score_pct,
                reason="Physics/Yield Mismatch Detected",
                payload={
                    "conservation_score": conservation_score,
                    "leakage_ratio": leakage_ratio,
                    "cash_mwk": cash_collected_mwk,
                    "expected_revenue_mwk": expected_revenue_mwk,
                },
            )

        return self.asset_status

    def reconcile_ok(self, cash_collected_mwk: float, expected_revenue_mwk: float) -> bool:
        """
        Boolean wrapper for the reconciliation gate.
        Returns True ONLY if status is AssetStatus.UNLOCKED.
        """
        status = self.reconcile(cash_collected_mwk, expected_revenue_mwk)
        return status == AssetStatus.UNLOCKED

    def get_rejection_log(self) -> List[Dict[str, Any]]:
        """Retrieve reconciliation rejection log."""
        return self.rejection_log

    def clear_rejection_log(self):
        """Clear rejection log history."""
        self.rejection_log = []

    def get_latest_status(self) -> AssetStatus:
        """Return the current asset status."""
        return self.asset_status

    def is_blocked(self) -> bool:
        return self.asset_status == AssetStatus.BLOCKED


@dataclass
class GoldZoneEntry:
    date: datetime
    meter_id: str
    within_variance: bool
    deviation_pct: float


class IntegrityReportAPI:
    """Schema for 90-day Gold Zone adherence reports for credit scoring."""

    @staticmethod
    def generate(gold_zone_entries: List[GoldZoneEntry]) -> Dict[str, Any]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=90)
        recent = [e for e in gold_zone_entries if e.date >= cutoff]

        total = len(recent)
        in_zone = sum(1 for e in recent if e.within_variance)

        return {
            "period_days": 90,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_entries": total,
            "in_gold_zone": in_zone,
            "gold_zone_rate_pct": round((in_zone / total * 100) if total else 0.0, 2),
            "records": [
                {
                    "date": e.date.isoformat(),
                    "meter_id": e.meter_id,
                    "within_variance": e.within_variance,
                    "deviation_pct": round(e.deviation_pct, 4),
                }
                for e in recent
            ],
        }

    @staticmethod
    def to_json(report_dict: Dict[str, Any]) -> str:
        return json.dumps(report_dict, indent=2, sort_keys=True, default=str)


# Example payload style to support SMS/manual data pipe
def parse_sms_or_manual_payload(payload: Dict[str, Any]) -> ReceiptRecord:
    if "raw_text" in payload:
        return ESCOMReceiptParser.parse(payload["raw_text"])

    return ESCOMReceiptParser.parse(
        f"Meter ID: {payload.get('meter_id')} Date: {payload.get('date')} "
        f"Amount: MWK {payload.get('amount_mwk')} Units: {payload.get('units_kwh')} kWh "
        f"Rate: {payload.get('rate_mwk_per_kwh', DEFAULT_BUDGETED_RATE_MWK)} MWK/kWh"
    )


if __name__ == "__main__":
    sample = "Meter ID: 37154345799 Date: 2026-03-09 Amount: MWK 95840 Units: 59.9 kWh Rate: MWK 1600/kWh"
    record = ESCOMReceiptParser.parse(sample)
    print('Parsed receipt:', asdict(record))

    anomaly = AnomalyDetection().check_micro_skimming(record.units_kwh)
    print('Anomaly check:', anomaly)

    calc = FiduciaryYieldCalculator(1600)
    expected = calc.expected_revenue(record.units_kwh)
    print('Expected revenue:', expected)

    gate = Gatekeeper()
    print('Initial status:', gate.asset_status)
    gate.reconcile(cash_collected_mwk=expected, expected_revenue_mwk=expected)
    print('Post-reconcile status:', gate.asset_status)

    entry = GoldZoneEntry(date=datetime.utcnow(), meter_id=record.meter_id, within_variance=True, deviation_pct=0.0)
    report = IntegrityReportAPI.generate([entry])
    print('Integrity report:', IntegrityReportAPI.to_json(report))
