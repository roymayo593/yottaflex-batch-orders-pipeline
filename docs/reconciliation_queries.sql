-- Latest run status and operational counts.
SELECT
    run_id,
    status,
    started_at,
    ended_at,
    customers_input,
    customers_published,
    orders_input,
    orders_published,
    history_only_count,
    rejected_count,
    failure_reason
FROM pipeline_runs
ORDER BY started_at DESC
LIMIT 10;

-- Reject distribution for a run. Bind :run_id in the SQLite client.
SELECT entity, reason_codes, COUNT(*) AS rejected_rows
FROM rejects
WHERE run_id = :run_id
GROUP BY entity, reason_codes
ORDER BY rejected_rows DESC, entity, reason_codes;

-- Verify every current order resolves to a customer. Expected result: zero.
SELECT COUNT(*) AS orphan_orders
FROM orders_curated AS orders
LEFT JOIN customers_curated AS customers
    ON customers.customer_id = orders.customer_id
WHERE customers.customer_id IS NULL;

-- Analytical aggregate used by the reconciliation report.
SELECT
    COUNT(*) AS order_count,
    ROUND(SUM(CAST(amount_usd AS REAL)), 2) AS total_amount_usd
FROM orders_curated;

-- Show entities with multiple recorded versions.
SELECT order_id, COUNT(*) AS version_count
FROM order_history
GROUP BY order_id
HAVING COUNT(*) > 1
ORDER BY version_count DESC, order_id;

