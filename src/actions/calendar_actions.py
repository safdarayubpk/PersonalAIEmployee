"""Calendar actions (stub).

Silver tier stub — returns simulated results.
Real implementations deferred to Gold tier.
"""

from datetime import datetime, timezone


def create_event(title: str = "", start: str = "", end: str = "",
                 location: str = "", description: str = "",
                 **kwargs) -> dict:
    """Create a calendar event (stub).

    Args:
        title: Event title
        start: Start time (ISO 8601)
        end: End time (ISO 8601)
        location: Event location
        description: Event description

    Returns:
        dict with status, action, event details
    """
    return {
        "status": "stub",
        "action": "create_event",
        "title": title,
        "start": start,
        "end": end,
        "detail": f"Stub: would create event '{title}'",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def list_events(days: int = 7, **kwargs) -> dict:
    """List upcoming calendar events (stub).

    Args:
        days: Number of days to look ahead

    Returns:
        dict with status, action, events list
    """
    return {
        "status": "stub",
        "action": "list_events",
        "days": days,
        "events": [],
        "detail": f"Stub: would list events for next {days} days",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
