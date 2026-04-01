import pytest
from datetime import datetime, timedelta, timezone

from backend.core_engine import (
    AnomalyDetection,
    FiduciaryYieldCalculator,
    Gatekeeper,
    TripleEngine,
    ESCOMReceiptParser,
    AssetStatus,
    GoldZoneEntry,
    IntegrityReportAPI,
)
from backend.cycle_manager import issue_token, FiduciaryLockError, ingest_event
from backend.identity_manager import IdentityManager, IdentityError, ReplayError
import binascii
import json
from base64 import b64encode
from hashlib import sha256

from scripts.init_db import create_db_and_tables, engine, Wallet, WalletLineage, TokenPurchase, Cycle, Operator, Mill, Role, RolePermission, SitePhysicsConstraint, ConstraintManifest, DailyReport, OperatorProfile, EventLog
from sqlmodel import Session, select, delete

from scripts.init_db import EventLog
from backend.authority_engine import AuthorityError

def test_anomaly_detection_exact_match():
    ad = AnomalyDetection()
    result = ad.check_micro_skimming(59.9)
    assert result["status"] == "VERIFIED"
    assert result["risk_level"] == "LOW"


def test_anomaly_detection_small_micro_skimming():
    ad = AnomalyDetection()
    result = ad.check_micro_skimming(10.0)
    assert result["status"] == "BLOCKED"
    assert result["risk_level"] == "CRITICAL"


def test_anomaly_detection_out_of_tolerance():
    ad = AnomalyDetection()
    result = ad.check_micro_skimming(63.0)
    assert result["status"] == "FLAGGED"
    assert result["risk_level"] == "MODERATE"


def test_fiduciary_yield_calculator_expected_revenue():
    calc = FiduciaryYieldCalculator(1600)
    assert calc.expected_revenue(59.9) == pytest.approx(95840.0, rel=1e-6)


def test_gatekeeper_reconcile_ok_wrapper_with_tolerance_edges():
    gate = Gatekeeper()
    expected = 95840.0

    # 4.9% variance (within the gold zone) should unlock
    assert gate.reconcile_ok(91144.0, expected) is True
    assert gate.asset_status == AssetStatus.UNLOCKED

    # set locked state to isolate the next check
    gate.asset_status = AssetStatus.LOCKED

    # 5.1% variance (outside the gold zone) should remain locked
    assert gate.reconcile_ok(90952.0, expected) is False
    assert gate.asset_status == AssetStatus.LOCKED


def test_gatekeeper_reconcile_blocked_negative_values():
    gate = Gatekeeper()
    status = gate.reconcile(-1.0, 95840.0)
    assert status == AssetStatus.BLOCKED
    assert gate.token_authorization_allowed() is False


def test_escom_receipt_parser_test_case():
    raw = "Meter ID: 37154345799 Date: 2026-03-09 Amount: MWK 95840 Units: 59.9 kWh Rate: MWK 1600/kWh"
    rec = ESCOMReceiptParser.parse(raw)
    assert rec.meter_id == "37154345799"
    assert rec.units_kwh == pytest.approx(59.9, rel=1e-6)
    assert rec.amount_mwk == pytest.approx(95840.0)


def test_standard_buy_dynamic_units():
    expected_default = ESCOMReceiptParser.expected_units_for_standard_buy(1600)
    assert expected_default == pytest.approx(12.5)

    expected_higher = ESCOMReceiptParser.expected_units_for_standard_buy(2000)
    assert expected_higher == pytest.approx(10.0)


def test_triple_engine_conservation_yield_leakage_green():
    engine = TripleEngine()

    result = engine.evaluate_cycle(
        reported_kwh=60.0,
        token_kwh=59.9,
        actual_revenue_mwk=96000.0,
        expected_revenue_mwk=95840.0,
        opex_mwk=10000.0,
        gross_mwk=96000.0,
        revenue_wallet_id="walletA",
        opex_wallet_id="walletB",
    )

    assert result["status"] == "GREEN"
    assert result["conservation_pct"] >= 95.0
    assert result["yield_pct"] >= 99.0
    assert result["leakage_pct"] == pytest.approx(89.58, rel=1e-2)


def test_triple_engine_wallet_separation_red():
    engine = TripleEngine()
    result = engine.evaluate_cycle(
        reported_kwh=60.0,
        token_kwh=59.9,
        actual_revenue_mwk=96000.0,
        expected_revenue_mwk=95840.0,
        opex_mwk=10000.0,
        gross_mwk=96000.0,
        revenue_wallet_id="walletA",
        opex_wallet_id="walletA",
    )

    assert result["status"] == "RED"
    assert "Wallets are merged" in result["reason"]


