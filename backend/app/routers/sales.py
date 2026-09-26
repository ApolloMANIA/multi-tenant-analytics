from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import CurrentUser, RLSSession, require_roles
from app.models import Sale, UserRole
from app.schemas import SaleCreate, SaleOut, SaleUpdate, TokenPayload

router = APIRouter(prefix="/sales", tags=["sales"])

WriterUser = Annotated[
    TokenPayload, Depends(require_roles(UserRole.admin, UserRole.editor))
]


@router.get("", response_model=list[SaleOut])
def list_sales(payload: CurrentUser, db: RLSSession, limit: int = 100) -> list[SaleOut]:
    q = select(Sale).order_by(Sale.sold_at.desc()).limit(min(limit, 500))
    rows = db.execute(q).scalars().all()
    return [SaleOut.model_validate(r) for r in rows]


@router.post("", response_model=SaleOut, status_code=status.HTTP_201_CREATED)
def create_sale(body: SaleCreate, db: RLSSession, payload: WriterUser) -> SaleOut:
    sale = Sale(
        tenant_id=UUID(payload.tenant_id),
        product_name=body.product_name,
        category=body.category,
        quantity=body.quantity,
        unit_price=body.unit_price,
        sold_at=body.sold_at,
        created_by=UUID(payload.sub),
    )
    db.add(sale)
    db.flush()
    db.refresh(sale)
    return SaleOut.model_validate(sale)


@router.patch("/{sale_id}", response_model=SaleOut)
def update_sale(
    sale_id: UUID,
    body: SaleUpdate,
    db: RLSSession,
    payload: WriterUser,
) -> SaleOut:
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(sale, key, value)
    db.flush()
    db.refresh(sale)
    return SaleOut.model_validate(sale)


@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sale(sale_id: UUID, db: RLSSession, payload: WriterUser) -> None:
    sale = db.get(Sale, sale_id)
    if sale is None:
        raise HTTPException(status_code=404, detail="Sale not found")
    db.delete(sale)
