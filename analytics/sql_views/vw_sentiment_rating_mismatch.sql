-- NLP validation KPI: flags reviews where the star rating and the model's
-- sentiment score disagree (e.g. 5 stars but negative sentiment).
CREATE VIEW vw_sentiment_rating_mismatch AS
SELECT
    r.review_id,
    r.star_rating,
    f.sentiment_score,
    CASE
        WHEN r.star_rating >= 4 AND f.sentiment_score < 0 THEN 'High rating, negative sentiment'
        WHEN r.star_rating <= 2 AND f.sentiment_score > 0 THEN 'Low rating, positive sentiment'
        ELSE 'Consistent'
    END AS mismatch_type
FROM dim_review r
JOIN fact_review_sentiment f ON r.review_id = f.review_id;