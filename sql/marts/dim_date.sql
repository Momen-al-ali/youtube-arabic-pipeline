-- dim_date
-- Pre-populated calendar table — run once
-- Range: 2024-01-01 → 2026-12-31

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
    d::DATE,
    EXTRACT(DAY     FROM d)::INTEGER,
    EXTRACT(WEEK    FROM d)::INTEGER,
    EXTRACT(MONTH   FROM d)::INTEGER,
    EXTRACT(QUARTER FROM d)::INTEGER,
    EXTRACT(YEAR    FROM d)::INTEGER,
    TO_CHAR(d, 'Month'),
    TO_CHAR(d, 'Day'),
    EXTRACT(DOW FROM d) IN (0, 6)
FROM generate_series(
    '2024-01-01'::DATE,
    '2026-12-31'::DATE,
    '1 day'::INTERVAL
) AS d
ON CONFLICT (date_key) DO NOTHING;