def test_gatekeeper_reconcile_yellow_threshold():
    gate = Gatekeeper()
    expected = 95840.0
    status = gate.reconcile(91472.0, expected)  # 95.46% score
    assert status == AssetStatus.UNLOCKED

    status = gate.reconcile(90000.0, expected)  # 93.97% score
    assert status == AssetStatus.LOCKED

    status = gate.reconcile(70000.0, expected)  # 27.0% score
    assert status == AssetStatus.BLOCKED


def test_gatekeeper_fiscal_incident_on_blocked():
    gate = Gatekeeper()
    status = gate.reconcile(
        cash_collected_mwk=70000.0,
        expected_revenue_mwk=95840.0,
        site_id="MILL001",
        conservation_score=70.0,
        opex_mwk=10000.0,
        gross_mwk=96000.0,
    )

    assert status == AssetStatus.BLOCKED
    assert len(gate.fiscal_incident_log) == 1

    incident = gate.fiscal_incident_log[0]
    assert incident["site_id"] == "MILL001"
    assert incident["score"] < 80.0
    assert incident["reason"] == "Physics/Yield Mismatch Detected"
    assert incident["payload"]["conservation_score"] == 70.0
    assert incident["payload"]["leakage_ratio"] == pytest.approx(0.1041666667, rel=1e-5)


def test_fiduciary_lock_error_on_blocked_cycle():
    # cheaper mock: simulate by calling Gatekeeper directly and evaluate map in reconcile_cycle
    from backend.core_engine import Gatekeeper

    # There is no DB seeding here; we only validate the logic path in issue_token guard.
    with pytest.raises(FiduciaryLockError):
        issue_token(
            mill_id="UNKNOWN",
            token_id="T1",
            units_kwh=50.0,
            cost_mwk=80000.0,
            revenue_wallet_id="walletA",
            opex_wallet_id="walletB",
        )


def test_cycle_model_wallet_metadata():
    cycle = Cycle(
        mill_id="MILL01",
        token_id="TK100",
        revenue_wallet_id="WAL-REV-01",
        opex_wallet_id="WAL-OPX-01",
        integrity_score=99.5,
        cycle_start=datetime.now(timezone.utc),
        cycle_end=datetime.now(timezone.utc),
        total_usage_kwh=100.0,
        total_actual_cash=120000.0,
        expected_revenue=119000.0,
        variance=1000.0,
        status="RECONCILED",
        audit_summary="Test cycle",
    )

    assert cycle.revenue_wallet_id == "WAL-REV-01"
    assert cycle.opex_wallet_id == "WAL-OPX-01"
    assert cycle.integrity_score == 99.5


def test_wallet_lineage_integration():
    create_db_and_tables()

    with Session(engine) as session:
        rev_wallet = Wallet(id="WAL-REV-01", name="Revenue Wallet", wallet_type="revenue")
        opex_wallet = Wallet(id="WAL-OPX-01", name="OpEx Wallet", wallet_type="opex")
        session.add_all([rev_wallet, opex_wallet])

        token = TokenPurchase(
            token_id="TK-999",
            mill_id="MILL01",
            units_kwh=50,
            cost_mwk=80000,
            revenue_wallet_id="WAL-REV-01",
            opex_wallet_id="WAL-OPX-01",
        )
        session.add(token)

        cycle = Cycle(
            mill_id="MILL01",
            token_id="TK-999",
            revenue_wallet_id="WAL-REV-01",
            opex_wallet_id="WAL-OPX-01",
            integrity_score=99.0,
            cycle_start=datetime.now(timezone.utc),
            cycle_end=datetime.now(timezone.utc),
            total_usage_kwh=49.0,
            total_actual_cash=78000.0,
            expected_revenue=78400.0,
            variance=-400.0,
            status="RECONCILED",
            audit_summary="Test cycle lineage",
        )
        session.add(cycle)
        session.commit()

        lineage = WalletLineage(
            cycle_id=cycle.id,
            token_id="TK-999",
            from_wallet_id="WAL-REV-01",
            to_wallet_id="WAL-OPX-01",
            integrity_score=99.0,
            reason="Initial custody trace",
        )
        session.add(lineage)
        session.commit()

        loaded = session.get(WalletLineage, lineage.id)
        assert loaded is not None
        assert loaded.from_wallet_id == "WAL-REV-01"
        assert loaded.to_wallet_id == "WAL-OPX-01"

        # Immutable lineage: update should be rejected by event listener.
        loaded.reason = "Modified"
        with pytest.raises(ValueError):
            session.commit()


