import sqlite3

DB = "data/gridledger.db"
conn = sqlite3.connect(DB)
cur = conn.cursor()

# Get cycle count and status distribution for NABIWI
cur.execute("""
    SELECT status, COUNT(*) as count, 
           AVG(ABS(variance)) as avg_variance,
           COUNT(CASE WHEN ABS(variance) <= 5 THEN 1 END) as clean_count
    FROM cycle
    WHERE mill_id = 'NABIWI'
    GROUP BY status
""")

print("Cycle Status Distribution for NABIWI:")
print("-" * 70)
for row in cur.fetchall():
    print(f"Status: {row[0]:12} | Total: {row[1]:4} | Avg Variance: {row[2]:6.2f}% | Clean (≤5%): {row[3]:4}")

# Get total counts
cur.execute("""
    SELECT COUNT(*) as total,
           COUNT(CASE WHEN status = 'SEALED' THEN 1 END) as sealed,
           COUNT(CASE WHEN ABS(variance) <= 5 THEN 1 END) as clean_all,
           COUNT(CASE WHEN status = 'SEALED' AND ABS(variance) <= 5 THEN 1 END) as sealed_clean
    FROM cycle
    WHERE mill_id = 'NABIWI'
""")

row = cur.fetchone()
print("\n" + "=" * 70)
print(f"Total cycles:        {row[0]}")
print(f"Sealed cycles:       {row[1]}")
print(f"Clean cycles (all):  {row[2]}")
print(f"Sealed + clean:      {row[3]}")
print("=" * 70)

conn.close()
