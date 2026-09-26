from collections.abc import Generator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.auth import apply_rls_context, decode_token
from app.database import SessionLocal
from app.models import UserRole
from app.schemas import TokenPayload

bearer = HTTPBearer(auto_error=False)


def get_current_payload(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> TokenPayload:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        return decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def get_db_with_rls(
    payload: Annotated[TokenPayload, Depends(get_current_payload)],
) -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        apply_rls_context(
            db,
            tenant_id=payload.tenant_id,
            role=payload.role,
            is_platform_admin=payload.is_platform_admin,
        )
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def require_roles(*roles: UserRole):
    allowed = {r.value for r in roles}

    def _checker(payload: TokenPayload = Depends(get_current_payload)) -> TokenPayload:
        if payload.is_platform_admin:
            return payload
        if payload.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return payload

    return _checker


CurrentUser = Annotated[TokenPayload, Depends(get_current_payload)]
RLSSession = Annotated[Session, Depends(get_db_with_rls)]
AdminUser = Annotated[TokenPayload, Depends(require_roles(UserRole.admin))]
AdminEditor = Annotated[
    TokenPayload, Depends(require_roles(UserRole.admin, UserRole.editor))
]