def test_wallet_lineage_direct_insert_not_allowed():
    create_db_and_tables()
    with Session(engine) as session:
        rev_wallet = Wallet(id="WAL-REV-02", name="Revenue Wallet", wallet_type="revenue")
        opex_wallet = Wallet(id="WAL-OPX-02", name="OpEx Wallet", wallet_type="opex")
        session.add_all([rev_wallet, opex_wallet])
        session.commit()

        lineage = WalletLineage(
            cycle_id=None,
            token_id=None,
            from_wallet_id="WAL-REV-02",
            to_wallet_id="WAL-OPX-02",
            integrity_score=50.0,
            reason="Manual insert attempt",
            created_by_reconcile=False,
        )
        session.add(lineage)
        with pytest.raises(Exception):
            session.commit()


def test_identity_manager_verify_and_replay():
    public_key_hex, private_key_hex = IdentityManager.generate_keypair()
    payload = {"mill_id": "MILL01", "nonce": "001"}
    signature_b64 = IdentityManager.sign_payload(payload, private_key_hex)

    payload_string_different_order = '{"nonce":"001","mill_id":"MILL01"}'

    assert IdentityManager.verify_event(payload, signature_b64, public_key_hex)
    assert IdentityManager.verify_event(payload_string_different_order, signature_b64, public_key_hex)

    assert IdentityManager.compute_payload_hash(payload) == sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode("utf-8")).hexdigest()

    tampered_payload = {"mill_id": "MILL01", "nonce": "002"}
    with pytest.raises(IdentityError):
        IdentityManager.verify_event(tampered_payload, signature_b64, public_key_hex)

    assert IdentityManager.verify_nonce("002", "001")
    with pytest.raises(ReplayError):
        IdentityManager.verify_nonce("001", "002")


def test_event_ingest_with_signature_and_replay():
    create_db_and_tables()

    with Session(engine) as session:
        mill = Mill(id="MILL01", name="Mill 1", location="X", meter_type="type", efficiency_baseline=1000.0)
        operator = Operator(operator_id="OP01", name="Op1", phone="000", mill_id="MILL01")

        pk, sk = IdentityManager.generate_keypair()
        operator.public_key = pk
        session.add_all([mill, operator])
        session.commit()

    payload = json.dumps({"mill_id":"MILL01","nonce":"0001","reading":50})
    signature_b64 = IdentityManager.sign_payload(payload, sk)

    event = ingest_event("MILL01", "OP01", payload, signature_b64)
    assert event.status == "VERIFIED"

    # Ghost simulation: same signature with modified reading should be rejected.
    modified_payload = json.dumps({"mill_id":"MILL01","nonce":"0002","reading":51})
    with pytest.raises(IdentityError):
        ingest_event("MILL01", "OP01", modified_payload, signature_b64)

    with pytest.raises(ReplayError):
        ingest_event("MILL01", "OP01", payload, signature_b64)


def test_authority_engine_gap_breach_and_constraints():
    create_db_and_tables()

    with Session(engine) as session:
        # set up role and manifest requiring no gap breach
        role = Role(role_id="MILL_OP", name="Mill Operator")
        session.add(role)
        session.commit()

        manifest = ConstraintManifest(
            role_id="MILL_OP",
            constraint_type="no_gap_breach",
            constraint_definition=json.dumps({"mismatch_tolerance": 0.0}),
            active=True,
        )
        session.add(manifest)

        mill = Mill(id="MILL01", name="Mill1", location="L", meter_type="type", efficiency_baseline=1000.0)
        operator = Operator(operator_id="OP01", name="Op1", phone="000", mill_id="MILL01", role_id="MILL_OP")
        session.add_all([mill, operator])
        session.commit()

    from backend.authority_engine import AuthorityEngine, GapBreachError

    with Session(engine) as session:
        session.add_all([
            # gap between reports by 5 kWh
            DailyReport(mill_id="MILL01", opening_kwh=100.0, closing_kwh=150.0, actual_cash=150000.0),
            DailyReport(mill_id="MILL01", opening_kwh=156.0, closing_kwh=210.0, actual_cash=210000.0),
        ])
        session.commit()

    with pytest.raises(GapBreachError):
        AuthorityEngine.evaluate_operator_action("OP01", "reconcile_cycle", {"mill_id": "MILL01"})


