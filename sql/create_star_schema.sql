-- ============================================================
-- Star Schema DDL for GPay Review Sentiment Analysis
-- Reconstructed directly from live Supabase schema (information_schema)
-- ============================================================

-- Dimension: the 6 fixed GPay aspect categories
CREATE TABLE dim_aspect (
    aspect_id     SERIAL PRIMARY KEY,
    aspect_name   TEXT UNIQUE NOT NULL,
    category      TEXT
);

-- Dimension: standard date table
CREATE TABLE dim_date (
    date_id   SERIAL PRIMARY KEY,
    date      DATE UNIQUE NOT NULL,
    week      INTEGER,
    month     INTEGER,
    quarter   INTEGER,
    year      INTEGER
);

-- Dimension: one row per review's descriptive info
CREATE TABLE dim_review (
    review_id           TEXT PRIMARY KEY,
    review_date         DATE,
    review_text         TEXT,
    star_rating         INTEGER,
    app_version         TEXT,
    app_version_major   TEXT,   -- derived: major version, low-volume/legacy versions bucketed
    thumbs_up_count      INTEGER,
    review_length       INTEGER,
    source              TEXT DEFAULT 'Play Store'
);

-- Fact: one row per review's NLP result
CREATE TABLE fact_review_sentiment (
    review_id           TEXT PRIMARY KEY REFERENCES dim_review(review_id),
    aspect_id           INTEGER REFERENCES dim_aspect(aspect_id),
    date_id             INTEGER REFERENCES dim_date(date_id),
    sentiment_score     NUMERIC,
    sentiment_label     TEXT,
    aspect_confidence   NUMERIC,
    is_severity_high    BOOLEAN
);

-- Staging layer: raw scraped data preserved before any NLP processing
CREATE TABLE staging_raw_reviews (
    review_id         TEXT PRIMARY KEY,
    review_text       TEXT,
    star_rating       INTEGER,
    app_version       TEXT,
    thumbs_up_count   INTEGER,
    review_date       DATE,
    scraped_at        TIMESTAMP DEFAULT NOW()
);

-- Seed data: the 6 fixed aspect categories
INSERT INTO dim_aspect (aspect_name, category) VALUES
('General Feedback', 'General'),
('Transactions and Auto-Pay', 'Payments'),
('Rewards, Cashback and Offers', 'Incentives'),
('Account Security and Fraud Risk', 'Security'),
('Credit, Loans and CIBIL', 'Credit'),
('App Performance and Bugs', 'Technical')
ON CONFLICT (aspect_name) DO NOTHING;