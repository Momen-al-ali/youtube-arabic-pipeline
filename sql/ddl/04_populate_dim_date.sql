-- ============================================================
-- Populate dim_date with one row per day
-- Range: 2024-01-01 → 2026-12-31
-- Run once — safe to re-run (INSERT ... ON CONFLICT DO NOTHING)
-- ============================================================

INSERT INTO marts.dim_date (
    date_key,
    day,
    week,
    month,
    quarter,
    year,
    month_name,
    day_name,
    is_weekend
)
SELECT
    d::DATE                                             AS date_key,
    EXTRACT(DAY FROM d)::INTEGER                        AS day,
    EXTRACT(WEEK FROM d)::INTEGER                       AS week,
    EXTRACT(MONTH FROM d)::INTEGER                      AS month,
    EXTRACT(QUARTER FROM d)::INTEGER                    AS quarter,
    EXTRACT(YEAR FROM d)::INTEGER                       AS year,
    TO_CHAR(d, 'Month')                                 AS month_name,
    TO_CHAR(d, 'Day')                                   AS day_name,
    EXTRACT(DOW FROM d) IN (0, 6)                       AS is_weekend
FROM generate_series(
    '2024-01-01'::DATE,
    '2026-12-31'::DATE,
    '1 day'::INTERVAL
) AS d
ON CONFLICT (date_key) DO NOTHING;