def test_rbac_forbidden_force_unlock_for_operator():
    create_db_and_tables()

    with Session(engine) as session:
        role = Role(role_id="OPERATOR", name="Operator")
        session.add(role)
        session.commit()

        perm = RolePermission(role_id="OPERATOR", action="SUBMIT_REPORT", permitted=True)
        session.add(perm)

        op = Operator(operator_id="OP99", name="Op99", phone="000", mill_id="MILL01", role_id="OPERATOR")
        session.add(op)

        site = Mill(id="MILL01", name="Mill1", location="X", meter_type="type", efficiency_baseline=1000.0)
        session.add(site)

        session.commit()

    from backend.authority_engine import AuthorityEngine

    with pytest.raises(AuthorityError):
        AuthorityEngine.evaluate_operator_action("OP99", "FORCE_UNLOCK", {"mill_id": "MILL01"})


def test_yield_ceiling_violation_blocks():
    create_db_and_tables()

    with Session(engine) as session:
        role = Role(role_id="OPERATOR", name="Operator")
        session.add(role)
        session.commit()

        role_perm = RolePermission(role_id="OPERATOR", action="SUBMIT_REPORT", permitted=True)
        session.add(role_perm)

        site_phys = SitePhysicsConstraint(site_id="MILL01", max_yield_per_kwh=2500.0, min_yield_per_kwh=800.0, max_opex_percentage=0.2)
        session.add(site_phys)

        op = Operator(operator_id="OP02", name="Op2", phone="000", mill_id="MILL01", role_id="OPERATOR")
        session.add(op)

        site = Mill(id="MILL01", name="Mill1", location="X", meter_type="type", efficiency_baseline=1000.0)
        session.add(site)

        session.commit()

    from backend.authority_engine import AuthorityEngine

    with pytest.raises(AuthorityError):
        AuthorityEngine.evaluate_operator_action(
            "OP02",
            "SUBMIT_REPORT",
            {"mill_id": "MILL01", "reported_cash": 7000.0, "reported_kwh": 2.0, "meter_open": 10.0, "meter_close": 12.0, "opex_mwk": 1000.0, "gross_mwk": 4000.0},
        )


def test_leakage_cap_requires_manager():
    create_db_and_tables()

    with Session(engine) as session:
        role = Role(role_id="OPERATOR", name="Operator")
        session.add(role)
        session.commit()

        role_perm = RolePermission(role_id="OPERATOR", action="SUBMIT_REPORT", permitted=True)
        session.add(role_perm)

        site_phys = SitePhysicsConstraint(site_id="MILL01", max_yield_per_kwh=4000.0, min_yield_per_kwh=800.0, max_opex_percentage=0.2)
        session.add(site_phys)

        op = Operator(operator_id="OP03", name="Op3", phone="000", mill_id="MILL01", role_id="OPERATOR")
        session.add(op)

        site = Mill(id="MILL01", name="Mill1", location="X", meter_type="type", efficiency_baseline=1000.0)
        session.add(site)

        session.commit()

    from backend.authority_engine import AuthorityEngine

    with pytest.raises(AuthorityError):
        AuthorityEngine.evaluate_operator_action(
            "OP03",
            "SUBMIT_REPORT",
            {"mill_id": "MILL01", "reported_cash": 1000.0, "reported_kwh": 10.0, "meter_open": 20.0, "meter_close": 30.0, "opex_mwk": 2500.0, "gross_mwk": 10000.0},
        )


def test_synthetic_fraud_detection():
    create_db_and_tables()

    with Session(engine) as session:
        site = Mill(id="MILL01", name="Mill1", location="X", meter_type="type", efficiency_baseline=1000.0)
        session.add(site)

        op = Operator(operator_id="OP05", name="Op5", phone="000", mill_id="MILL01", role_id="MANAGER")
        session.add(op)

        role = Role(role_id="MANAGER", name="Manager")
        session.add(role)
        session.commit()

        role_perm = RolePermission(role_id="MANAGER", action="SUBMIT_REPORT", permitted=True)
        session.add(role_perm)

        site_phys = SitePhysicsConstraint(site_id="MILL01", max_yield_per_kwh=2500.0, min_yield_per_kwh=800.0, max_opex_percentage=0.2)
        session.add(site_phys)
        session.commit()

    from backend.consistency_engine import ConsistencyEngine

    # 10 varying reports
    for i in range(10):
        payload = {"reported_cash": 1000.0 + i * 10, "reported_kwh": 1.0 + i * 0.1, "opex_mwk": 100.0 + i * 2}
        profile = ConsistencyEngine.update_profile("OP05", payload["reported_cash"] / payload["reported_kwh"], payload["opex_mwk"])

    # 11th perfectly consistent report with low variance
    payload = {"reported_cash": 1200.0, "reported_kwh": 1.2, "opex_mwk": 120.0}
    report = ConsistencyEngine.calculate_suspicion_score(payload, profile)

    assert report.is_synthetic_fraud or report.score >= 50


