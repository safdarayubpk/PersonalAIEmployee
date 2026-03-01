"""MCP Social Media Server — Facebook, Instagram, Twitter/X integration.

Tools: social.post_facebook (sensitive), social.post_instagram (sensitive),
       social.post_twitter (sensitive), social.weekly_summary (routine)
Transport: stdio
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP
from base_server import (
    get_vault_path, is_dry_run,
    log_tool_call, create_pending_approval, make_response,
    get_circuit_breaker, check_service_available,
)

server = FastMCP("fte-social")

# Load platform config
_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "social-platforms.json"
_PLATFORMS = {}
if _CONFIG_PATH.exists():
    _PLATFORMS = json.loads(_CONFIG_PATH.read_text()).get("platforms", {})


def _validate_content(content: str, platform: str) -> dict | None:
    """Validate content against platform character limits.

    Returns None if valid, or error dict if invalid.
    """
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


@server.tool()
def social_post_facebook(content: str, link: str = "",
                         approval_ref: str = "",
                         correlation_id: str = "") -> dict:
    """Publish a post to a configured Facebook Page. Requires HITL approval.

    Args:
        content: Post text (max 63,206 chars)
        link: URL to attach (optional)
        approval_ref: Path to approved file in Approved/ folder
        correlation_id: Correlation ID for audit tracing
    """
    # Validate content
    validation = _validate_content(content, "facebook")
    if validation:
        log_tool_call("social", "social.post_facebook", "validation_error", "failure",
                      validation["error"], correlation_id,
                      params={"char_count": len(content)})
        return make_response("validation_error", "social.post_facebook",
                             correlation_id, **validation)

    params = {"content": content[:100] + "...", "link": link,
              "char_count": len(content), "platform": "facebook"}

    if is_dry_run():
        log_tool_call("social", "social.post_facebook", "dry_run", "success",
                      f"Would post to Facebook Page: '{content[:50]}...'",
                      correlation_id, params=params)
        return make_response("dry_run", "social.post_facebook", correlation_id,
                             platform="facebook", char_count=len(content),
                             detail=f"Would post to Facebook Page: '{content[:50]}...'")

    if not approval_ref:
        approval_file = create_pending_approval("social.post_facebook",
                                                 {"content": content, "link": link},
                                                 correlation_id)
        log_tool_call("social", "social.post_facebook", "hitl_blocked", "skipped",
                      "HITL gate: approval required for Facebook post",
                      correlation_id, params=params)
        return make_response("pending_approval", "social.post_facebook",
                             correlation_id, approval_file=approval_file)

    # Circuit breaker check
    available, err = check_service_available("facebook")
    if not available:
        return make_response("service_degraded", "social.post_facebook",
                             correlation_id, detail="Facebook service is degraded.")

    # Live post
    cb = get_circuit_breaker("facebook")
    try:
        import requests
        page_id = os.environ.get("FACEBOOK_PAGE_ID", "")
        access_token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
        if not page_id or not access_token:
            raise ValueError("FACEBOOK_PAGE_ID and FACEBOOK_ACCESS_TOKEN must be set")

        api_version = _PLATFORMS.get("facebook", {}).get("api_version", "v19.0")
        url = f"https://graph.facebook.com/{api_version}/{page_id}/feed"
        data = {"message": content, "access_token": access_token}
        if link:
            data["link"] = link

        resp = requests.post(url, data=data, timeout=30)
        if resp.status_code == 401:
            cb.record_failure("401 Unauthorized", non_retryable=True)
            return make_response("error", "social.post_facebook", correlation_id,
                                 detail="Facebook authentication failed (401)")
        if resp.status_code == 429:
            cb.record_failure("Rate limited")
            return make_response("rate_limited", "social.post_facebook", correlation_id,
                                 retry_after_seconds=900, detail="Facebook rate limit hit")
        resp.raise_for_status()
        post_id = resp.json().get("id", "")

        cb.record_success()
        log_tool_call("social", "social.post_facebook", "success", "success",
                      f"Published to Facebook: {post_id}", correlation_id,
                      params=params, result={"post_id": post_id})
        return make_response("success", "social.post_facebook", correlation_id,
                             platform="facebook", post_id=post_id,
                             published_at=datetime.now(timezone.utc).isoformat())

    except Exception as e:
        cb.record_failure(str(e))
        log_tool_call("social", "social.post_facebook", "failure", "failure",
                      f"Facebook post failed: {e}", correlation_id, params=params)
        return make_response("error", "social.post_facebook", correlation_id,
                             detail=f"Facebook post failed: {e}")


@server.tool()
def social_post_instagram(caption: str, image_url: str,
                          approval_ref: str = "",
                          correlation_id: str = "") -> dict:
    """Publish a post to Instagram Business account. Requires image URL and HITL approval.

    Args:
        caption: Post caption (max 2,200 chars)
        image_url: Publicly accessible image URL (JPG/PNG, max 8MB)
        approval_ref: Path to approved file in Approved/ folder
        correlation_id: Correlation ID for audit tracing
    """
    validation = _validate_content(caption, "instagram")
    if validation:
        log_tool_call("social", "social.post_instagram", "validation_error", "failure",
                      validation["error"], correlation_id)
        return make_response("validation_error", "social.post_instagram",
                             correlation_id, **validation)

    if not image_url:
        return make_response("validation_error", "social.post_instagram",
                             correlation_id,
                             error="image_url is required for Instagram posts")

    params = {"caption": caption[:100] + "...", "image_url": image_url,
              "platform": "instagram"}

    if is_dry_run():
        log_tool_call("social", "social.post_instagram", "dry_run", "success",
                      f"Would post to Instagram: '{caption[:50]}...'",
                      correlation_id, params=params)
        return make_response("dry_run", "social.post_instagram", correlation_id,
                             platform="instagram", char_count=len(caption),
                             detail=f"Would post to Instagram: '{caption[:50]}...'")

    if not approval_ref:
        approval_file = create_pending_approval("social.post_instagram",
                                                 {"caption": caption, "image_url": image_url},
                                                 correlation_id)
        log_tool_call("social", "social.post_instagram", "hitl_blocked", "skipped",
                      "HITL gate: approval required for Instagram post",
                      correlation_id, params=params)
        return make_response("pending_approval", "social.post_instagram",
                             correlation_id, approval_file=approval_file)

    # Circuit breaker check
    available, err = check_service_available("instagram")
    if not available:
        return make_response("service_degraded", "social.post_instagram",
                             correlation_id, detail="Instagram service is degraded.")

    # Live post — two-step container→publish
    cb_ig = get_circuit_breaker("instagram")
    try:
        import requests
        ig_id = os.environ.get("INSTAGRAM_BUSINESS_ID", "")
        access_token = os.environ.get("FACEBOOK_ACCESS_TOKEN", "")
        if not ig_id or not access_token:
            raise ValueError("INSTAGRAM_BUSINESS_ID and FACEBOOK_ACCESS_TOKEN must be set")

        api_version = _PLATFORMS.get("instagram", {}).get("api_version", "v19.0")

        # Step 1: Create media container
        create_url = f"https://graph.instagram.com/{api_version}/{ig_id}/media"
        create_resp = requests.post(create_url, data={
            "image_url": image_url, "caption": caption,
            "access_token": access_token,
        }, timeout=30)
        create_resp.raise_for_status()
        container_id = create_resp.json().get("id", "")

        # Step 2: Publish
        publish_url = f"https://graph.instagram.com/{api_version}/{ig_id}/media_publish"
        publish_resp = requests.post(publish_url, data={
            "creation_id": container_id, "access_token": access_token,
        }, timeout=30)
        publish_resp.raise_for_status()
        post_id = publish_resp.json().get("id", "")

        cb_ig.record_success()
        log_tool_call("social", "social.post_instagram", "success", "success",
                      f"Published to Instagram: {post_id}", correlation_id,
                      params=params, result={"post_id": post_id})
        return make_response("success", "social.post_instagram", correlation_id,
                             platform="instagram", post_id=post_id,
                             published_at=datetime.now(timezone.utc).isoformat())

    except Exception as e:
        cb_ig.record_failure(str(e))
        log_tool_call("social", "social.post_instagram", "failure", "failure",
                      f"Instagram post failed: {e}", correlation_id, params=params)
        return make_response("error", "social.post_instagram", correlation_id,
                             detail=f"Instagram post failed: {e}")


@server.tool()
def social_post_twitter(content: str, approval_ref: str = "",
                        correlation_id: str = "") -> dict:
    """Publish a tweet to Twitter/X. Requires HITL approval.

    Args:
        content: Tweet text (max 280 chars)
        approval_ref: Path to approved file in Approved/ folder
        correlation_id: Correlation ID for audit tracing
    """
    validation = _validate_content(content, "twitter")
    if validation:
        log_tool_call("social", "social.post_twitter", "validation_error", "failure",
                      validation["error"], correlation_id)
        return make_response("validation_error", "social.post_twitter",
                             correlation_id, **validation)

    params = {"content": content, "platform": "twitter", "char_count": len(content)}

    if is_dry_run():
        log_tool_call("social", "social.post_twitter", "dry_run", "success",
                      f"Would tweet: '{content[:50]}...'",
                      correlation_id, params=params)
        return make_response("dry_run", "social.post_twitter", correlation_id,
                             platform="twitter", char_count=len(content),
                             detail=f"Would tweet: '{content[:50]}...'")

    if not approval_ref:
        approval_file = create_pending_approval("social.post_twitter",
                                                 {"content": content},
                                                 correlation_id)
        log_tool_call("social", "social.post_twitter", "hitl_blocked", "skipped",
                      "HITL gate: approval required for tweet",
                      correlation_id, params=params)
        return make_response("pending_approval", "social.post_twitter",
                             correlation_id, approval_file=approval_file)

    # Circuit breaker check
    available, err = check_service_available("twitter")
    if not available:
        return make_response("service_degraded", "social.post_twitter",
                             correlation_id, detail="Twitter service is degraded.")

    # Live tweet
    cb_tw = get_circuit_breaker("twitter")
    try:
        import tweepy
        client = tweepy.Client(
            consumer_key=os.environ.get("TWITTER_API_KEY", ""),
            consumer_secret=os.environ.get("TWITTER_API_SECRET", ""),
            access_token=os.environ.get("TWITTER_ACCESS_TOKEN", ""),
            access_token_secret=os.environ.get("TWITTER_ACCESS_TOKEN_SECRET", ""),
            wait_on_rate_limit=True,
        )
        response = client.create_tweet(text=content)
        tweet_id = str(response.data.get("id", "")) if response.data else ""

        cb_tw.record_success()
        log_tool_call("social", "social.post_twitter", "success", "success",
                      f"Tweet published: {tweet_id}", correlation_id,
                      params=params, result={"tweet_id": tweet_id})
        return make_response("success", "social.post_twitter", correlation_id,
                             platform="twitter", tweet_id=tweet_id,
                             published_at=datetime.now(timezone.utc).isoformat())

    except tweepy.TooManyRequests:
        cb_tw.record_failure("Rate limited")
        log_tool_call("social", "social.post_twitter", "rate_limited", "failure",
                      "Twitter rate limit hit", correlation_id, params=params)
        return make_response("rate_limited", "social.post_twitter", correlation_id,
                             retry_after_seconds=900,
                             detail="Twitter rate limit hit. Retry after 15 minutes.")

    except Exception as e:
        non_retryable = "401" in str(e) or "Unauthorized" in str(e)
        cb_tw.record_failure(str(e), non_retryable=non_retryable)
        log_tool_call("social", "social.post_twitter", "failure", "failure",
                      f"Tweet failed: {e}", correlation_id, params=params)
        return make_response("error", "social.post_twitter", correlation_id,
                             detail=f"Tweet failed: {e}")


@server.tool()
def social_weekly_summary(period_days: int = 7,
                          correlation_id: str = "") -> dict:
    """Generate weekly social media activity summary from logs.

    Args:
        period_days: Number of days to summarize (default: 7)
        correlation_id: Correlation ID for audit tracing
    """
    vault = get_vault_path()
    log_file = vault / "Logs" / "mcp_social.jsonl"

    stats = {
        "facebook": {"posts": 0, "last_post": None},
        "instagram": {"posts": 0, "last_post": None},
        "twitter": {"posts": 0, "last_post": None},
    }
    total_posts = 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=period_days)

    if log_file.exists():
        for line in log_file.read_text().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("action") != "success":
                    continue
                ts_str = entry.get("timestamp", "")
                ts = datetime.strptime(ts_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                if ts < cutoff:
                    continue

                tool = entry.get("tool", "")
                platform = None
                if "facebook" in tool:
                    platform = "facebook"
                elif "instagram" in tool:
                    platform = "instagram"
                elif "twitter" in tool:
                    platform = "twitter"

                if platform:
                    stats[platform]["posts"] += 1
                    stats[platform]["last_post"] = ts_str
                    total_posts += 1
            except (json.JSONDecodeError, ValueError):
                continue

    # Generate summary file
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    summary_path = vault / "Plans" / f"Social_Media_Summary_{ts.strftime('%Y%m%d')}.md"
    summary_path.parent.mkdir(parents=True, exist_ok=True)

    content = f"""---
title: "Social Media Summary"
created: "{ts_str}"
type: social-summary
period_days: {period_days}
total_posts: {total_posts}
---

## Social Media Activity Summary

**Period**: Last {period_days} days (as of {ts_str})

### Posts by Platform

| Platform | Posts | Last Post |
|----------|-------|-----------|
| Facebook | {stats['facebook']['posts']} | {stats['facebook']['last_post'] or 'N/A'} |
| Instagram | {stats['instagram']['posts']} | {stats['instagram']['last_post'] or 'N/A'} |
| Twitter/X | {stats['twitter']['posts']} | {stats['twitter']['last_post'] or 'N/A'} |
| **Total** | **{total_posts}** | |
"""

    tmp = summary_path.with_suffix(summary_path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.rename(tmp, summary_path)

    log_tool_call("social", "social.weekly_summary", "success", "success",
                  f"Summary generated: {total_posts} posts in {period_days} days",
                  correlation_id, result={"total_posts": total_posts})

    return make_response("success", "social.weekly_summary", correlation_id,
                         summary_file=str(summary_path),
                         stats=stats, total_posts=total_posts)


if __name__ == "__main__":
    server.run(transport="stdio")
