from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Session
from scripts.init_db import engine, OperatorProfile


@dataclass
class SuspicionReport:
    operator_id: str
    z_score_yield: float
    z_score_opex: float
    score: float
    is_synthetic_fraud: bool
    is_outlier: bool
    details: str


class ConsistencyEngine:
    @staticmethod
    def update_profile(operator_id: str, new_yield: float, new_opex: float) -> OperatorProfile:
        with Session(engine) as session:
            profile = session.get(OperatorProfile, operator_id)
            if profile is None:
                profile = OperatorProfile(operator_id=operator_id)

            profile.n_reports += 1

            # Welford update for yield
            delta_yield = new_yield - profile.mean_yield
            profile.mean_yield += delta_yield / profile.n_reports
            delta2_yield = new_yield - profile.mean_yield
            profile.m2_yield += delta_yield * delta2_yield

            # Welford update for opex
            delta_opex = new_opex - profile.mean_opex
            profile.mean_opex += delta_opex / profile.n_reports
            delta2_opex = new_opex - profile.mean_opex
            profile.m2_opex += delta_opex * delta2_opex

            profile.updated_at = datetime.now(timezone.utc)

            session.add(profile)
            session.commit()
            session.refresh(profile)

            return profile

    @staticmethod
    def calculate_suspicion_score(payload: dict, profile: OperatorProfile) -> SuspicionReport:
        reported_cash = float(payload.get("reported_cash", 0.0))
        # Support ingestion payloads that use "reading" as an alias for kWh.
        reported_kwh_val = payload.get("reported_kwh", None)
        if reported_kwh_val is None:
            reported_kwh_val = payload.get("reading", 0.0)
        reported_kwh = float(reported_kwh_val)
        opex = float(payload.get("opex_mwk", 0.0))

        if reported_kwh <= 0:
            raise ValueError("reported_kwh must be greater than 0")

        current_yield = reported_cash / reported_kwh

        # variance must be computed from accumulated M2
        yield_variance = (profile.m2_yield / (profile.n_reports - 1)) if profile.n_reports > 1 else 0.0
        opex_variance = (profile.m2_opex / (profile.n_reports - 1)) if profile.n_reports > 1 else 0.0

        yield_std = yield_variance ** 0.5
        opex_std = opex_variance ** 0.5

        z_yield = 0.0
        z_opex = 0.0

        if yield_std > 0:
            z_yield = (current_yield - profile.mean_yield) / yield_std
        if opex_std > 0:
            z_opex = (opex - profile.mean_opex) / opex_std

        score = 0.0
        details = []

        # outlier detection
        if abs(z_yield) > 2.5:
            score += 20
            details.append("yield_outlier")
        if abs(z_opex) > 2.5:
            score += 20
            details.append("opex_outlier")

        # Synthetic fraud detection:
        # If the stream has enough samples and the relative variability is low,
        # a "too-perfect" next report is treated as potentially synthetic.
        synthetic = False
        if profile.n_reports >= 5:
            yield_cv = (yield_std / abs(profile.mean_yield)) if profile.mean_yield else float("inf")
            opex_cv = (opex_std / abs(profile.mean_opex)) if profile.mean_opex else float("inf")
            if yield_cv < 0.35 and opex_cv < 0.25:
                synthetic = True
                score += 50
                details.append("synthetic_low_variance")

        return SuspicionReport(
            operator_id=profile.operator_id,
            z_score_yield=z_yield,
            z_score_opex=z_opex,
            score=score,
            is_synthetic_fraud=synthetic,
            is_outlier=abs(z_yield) > 2.5 or abs(z_opex) > 2.5,
            details=",".join(details) if details else "normal",
        )
