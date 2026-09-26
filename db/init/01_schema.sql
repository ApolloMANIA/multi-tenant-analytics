-- Roles: app_user is forced through RLS; superset_reader is read-only for BI.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
    CREATE ROLE app_user LOGIN PASSWORD 'app_user_secret';
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'superset_reader') THEN
    CREATE ROLE superset_reader LOGIN PASSWORD 'superset_reader_secret';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE analytics TO app_user;
GRANT CONNECT ON DATABASE analytics TO superset_reader;
GRANT USAGE ON SCHEMA public TO app_user, superset_reader;

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL UNIQUE,
    slug        TEXT NOT NULL UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TYPE user_role AS ENUM ('admin', 'editor', 'viewer');

CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email         TEXT NOT NULL,
    full_name     TEXT NOT NULL,
    hashed_password TEXT NOT NULL,
    role          user_role NOT NULL DEFAULT 'viewer',
    is_platform_admin BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

CREATE TABLE sales (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    product_name  TEXT NOT NULL,
    category      TEXT NOT NULL,
    quantity      INTEGER NOT NULL CHECK (quantity > 0),
    unit_price    NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
    sold_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by    UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_sales_tenant_sold_at ON sales(tenant_id, sold_at);
CREATE INDEX idx_sales_tenant_product ON sales(tenant_id, product_name);
CREATE INDEX idx_sales_category ON sales(tenant_id, category);

-- Daily aggregates (materialized) for fast dashboard queries
CREATE MATERIALIZED VIEW mv_daily_sales AS
SELECT
    tenant_id,
    date_trunc('day', sold_at)::date AS sale_date,
    product_name,
    category,
    SUM(quantity) AS units_sold,
    SUM(quantity * unit_price) AS revenue,
    COUNT(*) AS order_count
FROM sales
GROUP BY tenant_id, date_trunc('day', sold_at)::date, product_name, category
WITH DATA;

CREATE UNIQUE INDEX idx_mv_daily_sales_pk
    ON mv_daily_sales (tenant_id, sale_date, product_name, category);
CREATE INDEX idx_mv_daily_sales_tenant_date
    ON mv_daily_sales (tenant_id, sale_date);

GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
GRANT SELECT ON mv_daily_sales TO app_user, superset_reader;

CREATE OR REPLACE FUNCTION refresh_daily_sales() RETURNS void AS $$
BEGIN
  REFRESH MATERIALIZED VIEW mv_daily_sales;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

GRANT EXECUTE ON FUNCTION refresh_daily_sales() TO app_user;
GRANT SELECT ON tenants, users, sales TO superset_reader;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO superset_reader;
