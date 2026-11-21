"""Local-only administrator password recovery. No public recovery endpoint."""
import argparse
from getpass import getpass
from sqlalchemy import select
from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.db.session import make_database
from app.models.entities import User, AuditLog
from app.schemas.contracts import PasswordInput


def reset_admin(settings: Settings, username: str, password: str):
    settings.validate_secret()
    data = PasswordInput(password=password)
    engine, factory = make_database(settings.database_url)
    try:
        with factory() as db:
            user = db.scalar(select(User).where(User.username == username.lower()))
            if user is None or not user.is_admin:
                raise ValueError("Administrator not found; ordinary users will not be promoted")
            if verify_password(data.password, user.hashed_password):
                raise ValueError("Choose a password different from the current password")
            user.hashed_password = hash_password(data.password)
            user.token_version += 1
            user.must_change_password = False
            db.add(AuditLog(actor_id=user.id, actor_name=user.username,
                            action="reset_admin_password_cli", target=f"user:{user.id}"))
            db.commit()
    finally:
        engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Reset an existing administrator password locally")
    parser.add_argument("--username", default="admin")
    args = parser.parse_args()
    password = getpass("New password (10+ characters; input is hidden): ")
    confirmation = getpass("Confirm new password: ")
    if password != confirmation:
        raise SystemExit("Passwords do not match; nothing changed")
    try:
        reset_admin(Settings(), args.username, password)
    except ValueError as error:
        raise SystemExit(str(error))
    print("Administrator password updated. Use your new password to sign in. Old sessions are invalid.")


if __name__ == "__main__":
    main()