def test_daily_recon_window_lock():
    create_db_and_tables()

    with Session(engine) as session:
        site = Mill(id="MILL01", name="Mill1", location="X", meter_type="type", efficiency_baseline=1000.0)
        session.add(site)
        session.commit()

    from backend.reconciliation_engine import ReconciliationEngine
    import pytest

    future_time = datetime.now(timezone.utc) + timedelta(hours=1)
    with pytest.raises(ValueError):
        ReconciliationEngine.run_daily_recon(
            mill_id="MILL01",
            physical_reading=100.0,
            start_time=future_time - timedelta(days=1),
            end_time=future_time,
        )


def test_daily_recon_with_events():
    create_db_and_tables()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)

    with Session(engine) as session:
        site = Mill(id="MILL01", name="Mill1", location="X", meter_type="type", efficiency_baseline=1000.0)
        session.add(site)

        op = Operator(operator_id="OP06", name="Op6", phone="000", mill_id="MILL01")
        session.add(op)

        session.commit()

        # Add verified events in the window
        for i in range(3):
            payload = json.dumps({"reported_kwh": 10.0, "reported_cash": 10000.0, "nonce": str(i)})
            event = EventLog(
                mill_id="MILL01",
                operator_id="OP06",
                payload_json=payload,
                payload_hash="hash_" + str(i),
                signature="sig_" + str(i),
                prev_hash="",
                status="VERIFIED",
                event_time=start + timedelta(hours=6 + i),
            )
            session.add(event)

        session.commit()

    from backend.reconciliation_engine import ReconciliationEngine

    recon = ReconciliationEngine.run_daily_recon(
        mill_id="MILL01",
        physical_reading=150.0,
        start_time=start,
        end_time=now,
    )

    assert recon["event_count"] == 3
    assert recon["reported_kwh"] == 30.0
    assert recon["total_cash"] == 30000.0
    assert recon["root_hash"] != "NO_EVENTS"


def test_generate_audit_certificate():
    create_db_and_tables()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)

    with Session(engine) as session:
        site = Mill(id="MILL01", name="Mill1", location="X", meter_type="type", efficiency_baseline=1000.0)
        session.add(site)
        session.commit()

    from backend.reconciliation_engine import ReconciliationEngine

    record = ReconciliationEngine.store_reconciliation(
        mill_id="MILL01",
        physical_reading=200.0,
        start_time=start,
        end_time=now,
    )

    certificate = ReconciliationEngine.generate_audit_certificate("MILL01", now)
    assert "MILL01" in certificate
    assert "Reconciliation Status" in certificate
    assert record.root_hash in certificate


def test_trust_scorecard_daily():
    create_db_and_tables()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)

    with Session(engine) as session:
        site = Mill(id="MILL01", name="Mkwinda Mill", location="Mkwinda", meter_type="Inhemeter", efficiency_baseline=1600.0)
        session.add(site)

        op = Operator(operator_id="OP07", name="Op7", phone="000", mill_id="MILL01")
        session.add(op)
        session.commit()

        # Add verified events
        for i in range(5):
            payload = json.dumps({"reported_kwh": 10.0 + i, "reported_cash": 16000.0 + i * 100, "nonce": str(i)})
            event = EventLog(
                mill_id="MILL01",
                operator_id="OP07",
                payload_json=payload,
                payload_hash="hash_" + str(i),
                signature="sig_" + str(i),
                prev_hash="",
                status="VERIFIED",
                event_time=start + timedelta(hours=6 + i),
            )
            session.add(event)
        session.commit()

    from backend.reconciliation_engine import ReconciliationEngine
    from backend.trust_scorecard import TrustScorecardGenerator

    ReconciliationEngine.store_reconciliation(
        mill_id="MILL01",
        physical_reading=180.0,
        start_time=start,
        end_time=now,
    )

    generator = TrustScorecardGenerator("MILL01")
    scorecard = generator.generate_daily_scorecard(now)

    assert scorecard["kpis"]["trust_integrity_score"] >= 0
    assert scorecard["kpis"]["trust_integrity_score"] <= 100
    assert scorecard["metadata"]["reconciliation_status"] in ["SOVEREIGN", "UNDER_REVIEW"]
    assert scorecard["investor_verdict"]


