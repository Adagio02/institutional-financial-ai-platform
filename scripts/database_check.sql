SELECT version_num
FROM alembic_version;
SELECT *
FROM trade_proposals
ORDER BY created_at DESC;
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'trade_proposals'
ORDER BY ordinal_position;