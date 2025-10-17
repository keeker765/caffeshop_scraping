"""Runtime configuration helpers for the coffee shop scraping project."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

import yaml


@dataclass
class CityTarget:
    """Represents a single city to scrape."""

    name: str
    country: str
    region: str | None = None

    @property
    def display_name(self) -> str:
        """Return the human readable name for logging/reporting."""
        if self.region:
            return f"{self.name}, {self.region}, {self.country}"
        return f"{self.name}, {self.country}"


@dataclass
class ProjectSettings:
    """Top level project configuration."""

    google_api_key: str
    cities: List[CityTarget]
    request_delay_seconds: float = 1.5
    max_results_per_city: int = 120

    @classmethod
    def from_yaml(cls, path: Path) -> "ProjectSettings":
        """Create settings from a YAML file."""
        raw = yaml.safe_load(path.read_text())
        cities = [CityTarget(**item) for item in raw.get("cities", [])]
        return cls(
            google_api_key=raw["google_api_key"],
            request_delay_seconds=float(raw.get("request_delay_seconds", 1.5)),
            max_results_per_city=int(raw.get("max_results_per_city", 120)),
            cities=cities,
        )

    def city_names(self) -> Iterable[str]:
        return [city.display_name for city in self.cities]
