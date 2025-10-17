"""HTTP helpers for fetching business websites without triggering captchas."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Iterable, Optional

import requests

LOGGER = logging.getLogger(__name__)
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15"
)


@dataclass
class WebFetcher:
    """Simple HTTP client with back-off logic."""

    timeout: int = 20
    retry_statuses: tuple[int, ...] = (429, 503)
    max_retries: int = 3
    backoff_seconds: float = 3.0
    session: requests.Session | None = None

    def __post_init__(self) -> None:
        if self.session is None:
            self.session = requests.Session()
        self.session.headers.setdefault("User-Agent", USER_AGENT)

    def fetch(self, url: str) -> Optional[str]:
        """Fetch a single URL returning the response text."""
        for attempt in range(1, self.max_retries + 1):
            response = self.session.get(url, timeout=self.timeout)
            if response.status_code in self.retry_statuses:
                wait_time = self.backoff_seconds * attempt
                LOGGER.warning(
                    "Received %s from %s (attempt %s/%s); sleeping %.1fs",
                    response.status_code,
                    url,
                    attempt,
                    self.max_retries,
                    wait_time,
                )
                time.sleep(wait_time)
                continue
            if response.status_code >= 400:
                LOGGER.error("Failed to fetch %s: HTTP %s", url, response.status_code)
                return None
            return response.text
        LOGGER.error("Giving up on %s after %s retries", url, self.max_retries)
        return None
