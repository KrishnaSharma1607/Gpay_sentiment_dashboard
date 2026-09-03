-- Ranks aspects by negative review volume within each month, using RANK()
-- with PARTITION BY. Business purpose: shows which complaint category
-- dominated each month, useful for tying spikes to app release cycles.
CREATE VIEW vw_monthly_aspect_ranking AS
SELECT
    d.year, d.month,
    a.aspect_name,
    COUNT(*) AS negative_count,
    RANK() OVER (PARTITION BY d.year, d.month ORDER BY COUNT(*) DESC) AS aspect_rank
FROM fact_review_sentiment f
JOIN dim_aspect a ON f.aspect_id = a.aspect_id
JOIN dim_date d ON f.date_id = d.date_id
WHERE f.sentiment_label = 'NEGATIVE'
GROUP BY d.year, d.month, a.aspect_name;