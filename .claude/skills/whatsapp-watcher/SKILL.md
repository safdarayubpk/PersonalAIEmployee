---
name: whatsapp-watcher
description: Monitors WhatsApp Web via Playwright (Chromium) for new messages, parses text and media, classifies urgency per Company_Handbook.md, and creates Needs_Action .md files with YAML frontmatter. Use when the user asks to "watch whatsapp", "monitor whatsapp", "check whatsapp messages", "start whatsapp watcher", or when a scheduler triggers a WhatsApp monitoring cycle. Also triggers on phrases like "any new whatsapp messages", "whatsapp inbox", or "unread chats". Requires Playwright with Chromium installed.
---

# WhatsApp Watcher

Monitor WhatsApp Web via Playwright for new unread messages, classify urgency per Company_Handbook.md, and create Needs_Action markdown files for messages that need attention.

**Vault root**: `/home/safdarayub/Documents/AI_Employee_Vault`
(override via `VAULT_PATH` env var)

## Dependencies

- `playwright` (with Chromium browser)

Install:

```bash
pip install playwright
playwright install chromium
```

## Workflow

```
Launch Chromium → Open WhatsApp Web
       │
       ├── First run? → Display QR code → Wait for scan → Save session
       │
       └── Session exists? → Auto-login
              │
              └── Poll loop (every 15 seconds)
                     │
                     ├── Scan for unread chat badges
                     │     │
                     │     ├── No unread → Continue polling
                     │     │
                     │     └── Unread found
                     │           │
                     │           ├── Click chat → Extract messages
                     │           ├── Parse sender, text, media, timestamps
                     │           ├── Classify urgency (low/medium/high)
                     │           ├── If important → Create Needs_Action .md
                     │           └── Log to Logs/whatsapp.jsonl
                     │
                     └── Loop until SIGTERM/SIGINT
```

## Step 1: Launch and Authenticate

Run `scripts/whatsapp_monitor.py` which manages the browser session:

1. Launch Chromium with persistent context at `~/.whatsapp-watcher-session/`
2. Navigate to `https://web.whatsapp.com`
3. **First run**: QR code appears in the browser — scan with phone to link
4. **Subsequent runs**: Session restores automatically (no QR needed)
5. Wait for the chat list to load (timeout 60s). See `references/whatsapp_web_selectors.md` for selector details.

```bash
# Start monitoring (runs until stopped)
python .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py

# Custom vault path
python .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py --vault-path /custom/vault

# Custom poll interval (default: 15 seconds)
python .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py --interval 30

# Headless mode (no visible browser, use after QR is linked)
python .claude/skills/whatsapp-watcher/scripts/whatsapp_monitor.py --headless
```

## Step 2: Detect Unread Messages

Poll the chat list for unread badges:

1. Query all chat elements with unread count badges
2. For each unread chat:
   - Click the chat to open it
   - Extract the last N unread messages
   - Record sender name, group name (if group), message text, timestamps
   - Detect media: images, documents, voice notes, videos (by message type indicators)
3. Track processed message IDs to avoid duplicates across poll cycles

## Step 3: Classify Urgency

Load `Company_Handbook.md` from vault root and classify each message:

- **High**: Contains urgency keywords (`urgent`, `ASAP`, `immediately`, `emergency`, `deadline`, `critical`, `help`), financial requests, messages from VIP contacts
- **Medium**: Direct messages requesting a response, shared documents or media needing review, group mentions, meeting coordination, action items
- **Low**: Group chat general discussion, memes/stickers, forwarded chain messages, status reactions, single-emoji replies

Only messages classified as **medium** or **high** generate Needs_Action files.

## Step 4: Create Needs_Action File

For each important message, write to `Needs_Action/` using atomic writes:

**Filename**: `whatsapp-<sender-slug>-<YYYYMMDD-HHMMSS>.md`

**Content format**:

```markdown
---
title: "whatsapp-<sender-slug>-<subject-slug>"
created: "<ISO timestamp>"
tier: silver
source: whatsapp-watcher
priority: "<low|medium|high>"
status: needs_action
chat_type: "<direct|group>"
---

## What happened

New WhatsApp message from `<sender>` in <direct chat / group name>.

## Message Content

<message text, max 500 chars>

## Suggested action

<Reply / Review media / Forward to team / Acknowledge>

## Context

- From: <sender name>
- Chat: <direct or group name>
- Time: <message timestamp>
- Media: <list of media types or "none">
- Unread count: <number of unread in this chat>
```

## Step 5: Log Results

Append one JSON line per processed message to `Logs/whatsapp.jsonl`:

```json
{
  "timestamp": "2026-02-25T12:00:00",
  "component": "whatsapp-watcher",
  "action": "process_message",
  "status": "success",
  "detail": "Classified as high urgency, created Needs_Action file",
  "sender": "Ali Khan",
  "chat": "Project Team",
  "chat_type": "group",
  "urgency": "high",
  "has_media": false,
  "needs_action_file": "whatsapp-ali-khan-20260225-120000.md"
}
```

## Safety Rules

1. **Read-only** — never send messages, react, or modify WhatsApp state
2. **Session persistence** — browser profile at `~/.whatsapp-watcher-session/`, never in vault or git
3. **No phone numbers in logs** — log sender display names only
4. **No full message logging** — max 500 chars of message text in Needs_Action files
5. **All vault writes scoped to vault root** — path validation via `vault_helpers.validate_path()`
6. **No-deletion policy** — never delete messages or vault files
7. **Clean shutdown** — SIGTERM/SIGINT closes browser gracefully and removes PID lock
8. **Duplicate prevention** — track processed message IDs per session
9. **Log everything** — every poll cycle and classification logged to `Logs/whatsapp.jsonl`

## Resources

### scripts/

- `whatsapp_monitor.py` — Main monitoring script with Playwright browser automation, message extraction, classification, and Needs_Action file creation

### references/

- `whatsapp_web_selectors.md` — CSS selectors and DOM patterns for WhatsApp Web elements used by the monitor script
