from sqlmodel import Session, create_engine, select
from init_db import Mill, Operator, engine

def seed_mills():
    # Operational Directive: All assets utilize Inhemeter (37-prefix) hardware.
    # Standard verification command for all site audits: Code 003.
    mills = [
        Mill(
            id="37154345799", 
            name="Patrick", 
            location="Mkwinda", 
            meter_type="Inhemeter", 
            efficiency_baseline=1600.0
        ),
        Mill(
            id="37154367942", 
            name="Ganizani", 
            location="Chankhuntha", 
            meter_type="Inhemeter", 
            efficiency_baseline=1200.0
        ),
        Mill(
            id="37154463253", 
            name="Jeremiah", 
            location="Nayere", 
            meter_type="Inhemeter", 
            efficiency_baseline=1350.0
        ),
        Mill(
            id="37134859091", 
            name="Ruby", 
            location="Area 18", 
            meter_type="Inhemeter", 
            efficiency_baseline=1300.0
        ),
        Mill(
            id="37134002601", 
            name="Anthony", 
            location="Area 36", 
            meter_type="Inhemeter", 
            efficiency_baseline=1500.0
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


if __name__ == "__main__":
    seed_mills()
    seed_operators()