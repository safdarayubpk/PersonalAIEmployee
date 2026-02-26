# Gmail API Setup Guide

## 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Note the project ID

## 2. Enable Gmail API

1. Navigate to **APIs & Services > Library**
2. Search for "Gmail API"
3. Click **Enable**

## 3. Create OAuth2 Credentials

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Name: `AI Employee Gmail Watcher`
5. Click **Create**
6. Download the JSON file

## 4. Save Credentials

Save the downloaded file as `credentials.json` in the project root:

```
/home/safdarayub/Desktop/claude/fte/credentials.json
```

Ensure `credentials.json` is in `.gitignore` (already configured).

## 5. First Run

```bash
python .claude/skills/gmail-watcher/scripts/gmail_poll.py
```

A browser window opens for Google OAuth consent. After authorizing:
- `token.json` is created automatically in the project root
- Subsequent runs use the cached token (no browser needed)

## 6. Scopes

| Mode | Scopes | Purpose |
|------|--------|---------|
| Dry-run (default) | `gmail.readonly` | Read-only access to poll emails |
| Live (`--live`) | `gmail.readonly`, `gmail.modify` | Read + mark emails as read |

## 7. Token Refresh

Tokens expire after ~1 hour but auto-refresh using the refresh token. If the refresh token is revoked:

1. Delete `token.json`
2. Run the script again to re-authorize

## Security Notes

- `credentials.json` and `token.json` must never be committed to git
- Both files are listed in `.gitignore`
- Tokens are stored locally only — no cloud transmission
- Revoke access anytime at [Google Account Permissions](https://myaccount.google.com/permissions)
