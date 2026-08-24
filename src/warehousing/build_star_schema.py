import os
import sys
import time
import logging
import psycopg2
import psycopg2.extras
from datetime import datetime
from dotenv import load_dotenv

# Make ingestion/ and nlp_engine/ importable regardless of where this script is run from
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../src
sys.path.append(os.path.join(BASE_DIR, "ingestion"))
sys.path.append(os.path.join(BASE_DIR, "nlp_engine"))

from playstore_scraper import fetch_reviews          # noqa: E402
from sentiment_model import NLPProcessor              # noqa: E402

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DB_CONFIG = dict(
    host=os.environ.get("DB_HOST"),
    database=os.environ.get("DB_NAME"),
    port=os.environ.get("DB_PORT"),
    user=os.environ.get("DB_USER"),
    password=os.environ.get("DB_PASS"),
)


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def get_or_create_date_id(cursor, review_date):
    """Look up date_id for a given date; insert into dim_date if it doesn't exist yet."""
    cursor.execute("SELECT date_id FROM dim_date WHERE date = %s;", (review_date,))
    row = cursor.fetchone()
    if row:
        return row[0]

    week = review_date.isocalendar()[1]
    month = review_date.month
    quarter = (month - 1) // 3 + 1
    year = review_date.year

    cursor.execute("""
        INSERT INTO dim_date (date, week, month, quarter, year)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING date_id;
    """, (review_date, week, month, quarter, year))
    return cursor.fetchone()[0]


def get_aspect_id_map(cursor):
    cursor.execute("SELECT aspect_id, aspect_name FROM dim_aspect;")
    return {name: aid for aid, name in cursor.fetchall()}


def run_pipeline(app_id="com.google.android.apps.nbu.paisa.user", review_count=50):
    logging.info(f"=== STARTING STAR SCHEMA BUILD ({review_count} reviews) ===")

    # 1. Scrape
    raw_reviews = fetch_reviews(app_id, review_count=review_count)
    if not raw_reviews:
        logging.error("No reviews fetched. Aborting.")
        return

    # 2. Load NLP model (this takes a little while the first time — downloads model weights)
    nlp = NLPProcessor()

    conn = get_connection()
    cursor = conn.cursor()

    aspect_id_map = get_aspect_id_map(cursor)
    if not aspect_id_map:
        logging.error("dim_aspect is empty — run the seed SQL insert first (Step 8).")
        conn.close()
        return

    # Load already-scored review IDs so a rerun skips NLP work entirely for these,
    # instead of wastefully re-processing reviews we already have.
    cursor.execute("SELECT review_id FROM fact_review_sentiment;")
    already_scored = {row[0] for row in cursor.fetchall()}
    logging.info(f"Found {len(already_scored)} already-scored reviews — these will be skipped instantly.")

    inserted_reviews = 0
    inserted_facts = 0
    COMMIT_EVERY = 1000  # save progress periodically so a long run is crash-safe

    for idx, r in enumerate(raw_reviews, start=1):
        review_id = r['reviewId']
        content = r['content']
        review_date = r['at'].date() if isinstance(r['at'], datetime) else r['at']

        if review_id in already_scored:
            continue  # already done in a previous run — skip instantly, no NLP call

        try:
            # ---- staging_raw_reviews (capture raw data before any NLP processing) ----
            cursor.execute("""
                INSERT INTO staging_raw_reviews
                    (review_id, review_text, star_rating, app_version, thumbs_up_count, review_date)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (review_id) DO NOTHING;
            """, (
                review_id, content, r['score'], r['appVersion'],
                r['thumbsUpCount'], review_date
            ))

            # ---- dim_review ----
            cursor.execute("""
                INSERT INTO dim_review
                    (review_id, review_date, review_text, star_rating, app_version, thumbs_up_count, review_length, source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, 'Play Store')
                ON CONFLICT (review_id) DO NOTHING;
            """, (
                review_id, review_date, content, r['score'], r['appVersion'],
                r['thumbsUpCount'], len(content or "")
            ))
            if cursor.rowcount > 0:
                inserted_reviews += 1

            # ---- NLP ----
            insights = nlp.analyze_review(content)
            if not insights:
                continue  # empty/meaningless review, skip fact row

            aspect_id = aspect_id_map.get(insights['aspect'])
            if aspect_id is None:
                logging.warning(f"Unknown aspect '{insights['aspect']}' — skipping fact row for {review_id}")
                continue

            date_id = get_or_create_date_id(cursor, review_date)

            # ---- fact_review_sentiment ----
            cursor.execute("""
                INSERT INTO fact_review_sentiment
                    (review_id, aspect_id, date_id, sentiment_score, sentiment_label, aspect_confidence, is_severity_high)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (review_id) DO NOTHING;
            """, (
                review_id, aspect_id, date_id,
                insights['sentiment_score'], insights['sentiment_label'],
                insights['aspect_confidence'], insights['is_severity_high']
            ))
            if cursor.rowcount > 0:
                inserted_facts += 1

        except psycopg2.OperationalError as e:
            # Connection dropped (e.g. brief Wi-Fi/hotspot hiccup) — reconnect and skip this one review
            logging.warning(f"DB connection issue at review {idx}: {e}.")
            try:
                conn.close()
            except Exception:
                pass

            reconnected = False
            for attempt in range(1, 6):  # try up to 5 times with growing delay
                wait = attempt * 10
                logging.warning(f"Reconnect attempt {attempt}/5 in {wait}s...")
                time.sleep(wait)
                try:
                    conn = get_connection()
                    cursor = conn.cursor()
                    aspect_id_map = get_aspect_id_map(cursor)
                    reconnected = True
                    logging.info("Reconnected successfully. Resuming from next review.")
                    break
                except psycopg2.OperationalError as reconnect_err:
                    logging.warning(f"Reconnect attempt {attempt} failed: {reconnect_err}")

            if not reconnected:
                logging.error("Could not reconnect after 5 attempts — internet is likely down. "
                               "Stopping safely. Already-committed progress is saved. "
                               "Just rerun the script once your connection is back; "
                               "it will skip everything already done.")
                break  # exit the loop cleanly instead of crashing with a traceback

            continue

        if idx % COMMIT_EVERY == 0:
            conn.commit()
            logging.info(f"Progress: {idx}/{len(raw_reviews)} reviews processed "
                         f"({inserted_reviews} reviews, {inserted_facts} facts inserted so far)")

    conn.commit()
    cursor.close()
    conn.close()

    logging.info(f"Inserted {inserted_reviews} new reviews into dim_review.")
    logging.info(f"Inserted {inserted_facts} new rows into fact_review_sentiment.")
    logging.info("=== STAR SCHEMA BUILD COMPLETE ===")


if __name__ == "__main__":
    run_pipeline(review_count=16000)