def test_trust_scorecard_range():
    create_db_and_tables()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=3)

    with Session(engine) as session:
        site = Mill(id="MILL02", name="Mkwinda Mill", location="Mkwinda", meter_type="Inhemeter", efficiency_baseline=1600.0)
        session.add(site)
        session.commit()

    from backend.reconciliation_engine import ReconciliationEngine
    from backend.trust_scorecard import TrustScorecardGenerator

    for i in range(3):
        current_start = start + timedelta(days=i)
        current_end = current_start + timedelta(days=1)
        ReconciliationEngine.store_reconciliation(
            mill_id="MILL02",
            physical_reading=100.0 + i * 10,
            start_time=current_start,
            end_time=current_end,
        )

    generator = TrustScorecardGenerator("MILL02")
    range_scorecard = generator.generate_scorecard_range(start, now)

    assert range_scorecard["period"]["days_reported"] == 3
    assert "average_trust_score" in range_scorecard["aggregated_metrics"]
    assert "trend" in range_scorecard["aggregated_metrics"]


def test_trust_scorecard_markdown_format():
    create_db_and_tables()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)

    with Session(engine) as session:
        site = Mill(id="MILL01", name="Mkwinda Mill", location="Mkwinda", meter_type="Inhemeter", efficiency_baseline=1600.0)
        session.add(site)
        session.commit()

    from backend.reconciliation_engine import ReconciliationEngine
    from backend.trust_scorecard import TrustScorecardGenerator

    ReconciliationEngine.store_reconciliation(
        mill_id="MILL01",
        physical_reading=150.0,
        start_time=start,
        end_time=now,
    )

    generator = TrustScorecardGenerator("MILL01")
    scorecard = generator.generate_daily_scorecard(now)
    report = generator.format_investor_report(scorecard)

    assert "GridLedger Trust Scorecard" in report
    assert "Mkwinda Mill" in report
    assert "SOVEREIGN" in report or "STABLE" in report or "CAUTION" in report or "WARNING" in report
    assert "Cryptographic Anchor" in report


def test_capital_impact_sovereign_trust():
    """Test capital impact for high-trust (90+) asset."""
    from backend.trust_scorecard import TrustScorecardGenerator

    generator = TrustScorecardGenerator("MILL01")
    capital = generator.calculate_capital_impact(trust_score=95.0, variance_pct=0.8)

    # Sovereign status should get rate reduction of -5%
    assert capital["financing_rate_adjustment_pct"] == -5.0
    assert capital["financing_rate_adjustment_bps"] == -500

    # Should be institutional grade
    assert capital["risk_classification"] == "INSTITUTIONAL GRADE"
    assert capital["capital_tier"] == "Tier 1"
    assert capital["max_leverage_ratio"] == 3.5

    # Low variance should accelerate payback
    assert capital["payback_acceleration"] == "4 Months Faster"
    assert capital["months_faster_recovery"] == 4

    # Audit cost reduction for sovereign status
    assert "60% Reduction" in capital["audit_efficiency"]


def test_capital_impact_medium_trust():
    """Test capital impact for medium-trust (75-89) asset."""
    from backend.trust_scorecard import TrustScorecardGenerator

    generator = TrustScorecardGenerator("MILL01")
    capital = generator.calculate_capital_impact(trust_score=80.0, variance_pct=1.5)

    # Medium trust should get rate reduction of -2.5%
    assert capital["financing_rate_adjustment_pct"] == -2.5
    assert capital["financing_rate_adjustment_bps"] == -250

    # Should be commercial
    assert capital["risk_classification"] == "COMMERCIAL"
    assert capital["capital_tier"] == "Tier 2"
    assert capital["max_leverage_ratio"] == 2.5

    # Medium variance = 2 months acceleration
    assert capital["payback_acceleration"] == "2 Months Faster"

    # Audit reduction should be 30%
    assert "30% Reduction" in capital["audit_efficiency"]


def test_capital_impact_low_trust():
    """Test capital impact for low-trust (60-74) asset."""
    from backend.trust_scorecard import TrustScorecardGenerator

    generator = TrustScorecardGenerator("MILL01")
    capital = generator.calculate_capital_impact(trust_score=65.0, variance_pct=3.0)

    # Low trust gets smaller reduction
    assert capital["financing_rate_adjustment_pct"] == -1.0
    assert capital["financing_rate_adjustment_bps"] == -100

    # Should be subprime
    assert capital["risk_classification"] == "SUBPRIME"
    assert capital["capital_tier"] == "Tier 3"
    assert capital["max_leverage_ratio"] == 1.5

    # High variance = no payback acceleration
    assert capital["payback_acceleration"] == "Neutral"
    assert capital["months_faster_recovery"] == 0


