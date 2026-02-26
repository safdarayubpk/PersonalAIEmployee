"""Social media actions (stub).

Silver tier stub — returns simulated results.
Real implementations deferred to Gold tier.
"""

from datetime import datetime, timezone


def post_social(platform: str = "twitter", content: str = "",
                **kwargs) -> dict:
    """Post content to a social media platform (stub).

    Args:
        platform: Target platform (twitter, linkedin, etc.)
        content: Post content text

    Returns:
        dict with status, action, platform, detail
    """
    return {
        "status": "stub",
        "action": "post_social",
        "platform": platform,
        "content_length": len(content),
        "detail": f"Stub: would post {len(content)} chars to {platform}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
