-- Row-Level Security: session GUC app.current_tenant + app.is_platform_admin
-- FastAPI sets these with SET LOCAL on every request.

ALTER TABLE tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE sales ENABLE ROW LEVEL SECURITY;

-- Helper: current tenant UUID from session (empty => no access for non-admins)
CREATE OR REPLACE FUNCTION current_tenant_id() RETURNS UUID AS $$
DECLARE
    tid TEXT;
BEGIN
    tid := NULLIF(current_setting('app.current_tenant', true), '');
    IF tid IS NULL THEN
        RETURN NULL;
    END IF;
    RETURN tid::UUID;
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION is_platform_admin() RETURNS BOOLEAN AS $$
BEGIN
    RETURN COALESCE(current_setting('app.is_platform_admin', true), 'false') = 'true';
END;
$$ LANGUAGE plpgsql STABLE;

CREATE OR REPLACE FUNCTION current_app_role() RETURNS TEXT AS $$
BEGIN
    RETURN COALESCE(current_setting('app.current_role', true), '');
END;
$$ LANGUAGE plpgsql STABLE;

-- Tenants: platform admins see all; others only their tenant
CREATE POLICY tenants_select ON tenants
    FOR SELECT
    USING (is_platform_admin() OR id = current_tenant_id());

CREATE POLICY tenants_insert ON tenants
    FOR INSERT
    WITH CHECK (is_platform_admin());

CREATE POLICY tenants_update ON tenants
    FOR UPDATE
    USING (is_platform_admin());

CREATE POLICY tenants_delete ON tenants
    FOR DELETE
    USING (is_platform_admin());

-- Users
CREATE POLICY users_select ON users
    FOR SELECT
    USING (is_platform_admin() OR tenant_id = current_tenant_id());

CREATE POLICY users_insert ON users
    FOR INSERT
    WITH CHECK (
        is_platform_admin()
        OR (
            tenant_id = current_tenant_id()
            AND current_app_role() = 'admin'
        )
    );

CREATE POLICY users_update ON users
    FOR UPDATE
    USING (
        is_platform_admin()
        OR (
            tenant_id = current_tenant_id()
            AND current_app_role() = 'admin'
        )
    );

CREATE POLICY users_delete ON users
    FOR DELETE
    USING (
        is_platform_admin()
        OR (
            tenant_id = current_tenant_id()
            AND current_app_role() = 'admin'
        )
    );

-- Sales: tenant isolation; write roles admin/editor only
CREATE POLICY sales_select ON sales
    FOR SELECT
    USING (is_platform_admin() OR tenant_id = current_tenant_id());

CREATE POLICY sales_insert ON sales
    FOR INSERT
    WITH CHECK (
        (is_platform_admin() OR tenant_id = current_tenant_id())
        AND current_app_role() IN ('admin', 'editor')
    );

CREATE POLICY sales_update ON sales
    FOR UPDATE
    USING (
        (is_platform_admin() OR tenant_id = current_tenant_id())
        AND current_app_role() IN ('admin', 'editor')
    );

CREATE POLICY sales_delete ON sales
    FOR DELETE
    USING (
        (is_platform_admin() OR tenant_id = current_tenant_id())
        AND current_app_role() IN ('admin', 'editor')
    );

-- Force RLS even for table owners when using app_user
ALTER TABLE tenants FORCE ROW LEVEL SECURITY;
ALTER TABLE users FORCE ROW LEVEL SECURITY;
ALTER TABLE sales FORCE ROW LEVEL SECURITY;

-- Login bootstrap: auth queries need to find users before tenant context is set.
-- Use a SECURITY DEFINER function owned by the superuser (postgres) that bypasses RLS.
CREATE OR REPLACE FUNCTION lookup_user_by_email(p_email TEXT)
RETURNS TABLE (
    id UUID,
    tenant_id UUID,
    email TEXT,
    full_name TEXT,
    hashed_password TEXT,
    role user_role,
    is_platform_admin BOOLEAN
) AS $$
    SELECT u.id, u.tenant_id, u.email, u.full_name, u.hashed_password, u.role, u.is_platform_admin
    FROM users u
    WHERE lower(u.email) = lower(p_email)
    LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER SET search_path = public;

CREATE OR REPLACE FUNCTION lookup_tenant_by_slug(p_slug TEXT)
RETURNS TABLE (
    id UUID,
    name TEXT,
    slug TEXT
) AS $$
    SELECT t.id, t.name, t.slug
    FROM tenants t
    WHERE t.slug = p_slug
    LIMIT 1;
$$ LANGUAGE sql SECURITY DEFINER SET search_path = public;

GRANT EXECUTE ON FUNCTION lookup_user_by_email(TEXT) TO app_user;
GRANT EXECUTE ON FUNCTION lookup_tenant_by_slug(TEXT) TO app_user;
GRANT EXECUTE ON FUNCTION current_tenant_id() TO app_user, superset_reader;
GRANT EXECUTE ON FUNCTION is_platform_admin() TO app_user, superset_reader;
GRANT EXECUTE ON FUNCTION current_app_role() TO app_user, superset_reader;
