"""CLI utility to generate single-use invitation links for researchers and advisors."""

import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from app.core.config import settings
from app.db.database import db_manager
from app.models.auth import UserRole
from app.services.auth_service import AuthService


def main():
    parser = argparse.ArgumentParser(description="Create single-use invitation token for FLODSS pilot")
    parser.add_argument("--email", type=str, required=True, help="Invited researcher / advisor email address")
    parser.add_argument(
        "--role",
        type=str,
        default="RESEARCHER",
        choices=["RESEARCHER", "VIEWER", "ADMIN"],
        help="Assigned role (default: RESEARCHER)",
    )
    args = parser.parse_args()

    target_email = args.email.strip().lower()
    target_role = UserRole(args.role)

    db_manager.run_migrations()
    with db_manager.get_connection() as conn:
        AuthService.ensure_admin_user(conn)

        # Retrieve admin ID
        cur = conn.execute("SELECT id FROM users WHERE role = 'ADMIN' LIMIT 1;")
        row = cur.fetchone()
        if not row:
            print("[ERROR] Administrator account not found in database.")
            sys.exit(1)
        admin_id = row["id"]

        inv = AuthService.create_invitation(
            created_by_user_id=admin_id,
            email=target_email,
            role=target_role,
            conn=conn,
        )

        print("======================================================================")
        print("FLODSS RESEARCHER INVITATION GENERATED")
        print("======================================================================")
        print(f"  Davet Edilen E-posta : {inv.email}")
        print(f"  Rol                  : {inv.role}")
        print(f"  Geçerlilik Süresi    : {settings.INVITATION_EXPIRE_HOURS} saat")
        print(f"  Davetiye Token'ı     : {inv.token}")
        print("----------------------------------------------------------------------")
        print("  Yerel Kayıt Linki (Localhost):")
        print(f"    http://127.0.0.1:8000/?invitation={inv.token}")
        print("----------------------------------------------------------------------")
        print("  Tünel Aktifken Gönderilecek Link:")
        print(f"    https://<TUNEL-ADRESINIZ>.trycloudflare.com/?invitation={inv.token}")
        print("======================================================================")
        print("Bu linki davet ettiğiniz kişiye iletiniz. Linke tıkladığında adını ve")
        print("kendi parolasını belirleyerek hesabını anında etkinleştirecektir.")


if __name__ == "__main__":
    main()
