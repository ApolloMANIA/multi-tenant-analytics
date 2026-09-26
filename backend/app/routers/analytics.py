from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.deps import AdminEditor, AdminUser, CurrentUser, RLSSession
from app.schemas import DailyRevenuePoint, ProductRankRow, TenantComparisonRow

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/daily-revenue", response_model=list[DailyRevenuePoint])
def daily_revenue(payload: CurrentUser, db: RLSSession, days: int = 30) -> list[DailyRevenuePoint]:
    """Window functions: LAG for day-over-day delta + running total within tenant."""
    sql = text(
        """
        WITH daily AS (
            SELECT
                sale_date,
                SUM(revenue)::float AS revenue,
                SUM(units_sold)::int AS units_sold,
                SUM(order_count)::int AS order_count
            FROM mv_daily_sales
            WHERE tenant_id = CAST(:tenant_id AS uuid)
              AND sale_date >= (CURRENT_DATE - CAST(:days AS int))
            GROUP BY sale_date
        ),
        windowed AS (
            SELECT
                sale_date::text AS sale_date,
                revenue,
                units_sold,
                order_count,
                LAG(revenue) OVER (ORDER BY sale_date) AS prev_day_revenue,
                revenue - LAG(revenue) OVER (ORDER BY sale_date) AS revenue_delta,
                SUM(revenue) OVER (ORDER BY sale_date
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS running_revenue
            FROM daily
        )
        SELECT * FROM windowed ORDER BY sale_date
        """
    )
    rows = db.execute(
        sql,
        {
            "tenant_id": payload.tenant_id,
            "days": max(1, min(days, 365)),
        },
    ).mappings().all()
    return [DailyRevenuePoint(**dict(r)) for r in rows]


@router.get("/product-ranks", response_model=list[ProductRankRow])
def product_ranks(payload: CurrentUser, db: RLSSession, limit: int = 10) -> list[ProductRankRow]:
    """RANK() window function for top products within the caller's tenant."""
    sql = text(
        """
        WITH ranked AS (
            SELECT
                product_name,
                category,
                SUM(revenue)::float AS revenue,
                SUM(units_sold)::int AS units_sold,
                RANK() OVER (ORDER BY SUM(revenue) DESC) AS rank_in_tenant
            FROM mv_daily_sales
            WHERE tenant_id = CAST(:tenant_id AS uuid)
            GROUP BY product_name, category
        )
        SELECT * FROM ranked
        WHERE rank_in_tenant <= :limit
        ORDER BY rank_in_tenant
        """
    )
    rows = db.execute(
        sql,
        {"tenant_id": payload.tenant_id, "limit": max(1, min(limit, 50))},
    ).mappings().all()
    return [ProductRankRow(**dict(r)) for r in rows]


@router.get("/tenant-comparison", response_model=list[TenantComparisonRow])
def tenant_comparison(payload: AdminUser, db: RLSSession) -> list[TenantComparisonRow]:
    """Cross-tenant rollup — platform admin only (RLS + role gate)."""
    if not payload.is_platform_admin:
        raise HTTPException(status_code=403, detail="Platform admin required for cross-tenant view")

    sql = text(
        """
        SELECT
            t.id AS tenant_id,
            t.name AS tenant_name,
            COALESCE(SUM(m.revenue), 0)::float AS revenue,
            COALESCE(SUM(m.units_sold), 0)::int AS units_sold,
            COALESCE(SUM(m.order_count), 0)::int AS order_count
        FROM tenants t
        LEFT JOIN mv_daily_sales m ON m.tenant_id = t.id
        GROUP BY t.id, t.name
        ORDER BY revenue DESC
        """
    )
    rows = db.execute(sql).mappings().all()
    return [TenantComparisonRow(**dict(r)) for r in rows]


@router.post("/refresh-materialized-view")
def refresh_mv(payload: AdminEditor, db: RLSSession) -> dict[str, str]:
    db.execute(text("SELECT refresh_daily_sales()"))
    return {"status": "refreshed"}
