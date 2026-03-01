"""Correlation ID generation and propagation for end-to-end audit tracing.

Format: corr-YYYYMMDD-HHMMSS-XXXX (XXXX = 4 random hex chars)
Generated at watcher level, propagated through all components and logs.
"""

import os
import re
from datetime import datetime, timezone

# Pattern for validating correlation IDs
CORRELATION_ID_PATTERN = re.compile(r"^corr-\d{8}-\d{6}-[0-9a-f]{4}$")


def generate_correlation_id() -> str:
    """Generate a unique correlation ID.

    Format: corr-YYYYMMDD-HHMMSS-XXXX where XXXX is 4 random hex chars.
    """
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y%m%d-%H%M%S")
    random_hex = os.urandom(2).hex()
    return f"corr-{date_part}-{random_hex}"


def is_valid_correlation_id(correlation_id: str) -> bool:
    """Check if a string matches the correlation ID format."""
    return bool(CORRELATION_ID_PATTERN.match(correlation_id))


def extract_correlation_id(frontmatter: dict) -> str | None:
    """Extract correlation_id from a frontmatter dict, or None if missing."""
    return frontmatter.get("correlation_id")


def ensure_correlation_id(frontmatter: dict) -> tuple[str, bool]:
    """Ensure frontmatter has a correlation_id. Generate one if missing.

    Returns:
        Tuple of (correlation_id, was_generated). was_generated is True
        if the ID was created retroactively (legacy file support).
    """
    existing = extract_correlation_id(frontmatter)
    if existing and is_valid_correlation_id(existing):
        return existing, False
    new_id = generate_correlation_id()
    frontmatter["correlation_id"] = new_id
    return new_id, True
