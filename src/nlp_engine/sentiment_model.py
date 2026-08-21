# src/nlp_engine/sentiment_model.py
import logging
from transformers import pipeline
from cleaner import clean_text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# GPay Business Vectors (6 Core Aspects)
GPAY_ASPECTS = [
    "General Feedback",                   # Praise, general UI, app opinion, feedback
    "Transactions and Auto-Pay",          # Transfers, failed payments, mandates
    "Rewards, Cashback and Offers",       # Scratch cards, missing rewards, coupons
    "Account Security and Fraud Risk",    # Hacking, blocked account, fraud
    "Credit, Loans and CIBIL",            # Loans, credit score, CIBIL
    "App Performance and Bugs"            # Crashes, glitches, slow speed
]

# Aspects eligible for High Severity risk alerts
HIGH_SEVERITY_ASPECTS = [
    "Transactions and Auto-Pay",
    "Account Security and Fraud Risk",
    "Credit, Loans and CIBIL"
]

class NLPProcessor:
    """
    Dedicated class for Natural Language Processing.
    Completely decoupled from database operations.
    """
    def __init__(self):
        logging.info("Loading Hugging Face Models...")
        # Zero-shot classification to figure out the "Aspect"
        self.aspect_classifier = pipeline(
            "zero-shot-classification", 
            model="valhalla/distilbart-mnli-12-1" 
        )
        # Sentiment analysis to figure out the "Score"
        self.sentiment_analyzer = pipeline(
            "sentiment-analysis", 
            model="distilbert-base-uncased-finetuned-sst-2-english"
        )
        logging.info("Models loaded successfully.")

    def analyze_review(self, raw_text: str):
        """Processes a single review and returns Aspect, Confidence, and Sentiment."""
        clean_review = clean_text(raw_text)
        
        if not clean_review or len(clean_review) < 2:
            return None # Skip empty or meaningless reviews

        # Detect Sentiment
        sentiment_result = self.sentiment_analyzer(clean_review)[0]
        sentiment_label = sentiment_result['label'] # 'POSITIVE' or 'NEGATIVE'
        
        # Convert HuggingFace score (0 to 1) to Polarity (-1.0 to 1.0)
        base_score = sentiment_result['score']
        sentiment_score = base_score if sentiment_label == 'POSITIVE' else -base_score

        # Detect Aspect via Zero-Shot with Domain-Specific Hypothesis Template
        aspect_result = self.aspect_classifier(
            clean_review, 
            GPAY_ASPECTS,
            hypothesis_template="This review is about {}."
        )
        top_aspect = aspect_result['labels'][0]
        aspect_confidence = aspect_result['scores'][0]
        # Rely purely on model confidence (0.35 threshold) rather than arbitrary word count
        CONFIDENCE_THRESHOLD = 0.35
        if aspect_confidence < CONFIDENCE_THRESHOLD:
            top_aspect = "General Feedback"

        # Sentiment-Aware Severity Check
        # High severity requires BOTH a critical aspect AND a NEGATIVE sentiment score
        is_severity_high = (top_aspect in HIGH_SEVERITY_ASPECTS) and (sentiment_label == "NEGATIVE")

        return {
            "aspect": top_aspect,
            "aspect_confidence": round(aspect_confidence, 4),
            "sentiment_label": sentiment_label,
            "sentiment_score": round(sentiment_score, 4),
            "is_severity_high": is_severity_high,
            "review_length": len(clean_review)
        }

if __name__ == "__main__":
    # Local Testing block
    test_nlp = NLPProcessor()
    
    sample_1 = "OTP not working"
    sample_2 = "Google Pay prevented fraud successfully, amazing app"
    
    print(f"\nTest 1 ('{sample_1}'): {test_nlp.analyze_review(sample_1)}")
    print(f"\nTest 2 ('{sample_2}'): {test_nlp.analyze_review(sample_2)}")