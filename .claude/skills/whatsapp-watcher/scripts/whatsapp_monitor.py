"""WhatsApp Web monitor for the AI Employee vault.

Uses Playwright (Chromium) to monitor WhatsApp Web for new unread messages,
classifies urgency per Company_Handbook.md, and creates Needs_Action .md files.

Usage:
    python whatsapp_monitor.py                     # Visible browser (first run for QR)
    python whatsapp_monitor.py --headless          # Headless (after QR linked)
    python whatsapp_monitor.py --interval 30       # Poll every 30 seconds
    python whatsapp_monitor.py --vault-path /x     # Custom vault path

Requirements:
    pip install playwright
    playwright install chromium
"""

import argparse
import json
import os
import re
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Error: playwright not installed.")
    print("Run: pip install playwright && playwright install chromium")
    sys.exit(1)

DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"
SESSION_DIR = Path.home() / ".whatsapp-watcher-session"
COMPONENT = "whatsapp-watcher"
MAX_MSG_CHARS = 500
WHATSAPP_URL = "https://web.whatsapp.com"

SKILL_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", SKILL_DIR.parent.parent.parent))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from vault_helpers import redact_sensitive

RISK_KEYWORDS_PATH = PROJECT_ROOT / "config" / "risk-keywords.json"

_FALLBACK_HIGH = ["urgent", "asap", "immediately", "emergency", "deadline", "critical",
                  "help", "payment", "invoice", "transfer", "bank", "legal", "contract"]
_FALLBACK_MEDIUM = ["meeting", "schedule", "review", "approve", "confirm", "update",
                    "project", "client", "document", "shared", "action", "reply",
                    "respond", "call", "tomorrow", "today"]


def _load_risk_keywords() -> tuple[list[str], list[str]]:
    """Load risk keywords from shared config, falling back to defaults."""
    if RISK_KEYWORDS_PATH.exists():
        try:
            data = json.loads(RISK_KEYWORDS_PATH.read_text(encoding="utf-8"))
            return data.get("high", _FALLBACK_HIGH), data.get("medium", _FALLBACK_MEDIUM)
        except (json.JSONDecodeError, OSError):
            pass
    return _FALLBACK_HIGH, _FALLBACK_MEDIUM


HIGH_KEYWORDS, MEDIUM_KEYWORDS = _load_risk_keywords()

# CSS selectors — see references/whatsapp_web_selectors.md for details
SELECTORS = {
    "chat_list": 'div[aria-label="Chat list"]',
    "unread_chat": 'div[aria-label="Chat list"] span[aria-label*="unread message"]',
    "chat_row": 'div[role="listitem"]',
    "chat_title": 'span[title]',
    "message_text": 'span.selectable-text',
    "message_row": 'div[role="row"]',
    "media_image": 'img[src*="blob:"]',
    "media_document": 'a[href*="blob:"]',
    "media_voice": 'button[aria-label="Play"]',
}


def slugify(text: str, max_len: int = 30) -> str:
    """Convert text to a URL-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len]


def classify_urgency(text: str) -> str:
    """Classify message urgency based on keywords.

    Returns constitution-canonical priority values:
    critical (high-risk keywords), sensitive (medium-risk), routine (default).
    """
    lower = text.lower()
    if any(kw in lower for kw in HIGH_KEYWORDS):
        return "critical"
    if any(kw in lower for kw in MEDIUM_KEYWORDS):
        return "sensitive"
    return "routine"


def log_entry(log_file: Path, **fields) -> None:
    """Append a JSON line to the log file (sensitive fields redacted)."""
    entry = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), **fields}
    entry = redact_sensitive(entry)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def create_needs_action(sender: str, chat_name: str, chat_type: str,
                        message_text: str, urgency: str, media_types: list[str],
                        unread_count: int, vault_root: Path) -> str:
    """Create a Needs_Action .md file for an important message."""
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_filename = ts.strftime("%Y%m%d-%H%M%S")

    sender_slug = slugify(sender)
    filename = f"whatsapp-{sender_slug}-{ts_filename}.md"
    filepath = vault_root / "Needs_Action" / filename

    subject_slug = slugify(chat_name)
    media_str = ", ".join(media_types) if media_types else "none"
    truncated = message_text[:MAX_MSG_CHARS]

    content = f"""---
