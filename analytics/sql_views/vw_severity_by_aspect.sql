-- Severity-weighted complaint score, using a CTE
-- Business purpose: surfaces which complaint categories have the highest
-- proportion of high-severity issues, not just the highest volume.
CREATE VIEW vw_severity_by_aspect AS
WITH severity_counts AS (
    SELECT
        a.aspect_name,
        COUNT(*) FILTER (WHERE f.is_severity_high) AS high_severity_count,
        COUNT(*) AS total_count
    FROM fact_review_sentiment f
    JOIN dim_aspect a ON f.aspect_id = a.aspect_id
    GROUP BY a.aspect_name
)
SELECT
    aspect_name,
    high_severity_count,
    total_count,
    ROUND(100.0 * high_severity_count / NULLIF(total_count, 0), 2) AS severity_pct
FROM severity_counts
ORDER BY severity_pct DESC;