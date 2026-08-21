import os
import sys
import logging
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def load_reviews(reviews):
    if not reviews:
        logging.warning("no reviews found")
        return 0

    conn = None
    cursor = None

    # pulling credentials from .env
    db_host = os.environ.get("DB_HOST", "localhost")
    db_name = os.environ.get("DB_NAME", "playstore_db")
    db_port = os.environ.get("DB_PORT", "5432")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "postgres")

    logging.info("connecting to PostgreSQL database..")
    try:
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            port=db_port,
            user=db_user,
            password=db_pass
        )
        logging.info("database connected")
        cursor = conn.cursor()
    except Exception as e:
        logging.error(f"connection failed: {e}")
        sys.exit(1) # Guarantees the pipeline halts if DB fails

    inserted_count = 0

    try:
        logging.info(f"Loading {len(reviews)} reviews...")
        # ON CONFLICT keeps in check we don't insert duplicate rows(if the pipeline runs twice)
        insert_query = """
            INSERT INTO reviews (review_id, user_name, content, score, at, app_version, thumbs_up_count, reply_content, replied_at)
            VALUES %s
            ON CONFLICT (review_id) DO NOTHING;
        """
        
        # map the Python dictionaries to SQL tuples
        data_tuples = [
            (
                r['reviewId'], 
                r['userName'], 
                r['content'], 
                r['score'], 
                r['at'], 
                r['appVersion'], 
                r['thumbsUpCount'],
                r['replyContent'],
                r['repliedAt'] 
            ) 
            for r in reviews
        ]

        psycopg2.extras.execute_values(
            cursor, # DB cursor
            insert_query, # SQL query string
            data_tuples, # batch data
            page_size=100 # chunk size(for memory efficiency)
        )
        
        # Rowcount tells us how many rows were ACTUALLY inserted vs skipped
        inserted_count = cursor.rowcount
        
        logging.info(f"inserted {inserted_count} reviews.")

        conn.commit()
        logging.info("Transaction committed.")

    except Exception as e:
        logging.error(f"Insert failed: {e}")
        if conn:
            conn.rollback() # protect data integrity(if bulk insert fails halfway)
        logging.info("Rolling back transaction.")
        inserted_count = 0

    finally:
        # close the connection
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logging.info("database connection closed.")

    return inserted_count

if __name__ == "__main__":
    from playstore_scraper import fetch_reviews
    
    # test execution
    test_app = "com.google.android.apps.nbu.paisa.user" 
    
    logging.info("--- Starting Local Test Run ---")
    scraped_data = fetch_reviews(test_app, review_count=50)
    rows_inserted = load_reviews(scraped_data)
    
    print(f"\nrows inserted: {rows_inserted}")