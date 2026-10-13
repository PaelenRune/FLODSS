"""Rotate or assign a strong administrator password in the FLODSS SQLite database.

Usage:
    python scripts/rotate_admin_credentials.py [--email admin@university.edu] [--password CustomStrongPassword123!]
If no password is provided, a cryptographically secure 24-character password will be automatically generated.
"""

import argparse
import os
import secrets
import string
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.core.security import hash_password
from app.db.database import db_manager
from app.services.auth_service import AuthService, _now_iso


def generate_strong_password(length: int = 24) -> str:
    """Generate a high-entropy random password with mixed character sets."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*()-_=+" for c in pwd)
        ):
            return pwd


def main():
    parser = argparse.ArgumentParser(description="Rotate FLODSS Administrator Credentials")
    parser.add_argument("--email", type=str, default=None, help="Admin email address (defaults to current admin email)")
    parser.add_argument("--password", type=str, default=None, help="New admin password (generated if omitted)")
    parser.add_argument(
        "--secret-file",
        type=str,
        default=str(backend_dir / "data" / ".admin_credentials.secret"),
        help="Path to save credentials securely (default: backend/data/.admin_credentials.secret)",
    )
    parser.add_argument(
        "--mask-output",
        action="store_true",
        help="Do not display the plaintext password in stdout (writes only to secret-file)",
    )
    args = parser.parse_args()

    db_manager.run_migrations()
    with db_manager.get_connection() as conn:
        AuthService.ensure_admin_user(conn)

        # Retrieve existing admin
        cursor = conn.execute("SELECT id, email, full_name FROM users WHERE role = 'ADMIN' LIMIT 1;")
        row = cursor.fetchone()
        if not row:
            print("[ERROR] No administrator user found in database.")
            sys.exit(1)

        admin_id = row["id"]
        current_email = row["email"]
        target_email = (args.email or current_email).strip().lower()
        new_password = args.password or generate_strong_password()

        hashed = hash_password(new_password)
        now = _now_iso()

        # Update user record
        conn.execute(
            """
            UPDATE users
            SET email = ?, hashed_password = ?, updated_at = ?
            WHERE id = ?;
            """,
            (target_email, hashed, now, admin_id),
        )

        # Terminate any active sessions for security
        conn.execute("UPDATE sessions SET is_revoked = 1 WHERE user_id = ?;", (admin_id,))
        conn.commit()

        # Write to secret file
        secret_path = Path(args.secret_file)
        secret_path.parent.mkdir(parents=True, exist_ok=True)
        secret_content = (
            f"# FLODSS CONFIDENTIAL ADMINISTRATOR CREDENTIALS\n"
            f"# Generated: {now}\n"
            f"# KEEP THIS FILE CONFIDENTIAL - NEVER COMMIT TO GIT OR SHARE IN CHAT/LOGS\n"
            f"FLODSS_ADMIN_EMAIL={target_email}\n"
            f"FLODSS_ADMIN_PASSWORD={new_password}\n"
        )
        with open(secret_path, "w", encoding="utf-8") as sf:
            sf.write(secret_content)

        print("======================================================================")
        print("FLODSS ADMINISTRATOR CREDENTIALS SUCCESSFULLY UPDATED")
        print("======================================================================")
        print(f"  Admin User ID : {admin_id}")
        print(f"  Email         : {target_email}")
        if args.mask_output:
            print(f"  New Password  : [PROTECTED - Saved securely to {secret_path}]")
        else:
            print(f"  New Password  : {new_password}")
        print(f"  Secret File   : {secret_path}")
        print(f"  Database Path : {db_manager.db_path}")
        print("  Active Sessions: All revoked (clean security boundary).")
        print("======================================================================")
        print("IMPORTANT: The password is saved in the local secret file above.")
        print("Store these credentials in a private password manager and do not expose them.")


if __name__ == "__main__":
    main()
