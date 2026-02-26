---
name: gmail-watcher
description: Polls Gmail for unread emails using the Gmail API, filters important ones per Company_Handbook.md risk rules, and creates Needs_Action .md files with YAML frontmatter. Use when the user asks to "check gmail", "poll emails", "watch for new emails", "process inbox", "check for important emails", or when a scheduler triggers a Gmail polling cycle. Also triggers on phrases like "any new emails", "gmail inbox", or "unread messages". Requires google-api-python-client credentials to be configured.
---

# Gmail Watcher

Poll Gmail for unread emails, classify importance per Company_Handbook.md, and create Needs_Action markdown files for emails that need attention.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Dependencies

- `google-api-python-client`
- `google-auth-oauthlib`
- `google-auth-httplib2`
- `credentials.json` in project root (OAuth2 client credentials from Google Cloud Console)
- `token.json` auto-generated after first OAuth flow

Install:

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

## Workflow

```
Poll Gmail (unread, last N minutes)
       │
       ├── No unread → Log "no new emails" → Done
       │
       └── Unread found
              │
              ├── For each email:
              │     ├── Extract sender, subject, body snippet, attachments list
              │     ├── Load Company_Handbook.md risk rules
              │     ├── Classify urgency (low/medium/high)
              │     ├── If important → Create Needs_Action .md
              │     ├── If dry-run=false → Mark email as read in Gmail
              │     └── Log result to Logs/gmail.jsonl
              │
              └── Log summary to Logs/gmail.jsonl
```

## Step 1: Authenticate

Run `scripts/gmail_poll.py` which handles OAuth2:

1. Check for `token.json` in project root
2. If missing or expired, open browser for OAuth consent (first run only)
3. Cache token for subsequent runs

**Scopes required**: `gmail.readonly`, `gmail.modify` (for marking as read)

## Step 2: Poll for Unread Emails

```bash
# Dry-run mode (default) — polls and classifies but does NOT mark as read
python .claude/skills/gmail-watcher/scripts/gmail_poll.py

# Live mode — also marks processed emails as read
python .claude/skills/gmail-watcher/scripts/gmail_poll.py --live

# Custom polling window (default: 30 minutes)
python .claude/skills/gmail-watcher/scripts/gmail_poll.py --minutes 60

# Custom vault path
python .claude/skills/gmail-watcher/scripts/gmail_poll.py --vault-path /custom/vault
```

## Step 3: Classify Urgency

Load `Company_Handbook.md` from vault root and classify each email:

- **High**: Financial (invoice, payment, billing), legal (contract, NDA, compliance), security alerts, known VIP senders, deadlines within 24h
- **Medium**: Meeting requests, project updates requiring response, client emails, shared documents
- **Low**: Newsletters, automated notifications, marketing, FYI-only, no-reply senders

Only emails classified as **medium** or **high** generate Needs_Action files. Low-urgency emails are logged but skipped.

## Step 4: Create Needs_Action File

For each important email, write to `Needs_Action/` using atomic writes:

**Filename**: `email-<sender-slug>-<YYYYMMDD-HHMMSS>.md`

**Content format**:

```markdown
---
title: "email-<sender-slug>-<subject-slug>"
created: "<ISO timestamp>"
tier: silver
source: gmail-watcher
priority: "<low|medium|high>"
status: needs_action
gmail_id: "<message ID>"
---

## What happened

New email from `<sender>`: <subject>

## Body Summary

<first 500 chars of plain text body>

## Suggested action

<Review and respond / Review attachment / Forward to team / Archive>

## Context

- From: <sender name> <<sender email>>
- Subject: <subject line>
- Date: <email date>
- Attachments: <list or "none">
- Labels: <Gmail labels>
```

## Step 5: Mark as Read (Live Mode Only)

In live mode (`--live` flag), after creating the Needs_Action file:

1. Call Gmail API to remove `UNREAD` label from the message
2. Log the action to `Logs/gmail.jsonl`

In dry-run mode (default), skip this step and log `"dry_run": true`.

## Step 6: Log Results

Append one JSON line per email to `Logs/gmail.jsonl`:

```json
{
  "timestamp": "2026-02-25T12:00:00",
  "component": "gmail-watcher",
  "action": "poll_email",
  "status": "success",
  "detail": "Classified as high urgency, created Needs_Action file",
  "gmail_id": "msg_abc123",
  "sender": "boss@company.com",
  "subject": "Q1 Budget Review",
  "urgency": "high",
  "needs_action_file": "email-boss-20260225-120000.md",
  "dry_run": true
}
```

## Safety Rules

1. **Dry-run by default** — never mark emails as read unless `--live` flag is explicitly passed
2. **Read-only Gmail access in dry-run** — only `gmail.readonly` scope used when polling
3. **Never store email credentials in vault** — `credentials.json` and `token.json` stay in project root, listed in `.gitignore`
4. **Never store full email bodies in vault** — only first 500 chars of plain text summary
5. **All vault writes scoped to vault root** — path validation via `vault_helpers.validate_path()`
6. **No-deletion policy** — never delete emails from Gmail or files from vault
7. **Log everything** — every poll, classification, and file creation logged to `Logs/gmail.jsonl`

## Resources

### scripts/

- `gmail_poll.py` — Main polling script with OAuth2, Gmail API calls, classification, and Needs_Action file creation

### references/

- `gmail_api_setup.md` — Step-by-step guide for creating Google Cloud project, enabling Gmail API, and downloading `credentials.json`
