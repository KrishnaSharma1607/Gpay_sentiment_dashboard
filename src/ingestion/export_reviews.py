import csv
import logging
import os
from google_play_scraper import Sort, reviews

logging.basicConfig(level=logging.INFO, format='\n%(asctime)s - EXPORTER - %(message)s')

def export_reviews_to_csv(app_package="com.google.android.apps.nbu.paisa.user", count=200, output_file="sample_reviews1.csv"):
    logging.info(f"Fetching {count} latest reviews for {app_package}...")
    
    try:
        raw_reviews, _ = reviews(
            app_package,
            lang='en',
            country='in',
            sort=Sort.NEWEST,
            count=count
        )
        
        if not raw_reviews:
            logging.warning("No reviews found.")
            return

        headers = [
            'reviewId', 'userName', 'content', 'score', 'at', 
            'appVersion', 'thumbsUpCount', 'replyContent', 'repliedAt'
        ]

        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", output_file)

        with open(filepath, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=headers)
            writer.writeheader()
            
            for review in raw_reviews:
                writer.writerow({
                    'reviewId': review.get('reviewId'),
                    'userName': review.get('userName'),
                    'content': review.get('content'),
                    'score': review.get('score'),
                    'at': review.get('at'),
                    'appVersion': review.get('appVersion') or review.get('reviewCreatedVersion', 'Unknown'),
                    'thumbsUpCount': review.get('thumbsUpCount', 0),
                    'replyContent': review.get('replyContent'),
                    'repliedAt': review.get('repliedAt')
                })
                
        logging.info(f"SUCCESS: Exported reviews to {filepath}")

    except Exception as e:
        logging.error(f"Failed to export reviews: {e}")

if __name__ == "__main__":
    export_reviews_to_csv(count=200)