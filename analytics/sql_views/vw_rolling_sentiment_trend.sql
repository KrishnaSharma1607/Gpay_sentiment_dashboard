-- 7-day rolling average sentiment, using a window function.
-- Note: this day-weighted rolling average (average of daily averages) was
-- later replaced in the Power BI dashboard by a review-weighted DAX measure
-- for consistency with other KPIs and to support full cross-filtering.
-- Kept here as the original SQL-layer implementation.
CREATE VIEW vw_rolling_sentiment_trend AS
SELECT
    d.date,
    AVG(f.sentiment_score) AS daily_avg_sentiment,
    AVG(AVG(f.sentiment_score)) OVER (
        ORDER BY d.date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7day_avg
FROM fact_review_sentiment f
JOIN dim_date d ON f.date_id = d.date_id
GROUP BY d.date
ORDER BY d.date;