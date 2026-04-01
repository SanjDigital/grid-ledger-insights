import os
import sys
from datetime import datetime
from sqlmodel import Session, select

# Enable module loading from workspace root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.init_db import engine, Mill, TokenPurchase
from scripts.init_db import Wallet
from backend.cycle_manager import reconcile_cycle, can_purchase_token


def parse_receipt_timestamp(receipt_ts: str) -> datetime:
    # Receipt timestamp format: 'DD/MM/YYYY HH:MM:SS'
    return datetime.strptime(receipt_ts, '%d/%m/%Y %H:%M:%S')


def add_token(receipt_no: str, meter_id: str, units: float, cost: float, timestamp: str):
    parsed_ts = parse_receipt_timestamp(timestamp)
    iso_ts = parsed_ts.isoformat(sep=' ')
    effective_price = cost / units if units > 0 else None
    revenue_wallet_id = f"WALLET_REV_{meter_id}"
    opex_wallet_id = f"WALLET_OPEX_{meter_id}"

    with Session(engine) as session:
        mill = session.get(Mill, meter_id)
        if not mill:
            print(f"⚠️ Warning: Mill {meter_id} not found in Mill table. Proceeding with token record.")

        # Ensure required wallets exist (TokenPurchase has NOT NULL wallet IDs).
        if session.get(Wallet, revenue_wallet_id) is None:
            session.add(Wallet(id=revenue_wallet_id, name=f"Revenue Wallet {meter_id}", wallet_type="revenue"))
        if session.get(Wallet, opex_wallet_id) is None:
            session.add(Wallet(id=opex_wallet_id, name=f"OpEx Wallet {meter_id}", wallet_type="opex"))

        # low-level token cycle lock check
        if not can_purchase_token(meter_id):
            print(f"🔒 Cannot issue token yet: previous cycle is not reconciled for {meter_id}.")

        existing = session.exec(select(TokenPurchase).where(TokenPurchase.token_id == receipt_no)).one_or_none()

        if existing:
            print(f"🔁 Upsert: Found existing receipt {receipt_no}, updating values.")
            existing.units_kwh = units
            existing.cost_mwk = cost
            existing.purchase_date = parsed_ts
            existing.mill_id = meter_id
            session.add(existing)
        else:
            token = TokenPurchase(
                token_id=receipt_no,
                mill_id=meter_id,
                units_kwh=units,
                cost_mwk=cost,
                revenue_wallet_id=revenue_wallet_id,
                opex_wallet_id=opex_wallet_id,
                purchase_date=parsed_ts,
            )
            session.add(token)
            print(f"✅ Added TokenPurchase {receipt_no} for mill {meter_id}.")

        session.commit()

    cycle_info = reconcile_cycle(meter_id)
    print(f"🔗 Chain-of-Integrity link for token {receipt_no}: {cycle_info.get('status')}")

    print(f"📊 Effective price per kWh: {effective_price:.2f} MWK")
    print(f"🕒 Timestamp stored as: {iso_ts}")
    return {
        'receipt_no': receipt_no,
        'meter_id': meter_id,
        'units': units,
        'cost': cost,
        'effective_price': effective_price,
        'timestamp': iso_ts,
        'upserted': True,
        'cycle_status': cycle_info.get('status'),
        'variance': cycle_info.get('variance'),
    }


if __name__ == '__main__':
    # Data from Patrick's receipt
    receipt = '592152026031381201737'
    meter = '37154345799'
    units = 59.9
    cost = 20000
    ts = '14/03/2026 15:00:00'

    result = add_token(receipt, meter, units, cost, ts)
    print(result)
