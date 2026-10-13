"""Deactivate test/demo accounts and revoke legacy test sessions/invitations before pilot launch."""

import sqlite3
from pathlib import Path

DB_PATHS = [
    Path(__file__).resolve().parent.parent / "data" / "flodss_research.db",
    Path(__file__).resolve().parent.parent / "backend" / "data" / "flodss_research.db",
]


def clean_database(db_path: Path):
    if not db_path.exists():
        return

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # 1. Revoke all active sessions
    cur.execute("UPDATE sessions SET is_revoked = 1 WHERE is_revoked = 0;")
    revoked_sessions = cur.rowcount

    # 2. Revoke lingering unused test invitation tokens
    cur.execute("UPDATE invitations SET is_revoked = 1 WHERE is_revoked = 0;")
    revoked_invitations = cur.rowcount

    # 3. Deactivate all non-admin test accounts
    cur.execute("UPDATE users SET is_active = 0 WHERE role != 'ADMIN';")
    deactivated_users = cur.rowcount

    conn.commit()
    conn.close()

    print(f"[{db_path.name}] Sanitization complete:")
    print(f"  - Deactivated Test Users : {deactivated_users}")
    print(f"  - Revoked Active Sessions: {revoked_sessions}")
    print(f"  - Revoked Pending Invites: {revoked_invitations}")


def main():
    print("======================================================================")
    print("FLODSS PRE-PILOT SECURITY SANITIZATION")
    print("======================================================================")
    for p in DB_PATHS:
        clean_database(p)
    print("======================================================================")
    print("STATUS: All test accounts and sessions deactivated. Only ADMIN remains active.")


if __name__ == "__main__":
    main()
