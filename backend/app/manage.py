import argparse
import getpass
import re
import sys

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from .auth import hash_password
from .db import SessionLocal
from .models import StaffUser
from .security import check_production_config
from .seed import init_db


def create_admin(db: Session, username: str, password: str, display_name: str = "Administrator") -> StaffUser:
    username = username.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.-]{2,59}", username):
        raise ValueError("Login 3–60 belgidan iborat boʻlsin: lotin harflari, raqam, nuqta, tire yoki pastki chiziq.")
    if not 16 <= len(password) <= 1024 or not password.strip():
        raise ValueError("Parol 16–1024 belgidan iborat boʻlishi kerak.")
    if not display_name.strip() or len(display_name) > 120:
        raise ValueError("Ism 1–120 belgidan iborat boʻlishi kerak.")
    if db.query(StaffUser).filter(StaffUser.username == username).first():
        raise ValueError("Bu login mavjud. Mavjud hisob oʻzgartirilmadi; boshqa login tanlang.")
    user = StaffUser(username=username, password_hash=hash_password(password), role="admin",
                     display_name=display_name.strip(), is_demo=False)
    db.add(user)
    db.commit()
    return user


def main() -> None:
    parser = argparse.ArgumentParser(description="DoriIshonch xodimlarini serverdan boshqarish")
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-admin", help="Demo boʻlmagan administrator yaratish")
    create.add_argument("--username", required=True)
    create.add_argument("--display-name", default="Administrator")
    args = parser.parse_args()
    if not sys.stdin.isatty():
        parser.error("Parolni yashirin kiritish uchun interaktiv terminal kerak.")
    try:
        check_production_config()
        password = getpass.getpass("Yangi parol (kamida 16 belgi): ")
        if password != getpass.getpass("Parolni takrorlang: "):
            parser.error("Parollar mos emas.")
        init_db(seed_if_empty=False)
        with SessionLocal() as session:
            user = create_admin(session, args.username, password, args.display_name)
            print(f"Administrator yaratildi: {user.username}")
    except (ValueError, RuntimeError) as error:
        parser.error(str(error))
    except SQLAlchemyError:
        parser.error("Baza bilan ishlashda xato. Ulanish, sxema va login takrorlanmaganini tekshiring.")


if __name__ == "__main__":
    main()
