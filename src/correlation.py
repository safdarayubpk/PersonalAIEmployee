from __future__ import annotations

"""Correlation ID generation and propagation for end-to-end audit tracing.

Platinum format: corr-YYYY-MM-DD-XXXXXXXX (8 random hex chars)
Legacy format:   corr-YYYYMMDD-HHMMSS-XXXX (4 random hex chars)

Generated at watcher level, propagated through all components and logs.
The ID MUST be preserved (never regenerated) when a task crosses agents.
"""

import os
import re
from datetime import datetime, timezone

# Platinum format: corr-YYYY-MM-DD-XXXXXXXX
CORRELATION_ID_PATTERN = re.compile(r"^corr-\d{4}-\d{2}-\d{2}-[0-9a-f]{8}$")

# Legacy format: corr-YYYYMMDD-HHMMSS-XXXX (backward compatibility)
LEGACY_CORRELATION_ID_PATTERN = re.compile(r"^corr-\d{8}-\d{6}-[0-9a-f]{4}$")


def generate_correlation_id() -> str:
    """Generate a unique correlation ID in Platinum format.

    Format: corr-YYYY-MM-DD-XXXXXXXX where XXXXXXXX is 8 random hex chars.
    """
    now = datetime.now(timezone.utc)
    date_part = now.strftime("%Y-%m-%d")
    random_hex = os.urandom(4).hex()
    return f"corr-{date_part}-{random_hex}"


def is_valid_correlation_id(correlation_id: str) -> bool:
    """Check if a string matches either the Platinum or legacy format.

    Accepts both formats for backward compatibility with Gold-tier files.
    """
    if not correlation_id:
        return False
    return bool(
        CORRELATION_ID_PATTERN.match(correlation_id)
        or LEGACY_CORRELATION_ID_PATTERN.match(correlation_id)
    )


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
