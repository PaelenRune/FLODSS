import sqlite3
from pathlib import Path

def inspect_db(path_str):
    p = Path(path_str)
    if not p.exists():
        print(f"DB not found: {path_str}")
        return
    conn = sqlite3.connect(p)
    cursor = conn.cursor()
    tables = [r[0] for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    print(f"=== Database: {path_str} (Size: {p.stat().st_size} bytes) ===")
    for t in ["users", "invitations", "sessions", "research_projects", "audit_events"]:
        if t in tables:
            count = cursor.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
            print(f"  {t}: {count} rows")
    conn.close()

print("PRODUCTION DATABASE:")
inspect_db("data/flodss_research.db")

print("\nISOLATED TEST DATABASE:")
inspect_db("data/test_flodss.db")
