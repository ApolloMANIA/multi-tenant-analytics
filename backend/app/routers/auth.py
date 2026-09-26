from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.auth import (
    apply_rls_context,
    create_access_token,
    hash_password,
    lookup_user_row,
    verify_password,
)
from app.database import SessionLocal, get_db
from app.deps import AdminUser, CurrentUser, RLSSession
from app.models import Tenant, User
from app.schemas import LoginRequest, RegisterRequest, TenantOut, Token, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> Token:
    row = lookup_user_row(db, body.email)
    if not row or not verify_password(body.password, row["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token(
        {
            "sub": str(row["id"]),
            "tenant_id": str(row["tenant_id"]),
            "role": str(row["role"]),
            "is_platform_admin": bool(row["is_platform_admin"]),
            "email": row["email"],
            "full_name": row["full_name"],
        }
    )
    return Token(access_token=token)


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest) -> UserOut:
    """Register a user into an existing tenant (demo onboarding)."""
    db = SessionLocal()
    try:
        tenant_row = db.execute(
            text("SELECT * FROM lookup_tenant_by_slug(:slug)"),
            {"slug": body.tenant_slug},
        ).mappings().first()
        if tenant_row is None:
            raise HTTPException(status_code=404, detail="Tenant not found")

        existing = lookup_user_row(db, body.email)
        if existing:
            raise HTTPException(status_code=409, detail="Email already registered")

        tenant_id = tenant_row["id"]
        apply_rls_context(db, tenant_id=tenant_id, role="admin", is_platform_admin=True)
        user = User(
            tenant_id=tenant_id,
            email=body.email.lower(),
            full_name=body.full_name,
            hashed_password=hash_password(body.password),
            role=body.role,
            is_platform_admin=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return UserOut.model_validate(user)
    finally:
        db.close()


@router.get("/me", response_model=UserOut)
def me(payload: CurrentUser, db: RLSSession) -> UserOut:
    user = db.get(User, UUID(payload.sub))
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return UserOut.model_validate(user)


@router.get("/tenants", response_model=list[TenantOut])
def list_tenants(
    db: RLSSession,
    payload: AdminUser,
) -> list[TenantOut]:
    rows = db.execute(select(Tenant).order_by(Tenant.name)).scalars().all()
    return [TenantOut.model_validate(t) for t in rows]
