import re

# Data cleaning steps- standardize text, remove URLs/emails/mentions/HTML, normalize whitespace,
# and retain only lowercase alphanumeric characters with basic punctuation for NLP preprocessing.
def clean_text(raw_text: str) -> str:
    text = raw_text.lower()
    text = re.sub(r'http\S+|www\.\S+', '', text)
    text = re.sub(r'\S+@\S+', '', text)
    text = re.sub(r'@\w+', '', text)
    text = re.sub(r'<.*?>', '', text)
    text = re.sub(r'[\n\r]+', ' ', text)
    text = re.sub(r"[^a-z0-9\s.,!?']", '', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text

if __name__ == "__main__":
    # Local Testing
    messy_review = "  WORST APP EVER!!!! 😡 My money got deducted but not credited. \n\n Contact me at angryuser@email.com or visit http://fixit.com @PhonePeSupport   "
    cleaned = clean_text(messy_review)
    print(f"Original: {messy_review}")
    print(f"Cleaned:  {cleaned}")