title: "whatsapp-{sender_slug}-{subject_slug}"
created: "{ts_str}"
tier: silver
source: whatsapp-watcher
priority: "{urgency}"
status: needs_action
chat_type: "{chat_type}"
---

## What happened

New WhatsApp message from `{sender}` in {chat_name}.

## Message Content

{truncated}

## Suggested action

Review and respond to this message.

## Context

- From: {sender}
- Chat: {chat_name}
- Time: {ts_str}
- Media: {media_str}
- Unread count: {unread_count}
"""

    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(content, encoding="utf-8")
    os.rename(tmp_path, filepath)

    return filename


def detect_media(message_el) -> list[str]:
    """Detect media types in a message element."""
    media = []
    try:
        if message_el.query_selector(SELECTORS["media_image"]):
            media.append("image")
        if message_el.query_selector(SELECTORS["media_document"]):
            media.append("document")
        if message_el.query_selector(SELECTORS["media_voice"]):
            media.append("voice_note")
    except Exception:
        pass
    return media


def extract_messages(page, max_messages: int = 10) -> list[dict]:
    """Extract recent messages from the currently open chat."""
    messages = []
    try:
        rows = page.query_selector_all(SELECTORS["message_row"])
        for row in rows[-max_messages:]:
            text_el = row.query_selector(SELECTORS["message_text"])
            text = text_el.inner_text() if text_el else ""
            media = detect_media(row)
            if text or media:
                messages.append({"text": text, "media": media})
    except Exception as e:
        print(f"Warning: Failed to extract messages: {e}")
    return messages


def get_unread_chats(page) -> list[dict]:
    """Find chats with unread message badges."""
    chats = []
    try:
        badge_els = page.query_selector_all(SELECTORS["unread_chat"])
        for badge in badge_els:
            chat_row = badge.evaluate_handle(
                "el => el.closest('[role=\"listitem\"]') || el.closest('[data-id]')"
            )
            if not chat_row:
                continue

            title_el = chat_row.as_element().query_selector(SELECTORS["chat_title"])
            title = title_el.get_attribute("title") if title_el else "Unknown"

            badge_text = badge.inner_text().strip()
            try:
                count = int(badge_text)
            except ValueError:
                count = 1

            chats.append({
                "element": chat_row.as_element(),
                "title": title,
                "unread_count": count,
            })
    except Exception:
        pass
    return chats


def monitor_loop(page, vault_root: Path, interval: int) -> None:
    """Main monitoring loop."""
    log_file = vault_root / "Logs" / "whatsapp.jsonl"
    processed_ids: set[str] = set()

    log_entry(log_file, component=COMPONENT, action="startup", status="success",
              detail=f"Monitoring WhatsApp Web, poll interval {interval}s")
    print(f"Monitoring WhatsApp Web (poll every {interval}s)...")

    while True:
        try:
            unread = get_unread_chats(page)

            if not unread:
                time.sleep(interval)
                continue

            for chat in unread:
                chat_id = f"{chat['title']}:{chat['unread_count']}"
                if chat_id in processed_ids:
                    continue

                try:
                    chat["element"].click()
                    page.wait_for_timeout(1500)
                except Exception:
                    continue

                messages = extract_messages(page)
                if not messages:
                    continue

                combined_text = " ".join(m["text"] for m in messages if m["text"])
                all_media = []
                for m in messages:
                    all_media.extend(m["media"])
                media_types = list(set(all_media))

                is_group = chat["unread_count"] > 0
                chat_type = "group" if "@" in chat["title"] or " " in chat["title"] else "direct"
                sender = chat["title"]

                urgency = classify_urgency(combined_text)

                if urgency == "routine":
                    log_entry(log_file, component=COMPONENT, action="classify_message",
                              status="skipped", detail="Routine priority, skipped",
                              sender=sender, chat=chat["title"], urgency=urgency)
                    processed_ids.add(chat_id)
                    continue

                filename = create_needs_action(
                    sender=sender, chat_name=chat["title"], chat_type=chat_type,
                    message_text=combined_text, urgency=urgency,
                    media_types=media_types, unread_count=chat["unread_count"],
                    vault_root=vault_root,
                )

                log_entry(log_file, component=COMPONENT, action="process_message",
                          status="success",
                          detail=f"Classified as {urgency}, created Needs_Action file",
                          sender=sender, chat=chat["title"], chat_type=chat_type,
                          urgency=urgency, has_media=bool(media_types),
                          needs_action_file=filename)

                print(f"  [{urgency.upper()}] {sender}: {combined_text[:80]}... → {filename}")
                processed_ids.add(chat_id)

        except Exception as e:
            error_str = str(e)
            log_entry(log_file, component=COMPONENT, action="poll_error",
                      status="failure", detail=error_str)
            print(f"Poll error: {e}")

            # Detect session loss — if chat list is gone, session is disconnected
            try:
                if not page.query_selector(SELECTORS["chat_list"]):
                    log_entry(log_file, component=COMPONENT, action="session_loss",
                              status="failure",
                              detail="WhatsApp session lost — chat list not found")
                    print("Session lost: WhatsApp Web disconnected.")
                    break
            except Exception:
                log_entry(log_file, component=COMPONENT, action="session_loss",
                          status="failure",
                          detail="WhatsApp session lost — page unresponsive")
                print("Session lost: page unresponsive.")
                break

        time.sleep(interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Monitor WhatsApp Web for new messages")
    parser.add_argument("--headless", action="store_true",
                        help="Run browser in headless mode (use after QR is linked)")
    parser.add_argument("--interval", type=int, default=15,
                        help="Poll interval in seconds (default: 15)")
    parser.add_argument("--vault-path", default=None,
                        help="Vault root path (default: VAULT_PATH env or standard path)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    vault_path = args.vault_path or os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH)
    vault_root = Path(vault_path)
    log_file = vault_root / "Logs" / "whatsapp.jsonl"
    pid_file = vault_root / "Logs" / "whatsapp-watcher.pid"

    if not vault_root.exists():
        print(f"Error: Vault not found at {vault_root}")
        sys.exit(1)

    # PID lock
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    if pid_file.exists():
        try:
            existing_pid = int(pid_file.read_text().strip())
            os.kill(existing_pid, 0)
            print(f"Error: WhatsApp watcher already running (PID: {existing_pid})")
            sys.exit(1)
        except ProcessLookupError:
            pid_file.unlink()
        except ValueError:
            pid_file.unlink()
    pid_file.write_text(str(os.getpid()))

    def cleanup(signum=None, frame=None):
        print("\nShutting down WhatsApp watcher...")
        if pid_file.exists():
            pid_file.unlink()
        log_entry(log_file, component=COMPONENT, action="shutdown", status="success",
                  detail="Clean shutdown via signal")
        sys.exit(0)

    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)

    SESSION_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch_persistent_context(
            user_data_dir=str(SESSION_DIR),
            headless=args.headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = browser.new_page()
        page.goto(WHATSAPP_URL)

        print("Waiting for WhatsApp Web to load...")
        if not args.headless:
            print("If QR code appears, scan it with your phone.")

        try:
            page.wait_for_selector(SELECTORS["chat_list"], timeout=60000)
            print("WhatsApp Web loaded successfully.")
            log_entry(log_file, component=COMPONENT, action="login", status="success",
                      detail="WhatsApp Web loaded")
        except Exception:
            print("Error: WhatsApp Web did not load within 60 seconds.")
            print("Try running without --headless to scan QR code.")
            cleanup()

        try:
            monitor_loop(page, vault_root, args.interval)
        except KeyboardInterrupt:
            pass
        finally:
            browser.close()
            cleanup()


if __name__ == "__main__":
    main()
