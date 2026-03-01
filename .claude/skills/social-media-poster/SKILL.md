---
name: social-media-poster
description: Draft and publish posts to Facebook, Instagram, and Twitter/X via MCP social server. Generates weekly social media summaries. Use when the user asks to "post to social media", "draft social post", "tweet", "post to facebook", "post to instagram", "social media summary", "publish social update", or when the orchestrator routes a social media task. Also triggers on phrases like "share on social", "social post", "create tweet", or "weekly social report". All publish actions require HITL approval (sensitive).
---

# Social Media Poster

Draft and publish posts to Facebook, Instagram, and Twitter/X through the MCP social media server (`fte-social`). All publish actions are HITL-gated (sensitive classification).

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Dependencies

- MCP social server registered: `fte-social` in `.claude/settings.json`
- API credentials in `.env`:
  - Facebook: `FACEBOOK_PAGE_ID`, `FACEBOOK_ACCESS_TOKEN`
  - Instagram: `INSTAGRAM_BUSINESS_ID` (uses Facebook token)
  - Twitter: `TWITTER_API_KEY`, `TWITTER_API_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_TOKEN_SECRET`

## Available MCP Tools

| Tool | HITL | Description |
|------|------|-------------|
| `social.post_facebook` | Sensitive | Post to Facebook Page |
| `social.post_instagram` | Sensitive | Post to Instagram (requires image_url) |
| `social.post_twitter` | Sensitive | Tweet to Twitter/X (max 280 chars) |
| `social.weekly_summary` | Routine | Generate posting activity summary |

## Workflow

```
1. DRAFT   → Compose content based on Business_Goals.md or user request
2. VALIDATE → Check character limits (Twitter: 280, Instagram: 2200, Facebook: 63206)
3. APPROVE → Create Pending_Approval file (HITL gate for sensitive actions)
4. PUBLISH → After approval, execute live post via MCP tool
5. LOG     → All actions logged to Logs/mcp_social.jsonl with correlation_id
```

## Usage

### Via Claude Code

```
claude "draft a business update tweet based on Business_Goals.md"
claude "post to all social platforms about our new product launch"
claude "generate weekly social media summary"
```

### Content Guidelines

- **Twitter**: Max 280 characters. Concise, engaging, with hashtags.
- **Instagram**: Max 2,200 character caption. Requires public image URL.
- **Facebook**: Max 63,206 characters. Can include link attachments.

## Safety Rules

1. **All posts require HITL approval** — sensitive classification
2. **Content validated before posting** — character limits enforced
3. **Dry-run by default** — no posts without explicit live mode + approval
4. **All activity logged** — `Logs/mcp_social.jsonl` with correlation IDs
5. **Rate limits handled** — Twitter 429 returns retry_after, not failure

## Resources

### references/

- `social_api_setup.md` — Step-by-step setup for Facebook Page Access Token, Instagram Business Account, and Twitter/X API keys. Includes rate limits and character limits per platform.
