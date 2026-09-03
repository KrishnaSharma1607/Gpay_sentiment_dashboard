# GPay Review Sentiment Analysis Pipeline

An end-to-end data pipeline that scrapes Google Pay reviews from the Play Store, runs them through an NLP sentiment and aspect-classification pipeline, warehouses the results in a PostgreSQL star schema, and visualizes the findings in an interactive 3-page Power BI dashboard.

## Overview

This project analyzes ~16,000 Google Pay reviews to understand what users are actually complaining about and how severe those complaints are. Each review is classified into one of 6 business-relevant categories (Transactions, Security, Rewards, Credit, App Performance, or General Feedback) and scored for sentiment using pre-trained Hugging Face transformer models. The processed data is normalized into a Kimball-style star schema, with four analytical SQL views computing severity scores, rolling sentiment trends, and NLP validation metrics using CTEs and window functions. The final output is a branded, interactive Power BI dashboard supporting drill-through, custom tooltips, and dynamic DAX measures.

## Pipeline

<img width="853" height="1843" alt="ChatGPT Image Sep 4, 2026, 03_03_30 AM" src="https://github.com/user-attachments/assets/d22a8cc1-20cb-4b70-8e85-c453f9d75509" />


1. **Ingestion** — `google-play-scraper` pulls reviews (text, rating, app version, date) for the Google Pay app.
2. **Staging** — Raw review data is preserved as-is before any processing, for audit purposes.
3. **NLP processing** — Each review passes through two Hugging Face models: a zero-shot classifier assigning one of 6 fixed aspect categories (with a confidence score), and a sentiment classifier scoring tone from -1 to +1. Reviews below a confidence threshold default to "General Feedback."
4. **Data warehousing** — Results are normalized into a star schema in PostgreSQL (hosted on Supabase): `dim_review`, `dim_aspect`, `dim_date`, and `fact_review_sentiment`.
5. **Analytical SQL layer** — Four views built on top of the warehouse compute severity-weighted complaint scores, sentiment/rating mismatch detection, rolling sentiment trends, and monthly aspect rankings, using CTEs and window functions (`RANK() OVER PARTITION BY`, `FILTER`, `ROWS BETWEEN`).
6. **Visualization** — Power BI Desktop (Import mode) connects to the warehouse and views, modeling relationships and presenting a 3-page dashboard: Executive Overview, Aspect Deep Dive, and Release Impact.

## Tech stack

| Layer | Tools |
|---|---|
| Scraping & orchestration | Python, `google-play-scraper` |
| NLP | Hugging Face Transformers (zero-shot classification, sentiment analysis) |
| Data warehouse | PostgreSQL (Supabase) |
| Analytics layer | SQL (CTEs, window functions) |
| Visualization | Power BI Desktop (Power Query, DAX, drill-through, custom tooltips) |
| Version control | Git, GitHub |

## Repository structure

```
├── docs/
│   └── pipeline_diagram.svg          # Architecture diagram (embedded above)
├── sql/
│   └── create_star_schema.sql        # DDL for the star schema tables
├── src/
│   ├── ingestion/
│   │   ├── playstore_scraper.py      # Scrapes reviews from the Play Store
│   │   ├── db_loader.py
│   │   └── export_reviews.py
│   ├── nlp_engine/
│   │   ├── sentiment_model.py        # Aspect classification + sentiment scoring
│   │   ├── batch_scorer.py
│   │   └── cleaner.py
│   ├── warehousing/
│   │   └── build_star_schema.py      # Main ETL: scrape → NLP → star schema
│   └── run_pipeline.py               # Incremental daily pipeline runner
├── analytics/
│   ├── data_samples/                 # Sample CSVs at each pipeline stage
│   ├── sql_views/                    # The 4 analytical SQL views, as files
│   └── dashboard/
│       └── Gpay_Sentiment_Dashboard.pbix
├── .gitignore
├── requirements.txt
└── README.md
```

## Dashboard preview

### Page 1 — Executive Overview
Full-dataset snapshot: 5 KPI cards (Total Reviews, Avg. Sentiment, % Negative, % High Severity, Avg. Star Rating), 5 slicers, a DAX-driven 7-day rolling sentiment trend, an aspect breakdown donut with a custom drill-down tooltip, a sentiment-by-aspect comparison, and a data-backed Key Insights panel.

### Page 2 — Aspect Deep Dive
Investigates model trustworthiness and severity by category: a severity ranking (via `RANKX` over `ALL()`), a scatter plot of user rating vs. model sentiment, a rating-sentiment mismatch breakdown built on `vw_sentiment_rating_mismatch`, and a table of top flagged reviews. Includes custom measures using `FILTER`+`RELATED` and `SWITCH(TRUE())`, plus drill-through from Page 1's aspect chart.

### Page 3 - Release Impact
sentiment trend by app version, monthly complaint ranking

The `.pbix` file is available in `analytics/dashboard/`.

## Future scope

- **Multilingual sentiment support** — the current model (`distilbert-base-uncased-finetuned-sst-2-english`) is English-only. Reviews written in Hindi or Hinglish likely receive less reliable sentiment scores. A natural next step is swapping in a multilingual model such as XLM-RoBERTa to properly handle mixed-language review text.
- **Longer historical range** — the current dataset spans ~4-5 months due to how far back Play Store scraping can practically reach for a high-volume app. Running the scraper on a recurring schedule (e.g. weekly) would build up a multi-year archive over time, enabling true year-over-year trend analysis.
- **Scheduled refresh** — the dashboard currently runs in Import mode with manual refresh. Publishing to Power BI Service with a scheduled refresh (or a cloud-hosted trigger for the Python pipeline) would make the dashboard update automatically as new reviews come in.
