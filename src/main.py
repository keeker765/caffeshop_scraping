"""Command line interface for the coffee shop scraping pilot pipeline."""
from __future__ import annotations

import argparse
import logging
from pathlib import Path

from caffeshop_scraping.config import ProjectSettings
from caffeshop_scraping.pipeline import run_pipeline

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Coffee shop scraping pipeline")
    parser.add_argument("config", type=Path, help="Path to YAML configuration file")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/cafes.csv"),
        help="Path to write the resulting CSV file",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging verbosity",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    logging.basicConfig(level=args.log_level, format=LOG_FORMAT)
    settings = ProjectSettings.from_yaml(args.config)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    run_pipeline(settings, args.output)


if __name__ == "__main__":
    main()
