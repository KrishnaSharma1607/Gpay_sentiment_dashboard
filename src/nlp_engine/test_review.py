import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(
    host=os.getenv("DB_HOST"),
    database=os.getenv("DB_NAME"),
    port=os.getenv("DB_PORT"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASS")
)

cursor = conn.cursor()

cursor.execute("""
SELECT
    r.review_id,
    r.user_name,
    r.score,
    r.content,
    f.aspect_name,
    f.sentiment_label,
    f.sentiment_score,
    f.aspect_confidence,
    f.is_severity_high,
    f.review_length
FROM reviews r
JOIN fact_review_sentiment f
ON r.review_id = f.review_id
LIMIT 10;
""")

rows = cursor.fetchall()

for i, row in enumerate(rows, 1):
    print("=" * 100)
    print(f"Review #{i}")
    print(f"Review ID          : {row[0]}")
    print(f"User               : {row[1]}")
    print(f"Play Store Rating  : {row[2]}")
    print(f"Review             : {row[3]}")
    print()
    print(f"Aspect             : {row[4]}")
    print(f"Sentiment          : {row[5]}")
    print(f"Sentiment Score    : {row[6]:.4f}")
    print(f"Confidence         : {row[7]:.4f}")
    print(f"High Severity      : {row[8]}")
    print(f"Length             : {row[9]}")
    print()

cursor.close()
conn.close()