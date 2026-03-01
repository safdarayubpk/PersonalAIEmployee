"""Tests for social media content validation."""

import json
import sys
from pathlib import Path

# Load platform config directly to test validation logic
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "social-platforms.json"
_PLATFORMS = json.loads(_CONFIG_PATH.read_text()).get("platforms", {})


def _validate_content(content: str, platform: str) -> dict | None:
    """Replicate validation logic from social_server for isolated testing."""
    config = _PLATFORMS.get(platform, {})
    max_chars = config.get("max_chars", 63206)
    if not content or not content.strip():
        return {"error": "Content cannot be empty", "platform": platform}
    if len(content) > max_chars:
        return {
            "error": f"Content exceeds {platform} character limit",
            "platform": platform,
            "char_count": len(content),
            "max_chars": max_chars,
            "excess": len(content) - max_chars,
        }
    return None


def test_valid_twitter():
    assert _validate_content("Hello world!", "twitter") is None


def test_twitter_exact_limit():
    assert _validate_content("x" * 280, "twitter") is None


def test_twitter_over_limit():
    result = _validate_content("x" * 281, "twitter")
    assert result is not None
    assert result["char_count"] == 281
    assert result["max_chars"] == 280
    assert result["excess"] == 1


def test_facebook_large_post():
    assert _validate_content("x" * 63206, "facebook") is None


def test_facebook_over_limit():
    result = _validate_content("x" * 63207, "facebook")
    assert result is not None


def test_instagram_limit():
    assert _validate_content("x" * 2200, "instagram") is None


def test_instagram_over_limit():
    result = _validate_content("x" * 2201, "instagram")
    assert result is not None


def test_empty_content():
    result = _validate_content("", "twitter")
    assert result is not None
    assert "empty" in result["error"].lower()


def test_whitespace_only():
    result = _validate_content("   ", "twitter")
    assert result is not None


if __name__ == "__main__":
    test_valid_twitter()
    test_twitter_exact_limit()
    test_twitter_over_limit()
    test_facebook_large_post()
    test_facebook_over_limit()
    test_instagram_limit()
    test_instagram_over_limit()
    test_empty_content()
    test_whitespace_only()
    print("All content validator tests passed!")
