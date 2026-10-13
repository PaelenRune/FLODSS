"""Database manager and migration engine for FLODSS.

Supports SQLite for local single-node research prototyping and
standard SQL schema migrations compatible with PostgreSQL.
"""

import os
import sqlite3
from pathlib import Path
from typing import Generator, Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class DatabaseManager:
    """Manages database connection and migration executions."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.DATABASE_PATH
        # Ensure parent directory exists
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._migrated = False

    def get_connection(self) -> sqlite3.Connection:
        """Create and configure a database connection."""
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=False,
            timeout=30.0,
        )
        conn.row_factory = sqlite3.Row
        # Enable foreign key constraints in SQLite
        conn.execute("PRAGMA foreign_keys = ON;")
        # Enable WAL journal mode for high concurrency
        if self.db_path != ":memory:":
            conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def run_migrations(self, conn: Optional[sqlite3.Connection] = None):
        """Execute all SQL migrations in order."""
        should_close = False
        if conn is None:
            conn = self.get_connection()
            should_close = True

        try:
            # Migration tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            migration_files = sorted(MIGRATIONS_DIR.glob("*.sql"))
            for mig_file in migration_files:
                version = mig_file.name
                cursor = conn.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,))
                if cursor.fetchone() is None:
                    logger.info(f"Applying migration: {version}")
                    with open(mig_file, "r", encoding="utf-8") as f:
                        sql = f.read()
                    conn.executescript(sql)
                    conn.execute("INSERT INTO schema_migrations (version) VALUES (?)", (version,))
                    conn.commit()
            self._migrated = True
        finally:
            if should_close:
                conn.close()


db_manager = DatabaseManager()


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """FastAPI dependency for obtaining a database connection."""
    if not db_manager._migrated:
        db_manager.run_migrations()
    conn = db_manager.get_connection()
    try:
        yield conn
    finally:
        conn.close()
