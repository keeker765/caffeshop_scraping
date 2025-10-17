"""Shared data models used across the scraping pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Business:
    """Represents core metadata about a coffee shop."""

    place_id: str
    business_name: str
    location: str
    full_address: str
    phone: Optional[str]
    additional_phones: List[str] = field(default_factory=list)
    google_maps_url: Optional[str] = None
    website_url: Optional[str] = None
    opening_hours: Optional[str] = None
    google_knowledge_url: Optional[str] = None
    social_medias_raw: List[str] = field(default_factory=list)
    facebook_url: Optional[str] = None
    instagram_handle: Optional[str] = None
    twitter_url: Optional[str] = None
    yelp_url: Optional[str] = None
    source_payload: Dict[str, object] = field(default_factory=dict)


@dataclass
class EmailRecord:
    """Represents a row in the exported dataset (one email per row)."""

    business: Business
    email: str
    email_owner_name: Optional[str]
    source_url: str
    scrape_notes: Optional[str]
    discovered_at: datetime

    def to_row(self) -> Dict[str, object]:
        """Transform the record into a flat dictionary for CSV export."""
        base = {
            "business_name": self.business.business_name,
            "instagram_handle": self.business.instagram_handle,
            "location": self.business.location,
            "full_address": self.business.full_address,
            "phone": self.business.phone,
            "additional_phones": ", ".join(self.business.additional_phones),
            "google_maps_url": self.business.google_maps_url,
            "website_url": self.business.website_url,
            "opening_hours": self.business.opening_hours,
            "google_knowledge_url": self.business.google_knowledge_url,
            "social_medias_raw": ", ".join(self.business.social_medias_raw),
            "facebook_url": self.business.facebook_url,
            "twitter_url": self.business.twitter_url,
            "yelp_url": self.business.yelp_url,
            "email": self.email,
            "email_owner_name": self.email_owner_name,
            "source_url": self.source_url,
            "scrape_notes": self.scrape_notes,
            "discovered_at": self.discovered_at.isoformat(),
        }
        return base
