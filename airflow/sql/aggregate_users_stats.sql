CREATE TABLE IF NOT EXISTS users_stats (
    stat_date DATE,
    country VARCHAR(128),
    total_users BIGINT,
    PRIMARY KEY (stat_date, country)
);

INSERT INTO users_stats (stat_date, country, total_users)
SELECT
    COALESCE(DATE(event_time), CURRENT_DATE) AS stat_date,
    COALESCE(country, 'UNKNOWN') AS country,
    COUNT(*) AS total_users
FROM users_raw
GROUP BY COALESCE(DATE(event_time), CURRENT_DATE), COALESCE(country, 'UNKNOWN')
ON CONFLICT (stat_date, country) DO UPDATE
SET total_users = EXCLUDED.total_users;
