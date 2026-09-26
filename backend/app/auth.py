from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.schemas import TokenPayload

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
settings = get_settings()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict[str, Any], expires_minutes: int | None = None) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.access_token_expire_minutes
    )
    payload["exp"] = expire
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> TokenPayload:
    try:
        raw = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return TokenPayload(
            sub=str(raw["sub"]),
            tenant_id=str(raw["tenant_id"]),
            role=str(raw["role"]),
            is_platform_admin=bool(raw.get("is_platform_admin", False)),
            email=str(raw["email"]),
            full_name=str(raw["full_name"]),
        )
    except (JWTError, KeyError, ValueError) as exc:
        raise ValueError("Invalid token") from exc


def lookup_user_row(db: Session, email: str) -> dict[str, Any] | None:
    """SECURITY DEFINER lookup so login works before RLS context is set."""
    row = db.execute(
        text("SELECT * FROM lookup_user_by_email(:email)"),
        {"email": email},
    ).mappings().first()
    return dict(row) if row else None


def apply_rls_context(
    db: Session,
    *,
    tenant_id: UUID | str | None,
    role: str,
    is_platform_admin: bool,
) -> None:
    db.execute(
        text("SELECT set_config('app.current_tenant', :tid, true)"),
        {"tid": str(tenant_id) if tenant_id else ""},
    )
    db.execute(
        text("SELECT set_config('app.current_role', :role, true)"),
        {"role": role or ""},
    )
    db.execute(
        text("SELECT set_config('app.is_platform_admin', :flag, true)"),
        {"flag": "true" if is_platform_admin else "false"},
    )
