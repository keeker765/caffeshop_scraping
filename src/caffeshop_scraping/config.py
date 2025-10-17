"""Runtime configuration helpers for the coffee shop scraping project."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Optional

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

    google_api_key: Optional[str] = None
    cities: List[CityTarget] = field(default_factory=list)
    request_delay_seconds: float = 1.5
    max_results_per_city: int = 120
    demo_fixture_path: Optional[Path] = None

    @classmethod
    def from_yaml(cls, path: Path) -> "ProjectSettings":
        """Create settings from a YAML file."""
        raw = yaml.safe_load(path.read_text())
        cities = [CityTarget(**item) for item in raw.get("cities", [])]
        google_api_key = raw.get("google_api_key")
        if google_api_key is not None:
            google_api_key = str(google_api_key)
        demo_fixture = raw.get("demo_fixture_path")
        demo_fixture_path = Path(demo_fixture) if demo_fixture else None
        if not google_api_key and not demo_fixture_path:
            raise ValueError("Provide either a google_api_key or a demo_fixture_path in the config")
        return cls(
            google_api_key=google_api_key,
            request_delay_seconds=float(raw.get("request_delay_seconds", 1.5)),
            max_results_per_city=int(raw.get("max_results_per_city", 120)),
            cities=cities,
            demo_fixture_path=demo_fixture_path,
        )

    def city_names(self) -> Iterable[str]:
        return [city.display_name for city in self.cities]

    @property
    def is_demo(self) -> bool:
        """Return True when the configuration points to a demo fixture."""
        return self.demo_fixture_path is not None
