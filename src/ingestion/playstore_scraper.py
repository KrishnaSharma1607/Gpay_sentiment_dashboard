import logging
from google_play_scraper import reviews, Sort

# logging set up
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def fetch_reviews(app_id, review_count=200, language="en", country="in"):
    try:
        # gathering raw data from play store API using library
        raw_reviews, _ = reviews(
            app_id,
            lang=language,
            country=country,
            sort=Sort.NEWEST,
            count=review_count
        )
    except Exception as e:
        logging.error(f"Play Store request failed: {e}")
        return []

    fetched_count = len(raw_reviews)

    if fetched_count == 0:
        logging.error("no reviews found")
        return []
    elif fetched_count < review_count:
        logging.warning(f"{review_count} reviews were expected but received only {fetched_count} are there")
    else:
        logging.info(f"Successfully fetched {fetched_count} raw reviews.")

    cleaned_reviews = []
    skipped_count = 0

    # processing the raw JSON to match the database schema
    for review in raw_reviews:
        review_id = review.get('reviewId')
        user_name = review.get('userName', 'Anonymous')
        content = review.get('content')
        score = review.get('score')
        at = review.get('at')
        
        # Play Store sometimes uses appVersion or reviewCreatedVersion
        app_version = review.get('appVersion') or review.get('reviewCreatedVersion', 'Unknown')
        thumbs_up_count = review.get('thumbsUpCount', 0)
        reply_content = review.get('replyContent')
        replied_at = review.get('repliedAt')

        # skipping reviews missing important data for NLP(field validation)
        if not review_id or not content or score is None:
            skipped_count += 1
            continue

        # cleaned
        cleaned_reviews.append({
            'reviewId': review_id,
            'userName': user_name,
            'content': content,
            'score': score,
            'at': at,
            'appVersion': app_version,
            'thumbsUpCount': thumbs_up_count,
            'replyContent': reply_content,
            'repliedAt': replied_at
        })

    cleaned_count = len(cleaned_reviews)
    logging.info(f"Fetched- {fetched_count} , Cleaned- {cleaned_count} , Skipped- {skipped_count}")

    return cleaned_reviews

if __name__ == "__main__":
    # Test block for local execution - Switched to PhonePe app ID
    test_app = "com.google.android.apps.nbu.paisa.user" 
    
    data = fetch_reviews(test_app, review_count=5)