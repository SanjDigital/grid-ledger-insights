from sqlmodel import Session, select
from scripts.init_db import Mill, TokenPurchase, DailyReport, engine

with Session(engine) as session:
    print('Mills:')
    mills = session.exec(select(Mill)).all()
    for mill in mills:
        print(f'  {mill.id}: {mill.name} at {mill.location}, baseline: {mill.efficiency_baseline}')
    
    print('\nToken Purchases:')
    purchases = session.exec(select(TokenPurchase)).all()
    for p in purchases:
        print(f'  {p.token_id}: {p.units_kwh} kWh for {p.mill_id}, cost: {p.cost_mwk} MWK')
    
    print('\nDaily Reports:')
    reports = session.exec(select(DailyReport)).all()
    for r in reports:
        print(f'  ID {r.id}: {r.mill_id}, {r.opening_kwh} to {r.closing_kwh} kWh, cash: {r.actual_cash}')