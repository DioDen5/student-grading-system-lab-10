"""Production logging configuration."""

import logging


def configure_logging(level: str) -> None:
    """Configure structured, timestamped application logging."""
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )
