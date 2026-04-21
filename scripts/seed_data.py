from sqlmodel import Session, create_engine, select
from init_db import Mill, Operator, TariffRate, engine
from datetime import datetime, timezone

def seed_mills():
    # Operational Directive: All assets utilize Inhemeter (37-prefix) hardware.
    # Standard verification command for all site audits: Code 003.
    # CRITICAL: revenue_rate_per_kwh is what operator charges customers, NOT what owner pays ESCOM
    mills = [
        Mill(
            id="37154345799", 
            name="Patrick", 
            location="Mkwinda", 
            meter_type="Inhemeter", 
            efficiency_baseline=1600.0,
            revenue_rate_per_kwh=1600.0  # Customer-facing rate for Mkwinda site
        ),
        Mill(
            id="37154367942", 
            name="Ganizani", 
            location="Chankhuntha", 
            meter_type="Inhemeter", 
            efficiency_baseline=1200.0,
            revenue_rate_per_kwh=1200.0  # Customer-facing rate
        ),
        Mill(
            id="37154463253", 
            name="Jeremiah", 
            location="Nayere", 
            meter_type="Inhemeter", 
            efficiency_baseline=1350.0,
            revenue_rate_per_kwh=1350.0  # Customer-facing rate
        ),
        Mill(
            id="37134859091", 
            name="Ruby", 
            location="Area 18", 
            meter_type="Inhemeter", 
            efficiency_baseline=1300.0,
            revenue_rate_per_kwh=1300.0  # Customer-facing rate
        ),
        Mill(
            id="37134002601", 
            name="Anthony", 
            location="Area 36", 
            meter_type="Inhemeter", 
            efficiency_baseline=1500.0,
            revenue_rate_per_kwh=1500.0  # Customer-facing rate
        ),
        Mill(
            id="NABIWI_NRID",
            name="NABIWI",
            location="Nabiwi Mill Site",
            meter_type="Inhemeter",
            efficiency_baseline=1350.0,
            revenue_rate_per_kwh=1350.0  # Nabiwi customer-facing rate
        )
    ]

    with Session(engine) as session:
        for mill in mills:
            statement = select(Mill).where(Mill.id == mill.id)
            existing = session.exec(statement).first()
            if existing:
                # Update existing mill
                existing.name = mill.name
                existing.location = mill.location
                existing.meter_type = mill.meter_type
                existing.efficiency_baseline = mill.efficiency_baseline
                print(f"Updated mill: {mill.id}")
            else:
                session.add(mill)
                print(f"Added mill: {mill.id}")
        session.commit()
    print("✅ Sites seeded with efficiency baselines.")


def seed_operators():
    operators = [
        Operator(operator_id="OP_001", name="Patrick", phone="+265999000001", mill_id="37154345799"),
        Operator(operator_id="OP_002", name="Ganizani", phone="+265999000002", mill_id="37154367942"),
        Operator(operator_id="OP_003", name="Jeremiah", phone="+265999000003", mill_id="37154463253"),
        Operator(operator_id="OP_004", name="Ruby", phone="+265999000004", mill_id="37134859091"),
        Operator(operator_id="OP_005", name="Anthony", phone="+265999000005", mill_id="37134002601"),
    ]

    with Session(engine) as session:
        for op in operators:
            statement = select(Operator).where(Operator.operator_id == op.operator_id)
            existing = session.exec(statement).first()
            if existing:
                existing.name = op.name
                existing.phone = op.phone
                existing.mill_id = op.mill_id
                print(f"Updated operator: {op.operator_id}")
            else:
                session.add(op)
                print(f"Added operator: {op.operator_id}")
        session.commit()
    print("✅ Operators seeded.")


def seed_tariff_rates():
    """
    Seed historical tariff rates.
    
    Critical: MERA tariff schedule for ET7 (three-phase, general, prepaid):
    - K253.70 until 2026-01-19 (legacy rate)
    - K284.15 effective 2026-01-19 (MERA Jan 2026 adjustment +12%)
    """
    mill_ids = ["37154345799", "37154367942", "37154463253", "37134859091", "37134002601", "NABIWI_NRID"]
    
    rates = []
    
    # Historical rate (pre-Jan 19, 2026)
    for mill_id in mill_ids:
        rates.append(TariffRate(
            mill_id=mill_id,
            rate_mk_per_kwh=253.70,
            effective_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            set_by="GRIDLEDGER_SYSTEM",
            notes="MERA ET7 rate before Jan 2026 adjustment"
        ))
    
    # New rate effective Jan 19, 2026 (MERA announcement)
    for mill_id in mill_ids:
        rates.append(TariffRate(
            mill_id=mill_id,
            rate_mk_per_kwh=284.15,
            effective_date=datetime(2026, 1, 19, tzinfo=timezone.utc),
            set_by="GRIDLEDGER_SYSTEM",
            notes="MERA Jan 2026 ET7 tariff adjustment (three-phase prepaid): +12.0% to 284.15 Mk/kWh"
        ))
    
    with Session(engine) as session:
        for rate in rates:
            # Check if rate already exists for this mill and effective_date
            statement = select(TariffRate).where(
                (TariffRate.mill_id == rate.mill_id) &
                (TariffRate.effective_date == rate.effective_date)
            )
            existing = session.exec(statement).first()
            if existing:
                print(f"Tariff rate already exists for {rate.mill_id} effective {rate.effective_date}")
            else:
                session.add(rate)
                print(f"Added tariff rate for {rate.mill_id}: {rate.rate_mk_per_kwh} Mk/kWh effective {rate.effective_date.date()}")
        session.commit()
    print("✅ Tariff rates seeded.")


if __name__ == "__main__":
    seed_mills()
    seed_operators()
    seed_tariff_rates()