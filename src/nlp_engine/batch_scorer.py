import os
import sys
import logging
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# import handling (works whether executed directly or via run_pipeline.py)
try:
    from sentiment_model import NLPProcessor
except ImportError:
    from src.nlp_engine.sentiment_model import NLPProcessor

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def process_unscored_reviews(batch_size=100):
    nlp = NLPProcessor()
    
    db_host = os.environ.get("DB_HOST", "localhost")
    db_name = os.environ.get("DB_NAME", "playstore_db")
    db_port = os.environ.get("DB_PORT", "5432")
    db_user = os.environ.get("DB_USER", "postgres")
    db_pass = os.environ.get("DB_PASS", "postgres")

    conn = None
    cursor = None

    try:
        conn = psycopg2.connect(
            host=db_host, 
            database=db_name, 
            port=db_port, 
            user=db_user, 
            password=db_pass
        )
        cursor = conn.cursor()
        
        total_processed = 0

        # Loop in batches until all unscored reviews in DB are processed
        while True:
            cursor.execute("""
                SELECT r.review_id, r.content 
                FROM reviews r
                LEFT JOIN fact_review_sentiment f ON r.review_id = f.review_id
                WHERE f.review_id IS NULL
                LIMIT %s;
            """, (batch_size,))
            
            unscored_reviews = cursor.fetchall()
            
            if not unscored_reviews:
                if total_processed == 0:
                    logging.info("No new reviews to process. Pipeline is up to date.")
                else:
                    logging.info(f"Batch processing complete. Total reviews scored: {total_processed}")
                break

            logging.info(f"Processing batch of {len(unscored_reviews)} new reviews through NLP engine...")
            
            insert_data = []
            for review_id, content in unscored_reviews:
                insights = nlp.analyze_review(content)
                
                # If content was empty/invalid, write a neutral record to avoid re-fetching on next run
                if not insights:
                    insights = {
                        "aspect": "General Feedback",
                        "sentiment_score": 0.0,
                        "sentiment_label": "NEUTRAL",
                        "aspect_confidence": 1.0,
                        "is_severity_high": False,
                        "review_length": len(content or "")
                    }

                insert_data.append((
                    review_id,
                    insights['aspect'],
                    insights['sentiment_score'],
                    insights['sentiment_label'],
                    insights['aspect_confidence'],
                    insights['is_severity_high'],
                    insights['review_length']
                ))

            # batch push to the Fact Table
            if insert_data:
                insert_query = """
                    INSERT INTO fact_review_sentiment 
                    (review_id, aspect_name, sentiment_score, sentiment_label, aspect_confidence, is_severity_high, review_length)
                    VALUES %s
                    ON CONFLICT (review_id) DO NOTHING;
                """
                psycopg2.extras.execute_values(cursor, insert_query, insert_data)
                conn.commit()
                
                total_processed += len(insert_data)
                logging.info(f"Inserted {len(insert_data)} records into fact table (Total so far: {total_processed}).")

    except Exception as e:
        logging.error(f"NLP Pipeline DB connection/execution failed: {e}")
        if conn: conn.rollback()
        sys.exit(1)
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

if __name__ == "__main__":
    process_unscored_reviews()