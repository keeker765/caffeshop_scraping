"""Thin client around the Google Maps Places/Geocoding APIs."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from time import sleep
from typing import Dict, Iterable, Iterator, List, Optional

import requests

LOGGER = logging.getLogger(__name__)
PLACES_SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
PLACE_DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"
GEOCODE_URL = "https://maps.googleapis.com/maps/api/geocode/json"


@dataclass
class GoogleMapsClient:
    """Simple client with minimal rate limiting."""

    api_key: str
    request_delay_seconds: float = 1.5
    session: requests.Session | None = None

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()

    def _get(self, url: str, params: Dict[str, object]) -> Dict[str, object]:
        """Perform a GET request with the API key injected."""
        params_with_key = dict(params)
        params_with_key["key"] = self.api_key
        LOGGER.debug("Requesting %s with params %s", url, params_with_key)
        response = self.session.get(url, params=params_with_key, timeout=30)
        response.raise_for_status()
        payload = response.json()
        status = payload.get("status")
        if status not in {"OK", "ZERO_RESULTS", "OVER_QUERY_LIMIT"}:
            raise RuntimeError(f"Unexpected status from Google API: {status} -> {payload}")
        if status == "OVER_QUERY_LIMIT":
            LOGGER.warning("Hit Google API query limit; sleeping before retry")
            sleep(max(self.request_delay_seconds * 2, 2.0))
        else:
            sleep(self.request_delay_seconds)
        return payload

    def geocode_city(self, city: str, country: str, region: Optional[str] = None) -> Optional[Dict[str, object]]:
        """Resolve a city's coordinates using the geocode API."""
        components = [f"country:{country}"]
        if region:
            components.append(f"administrative_area:{region}")
        payload = self._get(
            GEOCODE_URL,
            {
                "address": city,
                "components": "|".join(components),
            },
        )
        results = payload.get("results", [])
        if not results:
            LOGGER.warning("No geocoding result for %s, %s", city, country)
            return None
        return results[0]

    def iter_city_places(self, query: str, max_results: int = 120) -> Iterator[Dict[str, object]]:
        """Yield place search results for a city."""
        params = {"query": query, "type": "cafe"}
        fetched = 0
        next_page_token: Optional[str] = None
        while True:
            if next_page_token:
                params["pagetoken"] = next_page_token
            payload = self._get(PLACES_SEARCH_URL, params)
            for result in payload.get("results", []):
                yield result
                fetched += 1
                if fetched >= max_results:
                    return
            next_page_token = payload.get("next_page_token")
            if not next_page_token:
                return
            LOGGER.debug("Waiting for next page token to activate")
            sleep(2.0)

    def fetch_place_details(self, place_id: str, fields: Iterable[str]) -> Dict[str, object]:
        """Retrieve full place details."""
        payload = self._get(
            PLACE_DETAILS_URL,
            {
                "place_id": place_id,
                "fields": ",".join(fields),
            },
        )
        result = payload.get("result")
        if not result:
            raise RuntimeError(f"No details returned for place {place_id}")
        return result
