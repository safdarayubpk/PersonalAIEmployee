# MCP Social Media Server Tools Contract

**Server**: `fte-social`
**Script**: `src/mcp/social_server.py`
**Transport**: stdio

## Tools

### social.post_facebook

**HITL**: Sensitive (approval required)
**Description**: Publish a post to a configured Facebook Page

**Input**:
```json
{
  "content": "string (required) — post text (max 63,206 chars)",
  "link": "string (optional) — URL to attach",
  "correlation_id": "string (optional)"
}
```

**Output (dry-run)**:
```json
{
  "status": "dry_run",
  "tool": "social.post_facebook",
  "platform": "facebook",
  "char_count": 150,
  "detail": "Would post to Facebook Page: '<first 50 chars>...'",
  "correlation_id": "<propagated>"
}
```

**Output (live, approved)**:
```json
{
  "status": "success",
  "tool": "social.post_facebook",
  "platform": "facebook",
  "post_id": "<facebook-post-id>",
  "published_at": "<ISO 8601>",
  "correlation_id": "<propagated>"
}
```

---

### social.post_instagram

**HITL**: Sensitive (approval required)
**Description**: Publish a post to Instagram Business account (requires image URL)

**Input**:
```json
{
  "caption": "string (required) — post caption (max 2,200 chars)",
  "image_url": "string (required) — publicly accessible image URL (JPG/PNG, max 8MB)",
  "correlation_id": "string (optional)"
}
```

**Output (live, approved)**:
```json
{
  "status": "success",
  "tool": "social.post_instagram",
  "platform": "instagram",
  "post_id": "<instagram-post-id>",
  "published_at": "<ISO 8601>",
  "correlation_id": "<propagated>"
}
```

---

### social.post_twitter

**HITL**: Sensitive (approval required)
**Description**: Publish a tweet to Twitter/X

**Input**:
```json
{
  "content": "string (required) — tweet text (max 280 chars)",
  "correlation_id": "string (optional)"
}
```

**Output (live, approved)**:
```json
{
  "status": "success",
  "tool": "social.post_twitter",
  "platform": "twitter",
  "tweet_id": "<twitter-tweet-id>",
  "published_at": "<ISO 8601>",
  "correlation_id": "<propagated>"
}
```

**Output (rate limited)**:
```json
{
  "status": "rate_limited",
  "tool": "social.post_twitter",
  "retry_after_seconds": 900,
  "detail": "Twitter rate limit hit. Retry after 15 minutes.",
  "correlation_id": "<propagated>"
}
```

---

### social.weekly_summary

**HITL**: Routine (no approval needed)
**Description**: Generate weekly social media activity summary from logs

**Input**:
```json
{
  "period_days": "integer (optional, default: 7)",
  "correlation_id": "string (optional)"
}
```

**Output**:
```json
{
  "status": "success",
  "tool": "social.weekly_summary",
  "summary_file": "/path/to/Social_Media_Summary.md",
  "stats": {
    "facebook": {"posts": 2, "last_post": "<ISO 8601>"},
    "instagram": {"posts": 1, "last_post": "<ISO 8601>"},
    "twitter": {"posts": 3, "last_post": "<ISO 8601>"}
  },
  "total_posts": 6,
  "correlation_id": "<propagated>"
}
```
