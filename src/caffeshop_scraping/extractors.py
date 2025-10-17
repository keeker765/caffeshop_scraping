"""Utilities for extracting contact information from HTML."""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlparse

from bs4 import BeautifulSoup

LOGGER = logging.getLogger(__name__)
EMAIL_REGEX = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
SOCIAL_HOST_MAP = {
    "facebook.com": "facebook_url",
    "fb.com": "facebook_url",
    "instagram.com": "instagram_handle",
    "twitter.com": "twitter_url",
    "x.com": "twitter_url",
    "yelp.com": "yelp_url",
}


@dataclass
class PageExtraction:
    """Represents extracted contact information from a single page."""

    emails: List[str]
    email_to_name: Dict[str, Optional[str]]
    social_links: Dict[str, List[str]]


def normalize_email(email: str) -> str:
    return email.strip().lower()


def extract_emails(text: str) -> List[str]:
    """Return a de-duplicated list of emails from raw text."""
    emails = {normalize_email(match.group(0)) for match in EMAIL_REGEX.finditer(text)}
    return sorted(emails)


def extract_social_links(soup: BeautifulSoup) -> Dict[str, List[str]]:
    """Parse anchor tags and bucket them by platform."""
    buckets: Dict[str, List[str]] = defaultdict(list)
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        parsed = urlparse(href)
        netloc = parsed.netloc.lower()
        for host, field in SOCIAL_HOST_MAP.items():
            if host in netloc:
                if field == "instagram_handle":
                    handle = parsed.path.strip("/")
                    if handle:
                        buckets[field].append(handle)
                else:
                    buckets[field].append(href)
    return buckets


def parse_contact_page(html: str) -> PageExtraction:
    """Extract emails and social links from an HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    emails = extract_emails(soup.get_text(" "))
    social_links = extract_social_links(soup)
    email_to_name: Dict[str, Optional[str]] = {email: None for email in emails}

    # Attempt to infer names from simple patterns like "John – john@example.com"
    for text_node in soup.find_all(string=EMAIL_REGEX):
        email = normalize_email(text_node)
        parent_text = text_node.parent.get_text(" ") if text_node.parent else text_node
        before_email = parent_text.split(text_node, 1)[0]
        maybe_name = before_email.strip(" -:\n\t")
        if maybe_name and 0 < len(maybe_name.split()) <= 4:
            email_to_name[email] = maybe_name
    return PageExtraction(emails=emails, email_to_name=email_to_name, social_links=social_links)
