# Social Media API Setup Guide

## Facebook Page Access Token

### 1. Create Meta Developer Account

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Log in with the Facebook account that manages the target Page
3. Click **My Apps** → **Create App**
4. Choose **Business** type → enter app name

### 2. Add Facebook Login Product

1. In your app dashboard, click **Add Product**
2. Select **Facebook Login** → **Set Up**
3. Choose **Web** platform

### 3. Generate Page Access Token

1. Go to **Tools** → [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from the dropdown
3. Click **Generate Access Token**
4. Grant permissions: `pages_manage_posts`, `pages_read_engagement`
5. Select your Page from the dropdown
6. Copy the **Page Access Token**

### 4. Get Long-Lived Token

Short-lived tokens expire in ~1 hour. Exchange for a long-lived token:

```bash
curl -X GET "https://graph.facebook.com/v19.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id=YOUR_APP_ID&\
client_secret=YOUR_APP_SECRET&\
fb_exchange_token=SHORT_LIVED_TOKEN"
```

Long-lived tokens last ~60 days. For permanent tokens, use a System User.

### 5. Find Page ID

```bash
curl "https://graph.facebook.com/v19.0/me/accounts?access_token=YOUR_TOKEN"
```

The response includes `"id"` for each Page.

### 6. Set Environment Variables

```bash
export FACEBOOK_PAGE_ID="your-page-id"
export FACEBOOK_ACCESS_TOKEN="your-long-lived-page-token"
```

---

## Instagram Business Account

Instagram posting uses the **Facebook Graph API** (not a separate Instagram API).

### Prerequisites

- Facebook Page linked to an Instagram Business or Creator Account
- Same `FACEBOOK_ACCESS_TOKEN` from above (with `instagram_basic`, `instagram_content_publish` permissions)

### 1. Find Instagram Business ID

```bash
curl "https://graph.facebook.com/v19.0/YOUR_PAGE_ID?fields=instagram_business_account&access_token=YOUR_TOKEN"
```

### 2. Set Environment Variable

```bash
export INSTAGRAM_BUSINESS_ID="your-instagram-business-id"
# Uses FACEBOOK_ACCESS_TOKEN (already set above)
```

### 3. Image Requirements

Instagram posts require a **publicly accessible image URL**:
- Format: JPG or PNG
- Max size: 8MB
- Must be accessible via HTTPS (no localhost)
- The URL must be reachable by Facebook servers

---

## Twitter/X API (v2)

### 1. Create Developer Account

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Apply for **Free** or **Basic** access tier
3. Create a new Project and App

### 2. Generate API Keys

In your app settings under **Keys and Tokens**:

1. **Consumer Keys** (API Key and Secret) — identifies your app
2. **Authentication Tokens** — click **Generate** for:
   - Access Token
   - Access Token Secret

### 3. Set Permissions

Under **User authentication settings**:
- App permissions: **Read and Write**
- Type of App: **Web App, Automated App, or Bot**

### 4. Set Environment Variables

```bash
export TWITTER_API_KEY="your-api-key"
export TWITTER_API_SECRET="your-api-secret"
export TWITTER_ACCESS_TOKEN="your-access-token"
export TWITTER_ACCESS_TOKEN_SECRET="your-access-token-secret"
```

### 5. Python Dependencies

```bash
pip install tweepy
```

---

## Rate Limits

| Platform | Limit | Window | Handling |
|----------|-------|--------|----------|
| Facebook | 200 calls | per hour | 429 → retry after 900s |
| Instagram | 25 posts | per day | 429 → retry after 900s |
| Twitter | 450 requests | per 15 min | tweepy auto-waits |

## Character Limits

| Platform | Max Characters |
|----------|---------------|
| Twitter/X | 280 |
| Instagram | 2,200 (caption) |
| Facebook | 63,206 |

## Security Notes

- Store all tokens in `.env` file or environment variables — never commit to git
- `.env` is listed in `.gitignore`
- Rotate tokens periodically (Facebook every 60 days unless using System User)
- Use the minimum required permissions for each platform
