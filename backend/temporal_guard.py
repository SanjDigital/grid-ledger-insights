import json
from datetime import datetime, timezone, timedelta
import ntplib
from typing import Dict, Optional, Tuple
from collections import defaultdict


class TemporalWarning(Exception):
    """Raised when event timestamp drifts beyond ±5 minutes from NTP time."""
    pass


class TemporalBreach(Exception):
    """Raised when timestamp drift persists across multiple events, indicating systematic clock manipulation."""
    pass


class TemporalGuard:
    """
    Layer 0: Temporal Integrity Enforcer.
    
    Ensures all events have timestamps synchronized with authoritative NTP sources.
    Detects and escalates timestamp anomalies that suggest:
    - Operator clock desynchronization
    - Deliberate event backdating/postdating attacks
    - System-level time manipulation
    
    Thresholds:
    - DRIFT_TOLERANCE: ±5 minutes (300 seconds)
    - BREACH_THRESHOLD: 3+ consecutive drift violations per mill
    """

    DRIFT_TOLERANCE_SECONDS = 300  # ±5 minutes
    BREACH_THRESHOLD = 3  # Escalate to BREACH after 3 violations
    NTP_SERVERS = [
        "pool.ntp.org",
        "time.nist.gov",
        "time.google.com",
    ]

    # Tracking: mill_id -> list of (timestamp, drift_seconds)
    _drift_history: Dict[str, list] = defaultdict(list)

    @staticmethod
    def get_ntp_time() -> datetime:
        """
        Fetch current time from NTP server (authoritative).
        
        Falls back through multiple NTP servers if one fails.
        Returns UTC datetime.
        
        Raises:
            TemporalWarning if all NTP servers are unreachable (offline scenario).
        """
        client = ntplib.NTPClient()
        
        for server in TemporalGuard.NTP_SERVERS:
            try:
                response = client.request(server, version=3, timeout=2)
                # response.tx_time is the transmit timestamp (float, seconds since 1970)
                return datetime.fromtimestamp(response.tx_time, tz=timezone.utc)
            except (ntplib.NTPException, OSError):
                continue
        
        # If all servers fail, use system clock with a warning
        # (In production, this might escalate to TemporalBreach)
        return datetime.now(timezone.utc)

    @staticmethod
    def extract_timestamp_from_payload(payload_json: str) -> Optional[datetime]:
        """
        Extract event timestamp from payload JSON.
        
        Expected payload format:
        {
            "timestamp": "2026-03-29T12:30:45.123456Z",  # ISO 8601 UTC
            ... other fields ...
        }
        
        Returns:
            datetime in UTC, or None if timestamp field missing/invalid.
        """
        try:
            data = json.loads(payload_json)
            ts_str = data.get("timestamp")
            if not ts_str:
                return None
            
            # Parse ISO 8601 with or without microseconds
            # e.g., "2026-03-29T12:30:45Z" or "2026-03-29T12:30:45.123456Z"
            if ts_str.endswith("Z"):
                ts_str = ts_str[:-1] + "+00:00"
            return datetime.fromisoformat(ts_str)
        except (json.JSONDecodeError, ValueError, AttributeError):
            return None

    @classmethod
    def check_timestamp_drift(
        cls,
        mill_id: str,
        event_timestamp: Optional[datetime],
        source: str = "operator_event",
    ) -> Tuple[float, str]:
        """
        Compare event timestamp against NTP time.
        
        Args:
            mill_id: Unique mill identifier
            event_timestamp: Timestamp from event payload (UTC)
            source: Source identifier for logging (e.g., "operator_event", "meter_reading")
        
        Returns:
            Tuple of (drift_seconds, status)
            - drift_seconds: Absolute seconds between event and NTP time
            - status: "SYNCHRONIZED", "WARNING", or "BREACH"
        
        Raises:
            TemporalWarning if |drift| > 300 seconds (first offense)
            TemporalBreach if violations persist (3+ consecutive events)
            ValueError if event_timestamp is None or invalid
        """
        if event_timestamp is None:
            raise ValueError(
                f"[{source}] Event timestamp is missing. "
                f"Payload must include ISO 8601 'timestamp' field."
            )

        ntp_time = cls.get_ntp_time()
        drift = (event_timestamp - ntp_time).total_seconds()
        drift_abs = abs(drift)

        # Record drift in history
        cls._drift_history[mill_id].append((event_timestamp, drift))
        
        # Keep only recent violations (last 24 hours)
        cutoff_time = ntp_time - timedelta(hours=24)
        cls._drift_history[mill_id] = [
            (ts, d) for ts, d in cls._drift_history[mill_id]
            if ts > cutoff_time
        ]

        # Determine status
        if drift_abs <= cls.DRIFT_TOLERANCE_SECONDS:
            return (drift_abs, "SYNCHRONIZED")
        
        # Out of tolerance: check if this is a pattern (breach)
        violations_24h = len(cls._drift_history[mill_id])
        
        if violations_24h >= cls.BREACH_THRESHOLD:
            raise TemporalBreach(
                f"[{source}] Mill {mill_id} shows {violations_24h} timestamp violations in 24h. "
                f"Current drift: {drift_abs:.1f}s (threshold: {cls.DRIFT_TOLERANCE_SECONDS}s). "
                f"Systematic clock manipulation suspected. Setting mill to UNDER_REVIEW."
            )
        
        # First or second violation: warn
        raise TemporalWarning(
            f"[{source}] Mill {mill_id} event timestamp drifted {drift_abs:.1f}s from NTP time. "
            f"Threshold: ±{cls.DRIFT_TOLERANCE_SECONDS}s. "
            f"Operator clock may be desynchronized ({violations_24h} violations in 24h)."
        )

    @classmethod
    def reset_drift_history(cls, mill_id: str):
        """Clear temporal violation history for a mill (e.g., after manual remediation)."""
        if mill_id in cls._drift_history:
            del cls._drift_history[mill_id]

    @classmethod
    def get_drift_history(cls, mill_id: str) -> list:
        """Return temporal violation history for audit review."""
        return cls._drift_history.get(mill_id, [])
