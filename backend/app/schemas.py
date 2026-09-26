from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

import email_validator
from email_validator import EmailNotValidError, validate_email
from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models import UserRole

# Seed/demo accounts use @*.local; email-validator rejects that reserved TLD by default.
if "local" in email_validator.SPECIAL_USE_DOMAIN_NAMES:
    email_validator.SPECIAL_USE_DOMAIN_NAMES.remove("local")


def _normalize_email(value: str) -> str:
    try:
        return validate_email(value, check_deliverability=False).normalized
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc


EmailAddress = Annotated[str, AfterValidator(_normalize_email)]


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: str
    is_platform_admin: bool = False
    email: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailAddress
    password: str


class RegisterRequest(BaseModel):
    email: EmailAddress
    password: str = Field(min_length=8)
    full_name: str
    tenant_slug: str
    role: UserRole = UserRole.viewer


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    email: str
    full_name: str
    role: UserRole
    is_platform_admin: bool
    created_at: datetime


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    created_at: datetime


class SaleCreate(BaseModel):
    product_name: str
    category: str
    quantity: int = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    sold_at: datetime | None = None


class SaleUpdate(BaseModel):
    product_name: str | None = None
    category: str | None = None
    quantity: int | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    sold_at: datetime | None = None


class SaleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_name: str
    category: str
    quantity: int
    unit_price: Decimal
    sold_at: datetime
    created_by: UUID | None
    created_at: datetime


class DailyRevenuePoint(BaseModel):
    sale_date: str
    revenue: float
    units_sold: int
    order_count: int
    prev_day_revenue: float | None = None
    revenue_delta: float | None = None
    running_revenue: float | None = None


class ProductRankRow(BaseModel):
    product_name: str
    category: str
    revenue: float
    units_sold: int
    rank_in_tenant: int


class TenantComparisonRow(BaseModel):
    tenant_id: UUID
    tenant_name: str
    revenue: float
    units_sold: int
    order_count: int
