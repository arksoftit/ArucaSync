
SELECT version();

SELECT current_database() AS database_name, current_user AS current_user;

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name LIKE 'arc_%'
ORDER BY table_name;

SELECT
    table_name,
    column_name,
    ordinal_position,
    data_type,
    udt_name,
    character_maximum_length,
    numeric_precision,
    numeric_scale,
    is_nullable,
    column_default,
    is_identity
FROM information_schema.columns
WHERE table_schema = 'public'
AND table_name LIKE 'arc_%'
ORDER BY table_name, ordinal_position;

SELECT
    c.relname AS table_name,
    con.conname AS constraint_name,
    con.contype AS constraint_type,
    pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint con
JOIN pg_class c ON con.conrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'public'
AND c.relname LIKE 'arc_%'
AND con.contype IN ('p', 'u', 'f')
ORDER BY c.relname, con.contype, con.conname;

SELECT
    tablename AS table_name,
    indexname AS index_name,
    indexdef AS index_definition
FROM pg_indexes
WHERE schemaname = 'public'
AND tablename LIKE 'arc_%'
ORDER BY tablename, indexname;

SELECT
    n.nspname AS schema_name,
    c.relname AS table_name,
    t.tgname AS trigger_name,
    pg_get_triggerdef(t.oid) AS trigger_definition
FROM pg_trigger t
JOIN pg_class c ON t.tgrelid = c.oid
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'public'
AND c.relname LIKE 'arc_%'
AND NOT t.tgisinternal
ORDER BY c.relname, t.tgname;

SELECT
    n.nspname AS schema_name,
    p.proname AS function_name,
    pg_get_function_identity_arguments(p.oid) AS function_arguments,
    pg_get_functiondef(p.oid) AS function_definition
FROM pg_proc p
JOIN pg_namespace n ON p.pronamespace = n.oid
WHERE n.nspname = 'public'
AND p.proname LIKE 'fn_%'
ORDER BY p.proname;

SELECT
    c.relname AS table_name,
    c.relrowsecurity AS row_level_security_enabled
FROM pg_class c
JOIN pg_namespace n ON c.relnamespace = n.oid
WHERE n.nspname = 'public'
AND c.relname LIKE 'arc_%'
ORDER BY c.relname;

SELECT
    schemaname,
    tablename AS table_name,
    policyname AS policy_name,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
AND tablename LIKE 'arc_%'
ORDER BY tablename, policyname;

SELECT 'arc_clientes' AS table_name, COUNT(*) AS row_count FROM public.arc_clientes
UNION ALL
SELECT 'arc_depositos', COUNT(*) FROM public.arc_depositos
UNION ALL
SELECT 'arc_categorias', COUNT(*) FROM public.arc_categorias
UNION ALL
SELECT 'arc_inventario', COUNT(*) FROM public.arc_inventario
UNION ALL
SELECT 'arc_vendedores', COUNT(*) FROM public.arc_vendedores
UNION ALL
SELECT 'arc_zonas', COUNT(*) FROM public.arc_zonas
ORDER BY table_name;