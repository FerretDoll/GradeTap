"""Create an administrator on an explicitly selected, migrated database."""
from getpass import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import select

from app.api.auth_api import hasher
from app.db.models import Account
from app.db.session import SessionLocal


def main():
    email = TypeAdapter(EmailStr).validate_python(input("管理员邮箱: ").strip()).lower()
    password = getpass("密码（至少 8 位）: ")
    if len(password) < 8 or password != getpass("再次输入密码: "):
        raise SystemExit("密码确认失败")
    with SessionLocal() as db:
        if db.scalar(select(Account.id).where(Account.email == email)):
            raise SystemExit("邮箱已存在")
        db.add(Account(email=email, display_name="管理员", password_hash=hasher.hash(password),
                       account_status="active", platform_role="admin"))
        db.commit()


if __name__ == "__main__":
    main()
