"""Small management CLI.

Usage: python -m app.manage create-owner [--email X] [--password Y] [--name Z]
"""
import argparse
import getpass
import sys

from app.auth import hash_password
from app.config import get_settings
from app.db import SessionLocal
from app.models import AppUser


def create_owner(email: str | None, password: str | None, name: str | None) -> None:
    settings = get_settings()
    email = email or settings.owner_email
    if not password:
        password = getpass.getpass("Owner password: ")
    name = name or "Owner"
    db = SessionLocal()
    try:
        existing = db.query(AppUser).first()
        if existing is not None:
            print(
                f"An owner already exists ({existing.email}); updating its credentials.",
                file=sys.stderr,
            )
            existing.email = email
            existing.password_hash = hash_password(password)
            existing.display_name = name
        else:
            db.add(AppUser(email=email, password_hash=hash_password(password), display_name=name))
        db.commit()
        print(f"Owner ready: {email}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-owner")
    p.add_argument("--email")
    p.add_argument("--password")
    p.add_argument("--name")
    args = parser.parse_args()
    if args.cmd == "create-owner":
        create_owner(args.email, args.password, args.name)


if __name__ == "__main__":
    main()
