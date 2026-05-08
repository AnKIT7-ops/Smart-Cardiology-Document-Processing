"""Check what data exists in the shared database."""
import sys
import sqlite3

sys.stdout.reconfigure(encoding="utf-8")

conn = sqlite3.connect("smart_cardiology.db")
conn.row_factory = sqlite3.Row

# List all tables
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print("=" * 60)
print("  DATABASE CONTENTS AUDIT")
print("=" * 60)

for (tname,) in tables:
    rows = conn.execute(f"SELECT * FROM [{tname}]").fetchall()
    print(f"\n{tname}: {len(rows)} row(s)")
    for r in rows[:3]:
        d = dict(r)
        # Truncate long values
        for k, v in d.items():
            if isinstance(v, str) and len(v) > 60:
                d[k] = v[:60] + "..."
        print(f"  → {d}")

conn.close()
print("\n" + "=" * 60)
