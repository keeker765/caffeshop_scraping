"""High level orchestration for the coffee shop scraping workflow."""
from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional

from .config import CityTarget, ProjectSettings
from .extractors import PageExtraction, parse_contact_page
from .google_maps import GoogleMapsClient
from .models import Business, EmailRecord
from .web import WebFetcher

LOGGER = logging.getLogger(__name__)
CONTACT_FIELDS = [
    "place_id",
    "name",
    "formatted_address",
    "international_phone_number",
    "formatted_phone_number",
    "opening_hours",
    "website",
    "url",
    "user_ratings_total",
    "rating",
]


def _format_address(place: Dict[str, object]) -> str:
    return str(place.get("formatted_address", "")).strip()


def _format_location(city: CityTarget) -> str:
    if city.region:
        return f"{city.name}, {city.region}, {city.country}"
    return f"{city.name}, {city.country}"


def _extract_opening_hours(place: Dict[str, object]) -> Optional[str]:
    opening_hours = place.get("opening_hours") or {}
    weekday_text = opening_hours.get("weekday_text")
    if weekday_text:
        return " | ".join(weekday_text)
    return None


def build_business(place: Dict[str, object], city: CityTarget) -> Business:
    """Convert a Google Places payload into our business dataclass."""
    phones: List[str] = []
    primary_phone: Optional[str] = None
    for key in ("international_phone_number", "formatted_phone_number"):
        value = place.get(key)
        if isinstance(value, str):
            if not primary_phone:
                primary_phone = value
            else:
                phones.append(value)
    opening_hours = _extract_opening_hours(place)
    business = Business(
        place_id=str(place["place_id"]),
        business_name=str(place.get("name", "")).strip(),
        location=_format_location(city),
        full_address=_format_address(place),
        phone=primary_phone,
        additional_phones=phones,
        google_maps_url=str(place.get("url") or "") or None,
        website_url=str(place.get("website") or "") or None,
        opening_hours=opening_hours,
        source_payload=place,
    )
    return business


def enrich_with_socials(business: Business, extraction: PageExtraction) -> None:
    """Update a business instance with social network data."""
    business.social_medias_raw = sorted({link for links in extraction.social_links.values() for link in links})
    if extraction.social_links.get("facebook_url"):
        business.facebook_url = extraction.social_links["facebook_url"][0]
    if extraction.social_links.get("instagram_handle"):
        business.instagram_handle = extraction.social_links["instagram_handle"][0]
    if extraction.social_links.get("twitter_url"):
        business.twitter_url = extraction.social_links["twitter_url"][0]
    if extraction.social_links.get("yelp_url"):
        business.yelp_url = extraction.social_links["yelp_url"][0]


def expand_email_records(
    business: Business,
    extraction: PageExtraction,
    source_url: str,
    scrape_notes: str = "website",
) -> List[EmailRecord]:
    """Generate EmailRecord entries for a business given extracted emails."""
    records: List[EmailRecord] = []
    for email in extraction.emails:
        record = EmailRecord(
            business=business,
            email=email,
            email_owner_name=extraction.email_to_name.get(email),
            source_url=source_url,
            scrape_notes=scrape_notes,
            discovered_at=datetime.utcnow(),
        )
        records.append(record)
    return records


def iter_city_businesses(
    client: GoogleMapsClient, city: CityTarget, max_results: int
) -> Iterator[Business]:
    """Iterate over businesses for a city."""
    query = f"coffee shops in {city.display_name}"
    fields = CONTACT_FIELDS
    for place_summary in client.iter_city_places(query, max_results=max_results):
        place_id = place_summary.get("place_id")
        if not place_id:
            continue
        place_details = client.fetch_place_details(place_id, fields)
        yield build_business(place_details, city)


def process_city(
    client: GoogleMapsClient,
    fetcher: WebFetcher,
    city: CityTarget,
    max_results: int,
) -> List[EmailRecord]:
    """Process all businesses for a city and return email records."""
    records: List[EmailRecord] = []
    for business in iter_city_businesses(client, city, max_results=max_results):
        if not business.website_url:
            continue
        html = fetcher.fetch(business.website_url)
        if not html:
            continue
        extraction = parse_contact_page(html)
        enrich_with_socials(business, extraction)
        city_records = expand_email_records(business, extraction, business.website_url)
        records.extend(city_records)
    return records


def write_email_records(records: Iterable[EmailRecord], output_csv: Path) -> None:
    """Write email records to disk."""
    rows = [record.to_row() for record in records]
    if not rows:
        LOGGER.warning("No email records to export")
        return
    fieldnames = list(rows[0].keys())
    with output_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    LOGGER.info("Wrote %s rows to %s", len(rows), output_csv)


def run_pipeline(settings: ProjectSettings, output_csv: Path) -> None:
    """Top level orchestration helper."""
    if settings.is_demo:
        run_demo_pipeline(settings, output_csv)
        return
    if not settings.google_api_key:
        raise ValueError("google_api_key is required when not running in demo mode")
    client = GoogleMapsClient(api_key=settings.google_api_key, request_delay_seconds=settings.request_delay_seconds)
    fetcher = WebFetcher()
    all_records: List[EmailRecord] = []
    for city in settings.cities:
        LOGGER.info("Processing %s", city.display_name)
        city_records = process_city(client, fetcher, city, settings.max_results_per_city)
        LOGGER.info("%s produced %s email rows", city.display_name, len(city_records))
        all_records.extend(city_records)
    write_email_records(all_records, output_csv)


def _build_business_from_fixture(data: Dict[str, Any]) -> Business:
    """Create a Business instance from fixture data."""
    business_kwargs = dict(data)
    business_kwargs.setdefault("additional_phones", [])
    business_kwargs.setdefault("social_medias_raw", [])
    business_kwargs.setdefault("source_payload", data)
    return Business(**business_kwargs)


def load_demo_fixture(path: Path) -> List[Dict[str, Any]]:
    """Load a demo fixture JSON file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Demo fixture must contain a list of entries")
    return payload


def run_demo_pipeline(settings: ProjectSettings, output_csv: Path) -> None:
    """Generate email records using an offline demo fixture."""
    assert settings.demo_fixture_path is not None, "Demo mode requires a fixture path"
    fixture_entries = load_demo_fixture(settings.demo_fixture_path)
    all_records: List[EmailRecord] = []
    for entry in fixture_entries:
        business_data = entry.get("business") or {}
        if not business_data:
            LOGGER.warning("Skipping fixture entry without business data: %s", entry)
            continue
        business = _build_business_from_fixture(business_data)
        html = entry.get("html")
        if not isinstance(html, str):
            LOGGER.warning("Skipping fixture entry without HTML content for %s", business.business_name)
            continue
        extraction = parse_contact_page(html)
        enrich_with_socials(business, extraction)
        overrides = entry.get("email_owner_overrides") or {}
        for email, owner in overrides.items():
            if owner:
                normalized = email.strip().lower()
                if normalized in extraction.email_to_name:
                    extraction.email_to_name[normalized] = owner
        source_url = entry.get("source_url") or business.website_url or "demo"
        notes = entry.get("scrape_notes") or "demo_fixture"
        records = expand_email_records(business, extraction, source_url, scrape_notes=notes)
        all_records.extend(records)
    write_email_records(all_records, output_csv)
