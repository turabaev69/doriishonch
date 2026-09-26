"""Xodimlar uchun kirish (login).

Xaridorlar uchun login YOʻQ: skanerlash anonim boʻlishi kerak (qoʻrqmasdan xabar berish uchun).
Login faqat xodimlar sahifalari uchun: inspektor paneli, bojxona, ishlab chiqaruvchi paneli, inspektor copiloti.

Token: HMAC-SHA256 bilan imzolangan "foydalanuvchi|rol|muddat" (JWT ga oʻxshash, qoʻshimcha kutubxonasiz).
Parollar PBKDF2-SHA256 bilan saqlanadi.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import StaffUser

router = APIRouter(prefix="/auth")
TOKEN_TTL = 12 * 3600
ROLE_LABEL = {"admin": "Administrator", "inspector": "Inspektor", "customs": "Bojxona xodimi",
              "manufacturer": "Ishlab chiqaruvchi"}

DEMO_USERS = [
    # username, password, role, display_name, manufacturer_id
    ("admin", "admin123", "admin", "Administrator", None),
    ("inspektor", "inspektor123", "inspector", "Farmatsevtika inspektori", None),
    ("bojxona", "bojxona123", "customs", "Bojxona xodimi", None),
    ("zarafshon", "zarafshon123", "manufacturer", "Zarafshon Demo Farm", 1),
]


def _secret() -> bytes:
    if settings.is_production and len(settings.secret_key) < 32:
        raise RuntimeError("Productionda SECRET_KEY kamida 32 belgi boʻlishi shart")
    if settings.secret_key:
        return settings.secret_key.encode()
    f = Path(__file__).resolve().parent.parent / ".secret"
    if not f.exists():
        f.write_text(secrets.token_hex(32))
        os.chmod(f, 0o600)
    return f.read_text().strip().encode()


def hash_password(pw: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt.encode(), 120_000).hex()
    return f"pbkdf2${salt}${dk}"


def check_password(pw: str, stored: str) -> bool:
    try:
        _, salt, _ = stored.split("$")
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(pw, salt), stored)


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def make_token(user: StaffUser) -> str:
    payload = _b64(json.dumps({"u": user.username, "r": user.role, "m": user.manufacturer_id,
                               "exp": int(time.time()) + TOKEN_TTL}).encode())
    sig = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}"


def read_token(token: str) -> dict | None:
    try:
        payload, sig = token.split(".")
        good = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(good, sig):
            return None
        data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
        return data if data["exp"] > time.time() else None
    except Exception:
        return None


def current_user(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict | None:
    if not authorization or not authorization.lower().startswith("bearer "):
        return None
    data = read_token(authorization.split(" ", 1)[1].strip())
    if data is None or not settings.is_production:
        return data
    user = db.query(StaffUser).filter(StaffUser.username == data["u"]).first()
    if user is None or user.is_demo:
        return None
    return {**data, "r": user.role, "m": user.manufacturer_id}


def require_role(*roles: str):
    def dep(user: dict | None = Depends(current_user)) -> dict:
        if not settings.auth_enabled and not settings.is_production:
            return {"u": "anon", "r": "admin", "m": None}
        if not user:
            raise HTTPException(401, "Kirish talab qilinadi (xodimlar uchun)")
        if user["r"] != "admin" and user["r"] not in roles:
            raise HTTPException(403, "Bu sahifa sizning rolingiz uchun emas")
        return user
    return dep


def seed_users(db: Session) -> None:
    if settings.is_production:
        return
    if db.query(StaffUser).count():
        return
    for username, pw, role, name, mid in DEMO_USERS:
        db.add(StaffUser(username=username, password_hash=hash_password(pw), role=role, display_name=name,
                         manufacturer_id=mid, is_demo=True))
    db.commit()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    username: str
    role: str
    role_label: str
    display_name: str
    manufacturer_id: int | None


@router.post("/login", response_model=LoginResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(StaffUser).filter(StaffUser.username == req.username.strip().lower()).first()
    if not user or (settings.is_production and user.is_demo) or not check_password(req.password, user.password_hash):
        raise HTTPException(401, "Login yoki parol notoʻgʻri")
    return LoginResponse(token=make_token(user), username=user.username, role=user.role,
                         role_label=ROLE_LABEL.get(user.role, user.role), display_name=user.display_name,
                         manufacturer_id=user.manufacturer_id)


@router.get("/me")
def me(user: dict | None = Depends(current_user)):
    if not user:
        raise HTTPException(401, "Kirilmagan")
    return {"username": user["u"], "role": user["r"], "role_label": ROLE_LABEL.get(user["r"], user["r"]),
            "manufacturer_id": user.get("m")}


@router.get("/demo-accounts")
def demo_accounts():
    """Hakamlar uchun demo hisoblar (production da oʻchiring: SHOW_DEMO_ACCOUNTS=false)."""
    if settings.is_production or not settings.show_demo_accounts:
        return []
    return [{"username": u, "password": p, "role": ROLE_LABEL[r]} for u, p, r, _, _ in DEMO_USERS]
