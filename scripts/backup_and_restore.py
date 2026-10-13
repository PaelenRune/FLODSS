"""Database Backup, Integrity Check, and Restore Utility for FLODSS.

Usage:
    python scripts/backup_and_restore.py backup
    python scripts/backup_and_restore.py verify <backup_file>
    python scripts/backup_and_restore.py restore <backup_file>
"""

import os
import sys
import sqlite3
import argparse
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB = BASE_DIR / "data" / "flodss_research.db"
BACKUP_DIR = BASE_DIR / "data" / "backups"


def perform_backup(source_db: Path = DEFAULT_DB, target_dir: Path = BACKUP_DIR) -> Path:
    """Create a verified SQLite online backup."""
    if not source_db.exists():
        raise FileNotFoundError(f"Source database not found: {source_db}")

    target_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = target_dir / f"flodss_backup_{ts}.db"

    source_conn = sqlite3.connect(source_db)
    backup_conn = sqlite3.connect(backup_path)

    print(f"[BACKUP] Backing up '{source_db}' -> '{backup_path}'...")
    source_conn.backup(backup_conn)
    backup_conn.close()
    source_conn.close()

    # Integrity verification
    verify_conn = sqlite3.connect(backup_path)
    cur = verify_conn.execute("PRAGMA integrity_check;")
    result = cur.fetchone()[0]
    verify_conn.close()

    if result.lower() != "ok":
        backup_path.unlink(missing_ok=True)
        raise RuntimeError(f"Backup failed integrity check: {result}")

    print(f"[SUCCESS] Verified backup created ({backup_path.stat().st_size:,} bytes).")
    return backup_path


def restore_backup(backup_file: Path, target_db: Path = DEFAULT_DB) -> bool:
    """Restore a database from a validated backup file."""
    if not backup_file.exists():
        raise FileNotFoundError(f"Backup file not found: {backup_file}")

    # Check backup integrity before restoring
    test_conn = sqlite3.connect(backup_file)
    cur = test_conn.execute("PRAGMA integrity_check;")
    check = cur.fetchone()[0]
    test_conn.close()

    if check.lower() != "ok":
        raise RuntimeError(f"Cannot restore corrupt backup: {check}")

    # Restore to target
    target_db.parent.mkdir(parents=True, exist_ok=True)
    dest_conn = sqlite3.connect(target_db)
    src_conn = sqlite3.connect(backup_file)

    print(f"[RESTORE] Restoring from '{backup_file}' -> '{target_db}'...")
    src_conn.backup(dest_conn)
    src_conn.close()
    dest_conn.close()

    print("[SUCCESS] Database restored and ready for operations.")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FLODSS Database Maintenance Utility")
    subparsers = parser.add_subparsers(dest="action", required=True)

    backup_parser = subparsers.add_parser("backup", help="Create a live database backup")
    restore_parser = subparsers.add_parser("restore", help="Restore database from backup file")
    restore_parser.add_argument("backup_file", type=Path, help="Path to backup .db file")

    args = parser.parse_args()

    if args.action == "backup":
        perform_backup()
    elif args.action == "restore":
        restore_backup(args.backup_file)
