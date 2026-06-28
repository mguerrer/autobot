import hashlib
import hmac
import json
import base64
import secrets
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models import Usuario

SECRET_KEY = settings.ollama_url + "::autobot-session-secret"
COOKIE_NAME = "autobot_session"
SESSION_TTL = timedelta(hours=24)


def _derive_key() -> bytes:
    return hashlib.sha256(SECRET_KEY.encode()).digest()


def _sign(data: dict) -> str:
    payload = base64.urlsafe_b64encode(json.dumps(data, default=str).encode()).decode().rstrip("=")
    sig = hmac.new(_derive_key(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{sig}"


def _unsign(token: str) -> Optional[dict]:
    try:
        parts = token.split(".")
        if len(parts) != 2:
            return None
        payload_b64, sig = parts
        expected = hmac.new(_derive_key(), payload_b64.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        padded = payload_b64 + "=" * (4 - len(payload_b64) % 4)
        return json.loads(base64.urlsafe_b64decode(padded))
    except Exception:
        return None


def create_session(user: Usuario) -> str:
    data = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role,
        "negocio_rut": user.negocio_rut or "",
        "exp": (datetime.now(timezone.utc) + SESSION_TTL).isoformat(),
    }
    return _sign(data)


def get_session(request: Request) -> Optional[dict]:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    data = _unsign(token)
    if not data:
        return None
    exp = data.get("exp")
    if exp and datetime.fromisoformat(exp) < datetime.now(timezone.utc):
        return None
    return data


def require_auth(role: Optional[str] = None):
    def decorator(func):
        async def wrapper(request: Request, *args, **kwargs):
            session = get_session(request)
            if not session:
                raise HTTPException(status_code=303, detail="")
            if role and session.get("role") != role:
                raise HTTPException(status_code=303, detail="")
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator


async def get_current_user(request: Request) -> Optional[dict]:
    return get_session(request)


def ensure_authenticated(request: Request):
    session = get_session(request)
    if not session:
        raise HTTPException(status_code=303, detail="")
    return session


def has_role(session: dict, role: str) -> bool:
    return session.get("role") == role


async def seed_default_users():
    async with async_session() as db:
        result = await db.execute(select(Usuario).where(Usuario.username == "admin"))
        if not result.scalar_one_or_none():
            admin = Usuario(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
            )
            db.add(admin)

        result = await db.execute(select(Usuario).where(Usuario.username == "cliente1"))
        if not result.scalar_one_or_none():
            cliente = Usuario(
                username="cliente1",
                password_hash=hash_password("cliente123"),
                role="cliente",
                negocio_rut="76.123.456-7",
            )
            db.add(cliente)

        result = await db.execute(select(Usuario).where(Usuario.username == "cliente2"))
        if not result.scalar_one_or_none():
            cliente = Usuario(
                username="cliente2",
                password_hash=hash_password("cliente123"),
                role="cliente",
                negocio_rut="77.789.012-3",
            )
            db.add(cliente)

        result = await db.execute(select(Usuario).where(Usuario.username == "cliente3"))
        if not result.scalar_one_or_none():
            cliente = Usuario(
                username="cliente3",
                password_hash=hash_password("cliente123"),
                role="cliente",
                negocio_rut="7688844-2",
            )
            db.add(cliente)

        await db.commit()


def user_context(request: Request) -> dict:
    from app.auth import get_session
    session = get_session(request)
    return {"user": session, "is_admin": session and session.get("role") == "admin"}


def hash_password(password: str) -> str:
    salt = hashlib.sha256(SECRET_KEY.encode()).hexdigest()[:16]
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100000).hex()


def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed
