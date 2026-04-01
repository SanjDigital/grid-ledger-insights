from scripts.init_db import engine, Cycle, TokenPurchase
from sqlmodel import Session, select

with Session(engine) as session:
    cycles = session.exec(select(Cycle).order_by(Cycle.reconciled_at.desc())).all()
    print('Cycle count:', len(cycles))
    for c in cycles[:5]:
        print(c.mill_id, c.status, c.variance, c.audit_summary)

    token = session.exec(select(TokenPurchase).where(TokenPurchase.token_id == '592152026031381201737')).first()
    print('Token exists:', token is not None)
