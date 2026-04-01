import json
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional, List

from sqlmodel import Session, select

from scripts.init_db import engine, EventLog, ReconciliationRecord, Mill


class ReconError(Exception):
    pass


class ReconciliationEngine:

    @staticmethod
    def _compute_event_hash(event: EventLog) -> str:
        """Hash a single event: SHA256(payload_json + signature)."""
        combined = f"{event.payload_json}:{event.signature}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_merkle_root(hashes: List[str]) -> str:
        """
        Compute a Merkle root over a list of hex-encoded SHA256 hashes.

        Properties:
        - Every event in the window contributes to the root.
        - Deleting, inserting, or reordering any event produces a
          different root — the auditor can detect it.
        - An empty window returns the well-known empty sentinel so
          callers can distinguish "no events" from a real hash.

        Algorithm (standard binary Merkle tree):
        1. Start with leaf hashes (one per event, ordered by event_time).
        2. Pair adjacent hashes and hash each pair together.
        3. If the level has an odd number of nodes, duplicate the last
           node (standard Bitcoin/RFC convention).
        4. Repeat until one root hash remains.
        """
        if not hashes:
            return "MERKLE_EMPTY"

        # Work on a mutable copy; ensure we always have bytes to hash
        level = list(hashes)

        while len(level) > 1:
            next_level = []
            # Pad to even length by duplicating the last node
            if len(level) % 2 == 1:
                level.append(level[-1])
            for i in range(0, len(level), 2):
                combined = level[i] + level[i + 1]
                parent = hashlib.sha256(combined.encode("utf-8")).hexdigest()
                next_level.append(parent)
            level = next_level

        return level[0]

    @classmethod
    def _build_event_merkle_root(cls, events: List[EventLog]) -> str:
        """
        Build a Merkle root from a list of EventLog rows.

        Each leaf = SHA256(payload_json + ":" + signature).
        Events must already be ordered by event_time ascending so the
        root is deterministic for a given window.
        """
        leaf_hashes = [cls._compute_event_hash(e) for e in events]
        return cls._compute_merkle_root(leaf_hashes)

    @classmethod
    def run_daily_recon(
        cls,
        mill_id: str,
        physical_reading: float,
        start_time: datetime,
        end_time: datetime,
        tolerance_pct: float = 2.0,
    ) -> Dict:
        """
        Reconcile a 24-hour window of events against a physical meter reading.

        The root_hash is now a Merkle root over ALL verified events in the
        window (ordered by event_time), not just the last event.  This means:
        - Deleting any event changes the root.
        - Inserting a synthetic event changes the root.
        - Reordering events changes the root.
        An auditor can re-derive the root from the raw EventLog and compare.

        Returns:
            Dict with reconciliation results including merkle_root, status,
            variance, and a new merkle_depth field for auditability.

        Raises:
            ValueError if end_time is in the future (window lock).
            ReconError if mill does not exist.
        """
        current_time = datetime.now(timezone.utc)
        if end_time > current_time:
            raise ValueError(
                f"Cannot reconcile future window: "
                f"end_time={end_time} > current_time={current_time}"
            )

        with Session(engine) as session:
            mill = session.get(Mill, mill_id)
            if not mill:
                raise ReconError(f"Mill {mill_id} not found")

            prev_recon = session.exec(
                select(ReconciliationRecord)
                .where(ReconciliationRecord.mill_id == mill_id)
                .order_by(ReconciliationRecord.end_time.desc())
            ).first()

            previous_reading = prev_recon.physical_reading if prev_recon else 0.0
            physical_consumed = physical_reading - previous_reading

            # Fetch ALL verified events in window, ordered for deterministic Merkle
            events = session.exec(
                select(EventLog)
                .where(
                    EventLog.mill_id == mill_id,
                    EventLog.status == "VERIFIED",
                    EventLog.event_time >= start_time,
                    EventLog.event_time < end_time,
                )
                .order_by(EventLog.event_time)
            ).all()

            total_reported_kwh = 0.0
            total_cash = 0.0
            event_count = 0

            for event in events:
                try:
                    payload = json.loads(event.payload_json)
                    total_reported_kwh += float(payload.get("reported_kwh", 0.0))
                    total_cash += float(payload.get("reported_cash", 0.0))
                    event_count += 1
                except Exception:
                    pass

            # ── Merkle root over the full event window ────────────────────
            # Every event contributes — deletion or insertion is detectable.
            root_hash = cls._build_event_merkle_root(events)
            merkle_depth = (event_count - 1).bit_length() if event_count > 1 else 0

            # ── Variance & status ─────────────────────────────────────────
            delta = abs(physical_consumed - total_reported_kwh)
            variance_pct = (
                (delta / physical_consumed * 100) if physical_consumed > 0 else 0.0
            )
            status = "SOVEREIGN" if variance_pct <= tolerance_pct else "UNDER_REVIEW"

            # ── Energy Accountability Ratio (EAR) & Verified Throughput (VT) ──
            # EAR = reported_kwh / metered_kwh, clipped to [0, 1]
            # VT = metered_kwh * EAR
            metered_kwh = physical_consumed
            if metered_kwh > 0:
                ear = min(1.0, max(0.0, total_reported_kwh / metered_kwh))
            else:
                ear = 0.0
            vt = metered_kwh * ear

            yield_per_kwh = (
                total_cash / total_reported_kwh if total_reported_kwh > 0 else 0.0
            )

            return {
                "mill_id": mill_id,
                "start_time": start_time,
                "end_time": end_time,
                "physical_kwh": physical_consumed,
                "reported_kwh": total_reported_kwh,
                "variance_pct": variance_pct,
                "total_cash": total_cash,
                "yield_per_kwh": yield_per_kwh,
                "status": status,
                "event_count": event_count,
                "root_hash": root_hash,          # now a full Merkle root
                "merkle_depth": merkle_depth,     # tree depth for audit info
                "previous_reading": previous_reading,
                "current_reading": physical_reading,
                "energy_accountability_ratio": ear,  # EAR: accountability of reported vs metered
                "verified_throughput": vt,  # VT: deterministic coupling of EAR with metered
            }

    @classmethod
    def store_reconciliation(
        cls,
        mill_id: str,
        physical_reading: float,
        start_time: datetime,
        end_time: datetime,
        tolerance_pct: float = 2.0,
    ) -> ReconciliationRecord:
        result = cls.run_daily_recon(
            mill_id, physical_reading, start_time, end_time, tolerance_pct
        )

        with Session(engine) as session:
            record = ReconciliationRecord(
                mill_id=mill_id,
                timestamp=datetime.now(timezone.utc),
                start_time=start_time,
                end_time=end_time,
                physical_reading=physical_reading,
                physical_consumed=result["physical_kwh"],
                reported_kwh=result["reported_kwh"],
                variance_pct=result["variance_pct"],
                status=result["status"],
                event_count=result["event_count"],
                total_cash=result["total_cash"],
                root_hash=result["root_hash"],
                energy_accountability_ratio=result["energy_accountability_ratio"],
                verified_throughput=result["verified_throughput"],
            )
            session.add(record)
            session.commit()
            session.refresh(record)

        return record

    @classmethod
    def generate_audit_certificate(cls, mill_id: str, date: datetime) -> str:
        with Session(engine) as session:
            record = session.exec(
                select(ReconciliationRecord)
                .where(
                    ReconciliationRecord.mill_id == mill_id,
                    # Match reconciliation records by the day their end_time occurred.
                    # (Tests store windows that start the previous day.)
                    ReconciliationRecord.end_time
                    >= date.replace(hour=0, minute=0, second=0, microsecond=0),
                    ReconciliationRecord.end_time
                    < date.replace(hour=0, minute=0, second=0, microsecond=0)
                    + timedelta(days=1),
                )
            ).first()

            if not record:
                return f"No reconciliation record found for {mill_id} on {date.date()}"

            effective_yield = (
                record.total_cash / record.reported_kwh
                if record.reported_kwh > 0
                else 0
            )

            certificate = f"""
# GridLedger Audit Certificate

**Mill**: {record.mill_id}
**Date**: {date.date()}
**Report Generated**: {record.timestamp.isoformat()}

## Period
- Start: {record.start_time.isoformat()}
- End:   {record.end_time.isoformat()}

## Physical Readings
- Previous Reading:  0.0  (reference)
- Current Reading:   {record.physical_reading} kWh
- Physical Consumed: {record.physical_consumed} kWh

## Reported Energy
- Total Reported: {record.reported_kwh} kWh
- Total Cash:     {record.total_cash:,.0f} MWK
- Effective Yield:{effective_yield:,.2f} MWK/kWh

## Reconciliation Status
- Variance:    {record.variance_pct:.2f}%
- Status:      {record.status}
- Event Count: {record.event_count}

## Cryptographic Anchor
- Merkle Root: {record.root_hash}

### What this root proves
The Merkle root is computed over ALL {record.event_count} verified event(s)
in this reconciliation window, ordered by event_time.  Any deletion,
insertion, or reordering of events will produce a different root.
An auditor can independently re-derive this value from the raw EventLog.

---
*This certificate anchors physical energy consumption to the full*
*Merkle hash tree of the digital ledger for this period.*
"""
            return certificate.strip()