def test_capital_impact_high_risk():
    """Test capital impact for high-risk (<60) asset."""
    from backend.trust_scorecard import TrustScorecardGenerator

    generator = TrustScorecardGenerator("MILL01")
    capital = generator.calculate_capital_impact(trust_score=40.0, variance_pct=5.0)

    # High risk gets rate premium (positive)
    assert capital["financing_rate_adjustment_pct"] == 0.5
    assert capital["financing_rate_adjustment_bps"] == 50

    # Highest risk tier
    assert capital["risk_classification"] == "HIGH RISK"
    assert capital["capital_tier"] == "Tier 4"
    assert capital["max_leverage_ratio"] == 1.0

    # Recommendation should suggest decline
    assert "DECLINE" in capital["recommendation"]


def test_capital_impact_basis_points_calculation():
    """Test that basis points calculation includes all components."""
    from backend.trust_scorecard import TrustScorecardGenerator

    generator = TrustScorecardGenerator("MILL01")
    capital = generator.calculate_capital_impact(trust_score=92.0, variance_pct=0.5)

    # Basis points should include: rate (-500) + audit (60% = ~30) + payback (4mo = 40)
    # Total should be approximately -500 + 30 + 40 = -430
    expected_bps = -500 + (0.6 * 50) + (4 * 10)
    assert capital["estimated_annual_savings_bps"] == int(expected_bps)


def test_capital_recommendation_logic():
    """Test capital investment recommendation generation."""
    from backend.trust_scorecard import TrustScorecardGenerator

    generator = TrustScorecardGenerator("MILL01")

    # Sovereign scenario
    sovereign = generator.calculate_capital_impact(91.0, 0.8)
    assert "APPROVE" in sovereign["recommendation"]
    assert "growth capital" in sovereign["recommendation"].lower()

    # Standard scenario
    stable = generator.calculate_capital_impact(78.0, 1.5)
    assert "APPROVE" in stable["recommendation"]
    assert "Standard" in stable["recommendation"] or "quarterly" in stable["recommendation"].lower()

    # Conditional scenario
    conditional = generator.calculate_capital_impact(65.0, 2.5)
    assert "CONDITIONAL" in conditional["recommendation"]

    # Decline scenario
    decline = generator.calculate_capital_impact(45.0, 4.5)
    assert "DECLINE" in decline["recommendation"]


def test_integrity_report_90_days():
    now = datetime.now(timezone.utc)
    entries = [
        GoldZoneEntry(date=now - timedelta(days=10), meter_id="A", within_variance=True, deviation_pct=1.0),
        GoldZoneEntry(date=now - timedelta(days=95), meter_id="B", within_variance=False, deviation_pct=10.0),
    ]
    report = IntegrityReportAPI.generate(entries)
    assert report["total_entries"] == 1
    assert report["in_gold_zone"] == 1


# ── Merkle Root Tests ─────────────────────────────────────────────────────────
# These three tests validate the upgraded reconciliation_engine.py which now
# computes a Merkle root over ALL verified events in the window instead of
# hashing only the last event.  This means any deletion, insertion, or
# reordering of events will produce a different root — detectable by an auditor.

def test_merkle_root_empty_window_returns_sentinel():
    """
    A reconciliation window with zero VERIFIED events must return the
    well-known sentinel MERKLE_EMPTY rather than a hash or NO_EVENTS.
    This lets callers distinguish "nothing happened" from a real chain.
    """
    create_db_and_tables()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)

    with Session(engine) as session:
        site = Mill(id="MILL_MERKLE_EMPTY", name="Merkle Empty Mill",
                    location="X", meter_type="type", efficiency_baseline=1000.0)
        session.add(site)
        session.commit()

    from backend.reconciliation_engine import ReconciliationEngine

    recon = ReconciliationEngine.run_daily_recon(
        mill_id="MILL_MERKLE_EMPTY",
        physical_reading=0.0,
        start_time=start,
        end_time=now,
    )

    assert recon["root_hash"] == "MERKLE_EMPTY", (
        f"Expected sentinel 'MERKLE_EMPTY' for empty window, got: {recon['root_hash']}"
    )
    assert recon["event_count"] == 0
    assert recon["merkle_depth"] == 0


