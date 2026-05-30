import sqlite3

DB = "data/gridledger.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Get all SEALED cycles for NABIWI, ordered by cycle_start
cur.execute("""
    SELECT id, cycle_start, cycle_end, total_usage_kwh, total_actual_cash,
           expected_revenue, variance, status, cycle_seal
    FROM cycle
    WHERE mill_id = 'NABIWI' AND status = 'SEALED'
    ORDER BY cycle_start ASC
""")
rows = cur.fetchall()
conn.close()

print(f"Total SEALED cycles for NABIWI: {len(rows)}")

# Find the longest streak of clean cycles
# Clean = variance within ±5%, no null variance, status is SEALED
longest_streak = []
current_streak = []

for r in rows:
    var = r[6]
    if var is not None and abs(var) <= 5.0:
        current_streak.append(r)
    else:
        if len(current_streak) > len(longest_streak):
            longest_streak = current_streak
        current_streak = []

# Check final streak
if len(current_streak) > len(longest_streak):
    longest_streak = current_streak

print(f"Longest clean streak: {len(longest_streak)} cycles")

# Show the date range
if longest_streak:
    print(f"Date range: {longest_streak[0][1]} to {longest_streak[-1][2]}")
    # Print first 3 and last 3
    print("\nFirst 3 cycles:")
    for r in longest_streak[:3]:
        print(f"  ID {r[0]}: {r[1]} → {r[2]} | {r[3]} kWh | MWK {r[4]} | variance {r[6]}%")
    print("\nLast 3 cycles:")
    for r in longest_streak[-3:]:
        print(f"  ID {r[0]}: {r[1]} → {r[2]} | {r[3]} kWh | MWK {r[4]} | variance {r[6]}%")
