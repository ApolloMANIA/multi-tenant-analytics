-- Demo seeds. Password for all users: password123
INSERT INTO tenants (id, name, slug) VALUES
    ('11111111-1111-1111-1111-111111111111', 'Acme Retail', 'acme'),
    ('22222222-2222-2222-2222-222222222222', 'Globex Corp', 'globex');

INSERT INTO users (id, tenant_id, email, full_name, hashed_password, role, is_platform_admin) VALUES
    (
        'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
        '11111111-1111-1111-1111-111111111111',
        'admin@platform.local',
        'Platform Admin',
        '$2b$12$QPQxWS75XIhztFA35snsEeCGPetgpAw7aht4rpucIr5oKW5bk1uDC',
        'admin',
        TRUE
    ),
    (
        'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
        '11111111-1111-1111-1111-111111111111',
        'admin@acme.local',
        'Acme Admin',
        '$2b$12$QPQxWS75XIhztFA35snsEeCGPetgpAw7aht4rpucIr5oKW5bk1uDC',
        'admin',
        FALSE
    ),
    (
        'cccccccc-cccc-cccc-cccc-cccccccccccc',
        '11111111-1111-1111-1111-111111111111',
        'editor@acme.local',
        'Acme Editor',
        '$2b$12$QPQxWS75XIhztFA35snsEeCGPetgpAw7aht4rpucIr5oKW5bk1uDC',
        'editor',
        FALSE
    ),
    (
        'dddddddd-dddd-dddd-dddd-dddddddddddd',
        '11111111-1111-1111-1111-111111111111',
        'viewer@acme.local',
        'Acme Viewer',
        '$2b$12$QPQxWS75XIhztFA35snsEeCGPetgpAw7aht4rpucIr5oKW5bk1uDC',
        'viewer',
        FALSE
    ),
    (
        'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
        '22222222-2222-2222-2222-222222222222',
        'admin@globex.local',
        'Globex Admin',
        '$2b$12$QPQxWS75XIhztFA35snsEeCGPetgpAw7aht4rpucIr5oKW5bk1uDC',
        'admin',
        FALSE
    ),
    (
        'ffffffff-ffff-ffff-ffff-ffffffffffff',
        '22222222-2222-2222-2222-222222222222',
        'viewer@globex.local',
        'Globex Viewer',
        '$2b$12$QPQxWS75XIhztFA35snsEeCGPetgpAw7aht4rpucIr5oKW5bk1uDC',
        'viewer',
        FALSE
    );
-- Sales data for Acme (tenant 1)
INSERT INTO sales (tenant_id, product_name, category, quantity, unit_price, sold_at, created_by)
SELECT
    '11111111-1111-1111-1111-111111111111',
    (ARRAY['Widget A', 'Widget B', 'Gadget X', 'Gadget Y', 'Kit Pro'])[1 + (i % 5)],
    (ARRAY['Hardware', 'Hardware', 'Electronics', 'Electronics', 'Bundles'])[1 + (i % 5)],
    1 + (i % 8),
    (ARRAY[29.99, 49.99, 99.00, 149.50, 199.00])[1 + (i % 5)],
    date_trunc('day', now()) - ((i % 45) || ' days')::interval - ((i % 12) || ' hours')::interval,
    'cccccccc-cccc-cccc-cccc-cccccccccccc'
FROM generate_series(1, 120) AS s(i);

-- Sales data for Globex (tenant 2)
INSERT INTO sales (tenant_id, product_name, category, quantity, unit_price, sold_at, created_by)
SELECT
    '22222222-2222-2222-2222-222222222222',
    (ARRAY['Cloud Seat', 'Support Pack', 'Analytics Add-on', 'SSO Module', 'API Bundle'])[1 + (i % 5)],
    (ARRAY['SaaS', 'Services', 'SaaS', 'SaaS', 'SaaS'])[1 + (i % 5)],
    1 + (i % 10),
    (ARRAY[15.00, 250.00, 75.00, 120.00, 500.00])[1 + (i % 5)],
    date_trunc('day', now()) - ((i % 40) || ' days')::interval - ((i % 8) || ' hours')::interval,
    'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'
FROM generate_series(1, 100) AS s(i);

REFRESH MATERIALIZED VIEW mv_daily_sales;
