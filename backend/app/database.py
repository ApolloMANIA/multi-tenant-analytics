from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def tenant_session(
    tenant_id: UUID | None,
    role: str,
    is_platform_admin: bool,
) -> Generator[Session, None, None]:
    """Open a DB session with RLS session variables set for the request."""
    db = SessionLocal()
    try:
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
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
