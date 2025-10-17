# Coffee Shop Scraping Pilot

This repository contains a reproducible workflow for collecting high-quality contact data for coffee shops across multiple cities. The pilot focuses on 10 cities across the United States, Canada, and Europe.

## Features

- Google Maps Places and Details API integration to enumerate coffee shops by city.
- Website fetching pipeline with retry/backoff logic to avoid captchas.
- Email and social media extraction from business websites using BeautifulSoup.
- CSV export where each row contains one email address plus the associated business metadata.

## Project Structure

```
├── config.sample.yaml       # Example configuration file (copy and update with your API key)
├── requirements.txt         # Python dependencies
└── src/
    ├── main.py              # CLI entry point
    └── caffeshop_scraping/
        ├── __init__.py
        ├── config.py        # Settings loader and city definitions
        ├── extractors.py    # HTML parsing and contact extraction helpers
        ├── google_maps.py   # Google Maps API client
        ├── models.py        # Dataclasses for business and email rows
        ├── pipeline.py      # Orchestration logic
        └── web.py           # Website fetching utilities
```

## Getting Started

1. **Install dependencies**

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configure API access**

   - Copy `config.sample.yaml` to `config.yaml`.
   - Replace `YOUR_GOOGLE_API_KEY` with a valid Google Maps Places API key.
   - Adjust `request_delay_seconds` if you encounter captcha challenges. Start at 1.5–2 seconds.
   - Update the `cities` list if you need to target different locations.

3. **Run the pipeline**

   ```bash
   python -m src.main config.yaml --output output/coffee_shops.csv
   ```

   The command will:

   - Enumerate coffee shops for each city via the Google Places API.
   - Fetch each business website sequentially with retry/backoff.
   - Parse contact information, social media links, and emails.
   - Export a CSV file with one row per email address.

4. **Quality assurance**

   - Inspect the generated CSV and verify sample rows.
   - Review the logs for warnings about failed website fetches or missing emails.
   - For manual QA, check a subset of businesses by visiting their websites to confirm accuracy.

## Notes on Captcha Avoidance

- The pipeline uses a desktop Safari user agent and configurable delays between Google API requests.
- Website fetching is sequential with exponential backoff for 429/503 responses, minimizing rapid-fire requests.
- Google Maps scraping relies on official APIs to reduce the chance of encountering captchas. If the rate limits are exceeded, increase `request_delay_seconds` or add per-city scheduling.

## Extending the Workflow

- Integrate an email verification API in a post-processing step to flag invalid emails.
- Add proxy rotation if you expand beyond the pilot scope.
- Persist intermediate results (e.g., JSON dumps) to make reruns idempotent.
- Hook into Google Sheets API to upload the final CSV automatically.

## Disclaimer

Running this pipeline requires adherence to Google Maps Platform Terms of Service and the robots.txt policies of scraped websites. Always obtain the necessary permissions before executing large-scale scraping.