def test_merkle_root_is_deterministic():
    """
    Running reconciliation twice over the same event window must produce
    the identical Merkle root both times.  Non-determinism here would
    make the cryptographic anchor useless for auditing.
    """
    create_db_and_tables()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)

    with Session(engine) as session:
        site = Mill(id="MILL_MERKLE_DET", name="Merkle Det Mill",
                    location="X", meter_type="type", efficiency_baseline=1000.0)
        op = Operator(operator_id="OP_DET", name="Op Det",
                      phone="000", mill_id="MILL_MERKLE_DET")
        session.add_all([site, op])
        session.commit()

        for i in range(4):
            payload = json.dumps({
                "reported_kwh": 12.0 + i,
                "reported_cash": 19200.0 + i * 100,
                "nonce": f"det_{i}",
            })
            event = EventLog(
                mill_id="MILL_MERKLE_DET",
                operator_id="OP_DET",
                payload_json=payload,
                payload_hash=f"hash_det_{i}",
                signature=f"sig_det_{i}",
                prev_hash="",
                status="VERIFIED",
                event_time=start + timedelta(hours=4 + i),
            )
            session.add(event)
        session.commit()

    from backend.reconciliation_engine import ReconciliationEngine

    recon_a = ReconciliationEngine.run_daily_recon(
        mill_id="MILL_MERKLE_DET",
        physical_reading=100.0,
        start_time=start,
        end_time=now,
    )
    recon_b = ReconciliationEngine.run_daily_recon(
        mill_id="MILL_MERKLE_DET",
        physical_reading=100.0,
        start_time=start,
        end_time=now,
    )

    assert recon_a["root_hash"] == recon_b["root_hash"], (
        "Merkle root is non-deterministic — same window produced two different roots."
    )
    assert recon_a["root_hash"] not in ("MERKLE_EMPTY", "NO_EVENTS")
    assert recon_a["merkle_depth"] > 0


def test_merkle_root_changes_when_event_deleted():
    """
    The core forensic guarantee: if any event is removed from the window
    after the root was computed, re-running reconciliation must produce a
    DIFFERENT root.  This is what makes deletion detectable by an auditor.
    """
    create_db_and_tables()

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=1)

    with Session(engine) as session:
        site = Mill(id="MILL_MERKLE_DEL", name="Merkle Del Mill",
                    location="X", meter_type="type", efficiency_baseline=1000.0)
        op = Operator(operator_id="OP_DEL", name="Op Del",
                      phone="000", mill_id="MILL_MERKLE_DEL")
        session.add_all([site, op])
        session.commit()

        for i in range(5):
            payload = json.dumps({
                "reported_kwh": 10.0 + i,
                "reported_cash": 16000.0 + i * 200,
                "nonce": f"del_{i}",
            })
            event = EventLog(
                mill_id="MILL_MERKLE_DEL",
                operator_id="OP_DEL",
                payload_json=payload,
                payload_hash=f"hash_del_{i}",
                signature=f"sig_del_{i}",
                prev_hash="",
                status="VERIFIED",
                event_time=start + timedelta(hours=3 + i),
            )
            session.add(event)
        session.commit()

        all_events = session.exec(
            select(EventLog).where(EventLog.mill_id == "MILL_MERKLE_DEL")
        ).all()
        event_hashes = [e.payload_hash for e in all_events]

    from backend.reconciliation_engine import ReconciliationEngine

    # Root with all 5 events
    recon_full = ReconciliationEngine.run_daily_recon(
        mill_id="MILL_MERKLE_DEL",
        physical_reading=200.0,
        start_time=start,
        end_time=now,
    )
    root_full = recon_full["root_hash"]

        # Delete one event (simulates a bad actor removing evidence)
    # We use a bulk delete (session.execute(delete(...))) to bypass the ORM 'before_delete'
    # hook that prevents standard session.delete(event) for security.
    with Session(engine) as session:
        statement = delete(EventLog).where(EventLog.payload_hash == event_hashes[2])
        session.execute(statement)
        session.commit()


    # Root with 4 events — must differ
    recon_reduced = ReconciliationEngine.run_daily_recon(
        mill_id="MILL_MERKLE_DEL",
        physical_reading=200.0,
        start_time=start,
        end_time=now,
    )
    root_reduced = recon_reduced["root_hash"]

    assert root_full != root_reduced, (
        "SECURITY FAILURE: Merkle root did not change after an event was deleted. "
        "Deletion is undetectable — the forensic anchor is broken."
    )
    assert recon_full["event_count"] == 5
    assert recon_reduced["event_count"] == 4