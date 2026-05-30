import sqlite3, hashlib

conn = sqlite3.connect('data/gridledger.db')
cursor = conn.cursor()

cursor.execute('SELECT * FROM cycle WHERE id = 1')
row = cursor.fetchone()
cols = [d[0] for d in cursor.description]
record = dict(zip(cols, row))

print('=== CYCLE 1 — FULL RECORD ===')
for k, v in record.items():
    print(f'  {k}: {v}')

print()

seal_fields = [
    'mill_id', 'cycle_start', 'cycle_end',
    'total_usage_kwh', 'total_actual_cash',
    'expected_revenue', 'previous_seal'
]
values = [str(record.get(f, '') or '') for f in seal_fields]
payload = '|'.join(values)
computed_seal = hashlib.sha256(payload.encode()).hexdigest()

print('=== SEAL COMPUTATION ===')
print(f'  Algorithm: SHA-256')
print(f'  Fields (in order): {" | ".join(seal_fields)}')
print(f'  Values: {" | ".join(values)}')
print(f'  Computed seal: {computed_seal}')
print(f'  Stored seal:   {record.get("cycle_seal")}')
print(f'  Match: {computed_seal == record.get("cycle_seal")}')
conn.close()