"""Gmail polling script for the AI Employee vault.

Polls Gmail for unread emails, classifies urgency per Company_Handbook.md,
creates Needs_Action .md files for important emails, and optionally marks
them as read.

Usage:
    python gmail_poll.py                    # Dry-run (default)
    python gmail_poll.py --live             # Mark processed emails as read
    python gmail_poll.py --minutes 60       # Poll last 60 minutes
    python gmail_poll.py --vault-path /x    # Custom vault path

Requirements:
    pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
    credentials.json in project root (from Google Cloud Console)
"""

import argparse
import json
import os
import re
import sys
import base64
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("Error: Required packages not installed.")
    print("Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
    sys.exit(1)

SKILL_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", SKILL_DIR.parent.parent.parent))
sys.path.insert(0, str(PROJECT_ROOT / "src"))
from vault_helpers import redact_sensitive, generate_correlation_id
from role_gate import get_fte_role, is_cloud, validate_startup

CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"

SCOPES_READONLY = ["https://www.googleapis.com/auth/gmail.readonly"]
SCOPES_MODIFY = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"
COMPONENT = "gmail-watcher"
MAX_BODY_CHARS = 500

RISK_KEYWORDS_PATH = PROJECT_ROOT / "config" / "risk-keywords.json"

_FALLBACK_HIGH = ["payment", "invoice", "transfer", "bank", "transaction", "refund",
                  "billing", "budget", "salary", "legal", "contract", "agreement",
                  "lawsuit", "compliance", "NDA", "security", "breach", "urgent",
                  "emergency", "deadline", "ASAP", "immediately"]
_FALLBACK_MEDIUM = ["meeting", "schedule", "review", "approve", "confirm", "update",
                    "project", "client", "proposal", "document", "shared", "action"]


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
SKIP_SENDERS = ["noreply@", "no-reply@", "notifications@", "mailer-daemon@"]


def authenticate(live: bool) -> object:
    """Authenticate with Gmail API via OAuth2."""
    # Cloud agents always use readonly scopes (FR-008)
    if is_cloud():
        scopes = SCOPES_READONLY
    else:
        scopes = SCOPES_MODIFY if live else SCOPES_READONLY
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Token refresh failed: {e}")
                # Cloud agent: create manual alert for token refresh failure (FR-017)
                if is_cloud():
                    _create_token_refresh_alert(str(e))
                    sys.exit(1)
                print("Attempting re-authentication...")
                creds = None
        if creds is None:
            if not CREDENTIALS_FILE.exists():
                print(f"Error: {CREDENTIALS_FILE} not found.")
                print("See references/gmail_api_setup.md for setup instructions.")
                sys.exit(1)
            if is_cloud():
                # Cloud cannot do interactive auth
                _create_token_refresh_alert("credentials.json present but token.json missing/expired")
                sys.exit(1)
            try:
                flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), scopes)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"Authentication failed: {e}")
                sys.exit(1)

        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def poll_unread(service, minutes: int) -> list[dict]:
    """Fetch unread emails from the last N minutes."""
    after_epoch = int((datetime.now(timezone.utc) - timedelta(minutes=minutes)).timestamp())
    query = f"is:unread after:{after_epoch}"

    results = service.users().messages().list(userId="me", q=query, maxResults=20).execute()
    messages = results.get("messages", [])

    emails = []
    for msg_meta in messages:
        msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
        headers = {h["name"].lower(): h["value"] for h in msg["payload"].get("headers", [])}

        body_text = ""
        payload = msg["payload"]
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part.get("body", {}):
                    body_text = base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", errors="replace")
                    break
        elif "data" in payload.get("body", {}):
            body_text = base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", errors="replace")

        attachments = []
        if "parts" in payload:
            for part in payload["parts"]:
                if part.get("filename"):
                    attachments.append(part["filename"])

        emails.append({
            "id": msg_meta["id"],
            "sender": headers.get("from", "unknown"),
            "subject": headers.get("subject", "(no subject)"),
            "date": headers.get("date", ""),
            "body": body_text[:MAX_BODY_CHARS],
            "attachments": attachments,
            "labels": msg.get("labelIds", []),
        })

    return emails


def classify_urgency(email: dict) -> str:
    """Classify email urgency based on keywords.

    Returns constitution-canonical priority values:
    critical (high-risk keywords), sensitive (medium-risk), routine (default).
    """
    text = f"{email['sender']} {email['subject']} {email['body']}".lower()

    if any(kw.lower() in text for kw in HIGH_KEYWORDS):
        return "critical"
    if any(kw.lower() in text for kw in MEDIUM_KEYWORDS):
        return "sensitive"
    return "routine"


def is_skip_sender(sender: str) -> bool:
    """Check if sender is a no-reply or notification address."""
    sender_lower = sender.lower()
    return any(skip in sender_lower for skip in SKIP_SENDERS)


def slugify(text: str, max_len: int = 30) -> str:
    """Convert text to a URL-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len]


def create_needs_action(email: dict, urgency: str, vault_root: Path) -> str:
    """Create a Needs_Action/gmail/ .md file for an important email."""
    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_filename = ts.strftime("%Y%m%d-%H%M%S")

    sender_slug = slugify(email["sender"].split("@")[0].split("<")[-1])
    filename = f"email-{sender_slug}-{ts_filename}.md"
    # Write to domain subfolder Needs_Action/gmail/ (Platinum tier)
    filepath = vault_root / "Needs_Action" / "gmail" / filename

    subject_slug = slugify(email["subject"])
    attachments_str = ", ".join(email["attachments"]) if email["attachments"] else "none"

    corr_id = generate_correlation_id()

    # Detect agent role for frontmatter
    try:
        agent = get_fte_role()
    except SystemExit:
        agent = ""

    tier = "platinum" if agent else "silver"

    content = f"""---
title: "email-{sender_slug}-{subject_slug}"
created: "{ts_str}"
tier: {tier}
source: gmail-watcher
agent: {agent}
priority: "{urgency}"
status: needs_action
gmail_id: "{email['id']}"
correlation_id: "{corr_id}"
---

## What happened

New email from `{email['sender']}`: {email['subject']}

## Body Summary

{email['body']}

## Suggested action

Review and respond to this email.

## Context

- From: {email['sender']}
- Subject: {email['subject']}
- Date: {email['date']}
- Attachments: {attachments_str}
- Labels: {', '.join(email['labels'])}
"""

    tmp_path = filepath.with_suffix(filepath.suffix + ".tmp")
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(content, encoding="utf-8")
    os.rename(tmp_path, filepath)

    return filename


def _create_token_refresh_alert(error_detail: str) -> None:
    """Create a Needs_Action/manual/ alert for token refresh failure (FR-017)."""
    vault_path = os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH)
    vault_root = Path(vault_path)
    alert_dir = vault_root / "Needs_Action" / "manual"
    alert_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_file = ts.strftime("%Y%m%d-%H%M%S")
    corr_id = generate_correlation_id()

    content = f"""---
title: "gmail-token-refresh-failure"
created: "{ts_str}"
tier: platinum
source: gmail-watcher
agent: cloud
priority: "critical"
status: needs_action
correlation_id: "{corr_id}"
---

## What happened

Gmail OAuth2 token refresh failed on cloud agent. Manual intervention required.

## Error

{error_detail}

## Suggested action

1. On local machine, re-authenticate Gmail: `python3 src/actions/email.py`
2. Copy refreshed token.json to cloud VM
3. Restart cloud-gmail-watcher: `pm2 restart cloud-gmail-watcher`
"""

    filepath = alert_dir / f"gmail-token-failure-{ts_file}.md"
    tmp = filepath.with_suffix(filepath.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.rename(tmp, filepath)
    print(f"Created manual alert: {filepath}")


def log_entry(log_file: Path, **fields) -> None:
    """Append a JSON line to the log file (sensitive fields redacted)."""
    entry = {"timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"), **fields}
    entry = redact_sensitive(entry)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(entry) + "\n")


def mark_as_read(service, message_id: str) -> None:
    """Remove UNREAD label from a Gmail message."""
    service.users().messages().modify(
        userId="me", id=message_id,
        body={"removeLabelIds": ["UNREAD"]},
    ).execute()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Poll Gmail for unread emails")
    parser.add_argument("--live", action="store_true",
                        help="Mark processed emails as read (default: dry-run)")
    parser.add_argument("--minutes", type=int, default=30,
                        help="Poll window in minutes (default: 30)")
    parser.add_argument("--interval", type=int, default=0,
                        help="Daemon mode: poll every N seconds (0 = run once, default: 0)")
    parser.add_argument("--vault-path", default=None,
                        help="Vault root path (default: VAULT_PATH env or standard path)")
    return parser.parse_args()


def poll_once(service, args, vault_root: Path, log_file: Path,
              processed_ids: set[str]) -> tuple[int, int]:
    """Run one poll cycle. Returns (created, skipped) counts."""
    try:
        emails = poll_unread(service, args.minutes)
    except Exception as e:
        print(f"Poll error: {e}")
        log_entry(log_file, component=COMPONENT, action="poll", status="failure",
                  detail=str(e), dry_run=not args.live)
        return 0, 0

    if not emails:
        return 0, 0

    new_emails = [e for e in emails if e["id"] not in processed_ids]
    if not new_emails:
        return 0, 0

    print(f"Found {len(new_emails)} new email(s)")

    created = 0
    skipped = 0

    for email in new_emails:
        processed_ids.add(email["id"])

        if is_skip_sender(email["sender"]):
            log_entry(log_file, component=COMPONENT, action="skip_email", status="skipped",
                      detail=f"No-reply sender: {email['sender']}", gmail_id=email["id"],
                      dry_run=not args.live)
            skipped += 1
            continue

        urgency = classify_urgency(email)

        # Edge case: email with no subject and no body — always create Needs_Action
        no_content = (not email["subject"] or email["subject"] == "(no subject)") and not email["body"].strip()

        if urgency == "routine" and not no_content:
            log_entry(log_file, component=COMPONENT, action="classify_email", status="skipped",
                      detail=f"Routine priority, skipped", gmail_id=email["id"],
                      sender=email["sender"], subject=email["subject"],
                      urgency=urgency, dry_run=not args.live)
            skipped += 1
            continue

        filename = create_needs_action(email, urgency, vault_root)
        created += 1

        # Cloud agents never modify Gmail state (FR-008)
        if args.live and not is_cloud():
            mark_as_read(service, email["id"])

        log_entry(log_file, component=COMPONENT, action="poll_email", status="success",
                  detail=f"Classified as {urgency}, created Needs_Action file",
                  gmail_id=email["id"], sender=email["sender"],
                  subject=email["subject"], urgency=urgency,
                  needs_action_file=filename, dry_run=not args.live,
                  correlation_id=email.get("_correlation_id", ""))

        print(f"  [{urgency.upper()}] {email['sender']}: {email['subject']} → {filename}")

    return created, skipped


def main() -> None:
    args = parse_args()

    # Validate FTE_ROLE on startup (Platinum tier)
    try:
        role = validate_startup()
        print(f"Gmail Watcher starting as FTE_ROLE={role}")
    except SystemExit:
        # FTE_ROLE not set — backward compat with Gold tier
        role = ""

    vault_path = args.vault_path or os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH)
    vault_root = Path(vault_path)
    log_file = vault_root / "Logs" / "gmail.jsonl"

    if not vault_root.exists():
        print(f"Error: Vault not found at {vault_root}")
        sys.exit(1)

    mode = "live" if args.live else "dry-run"
    interval = args.interval

    service = authenticate(args.live)
    processed_ids: set[str] = set()

    if interval <= 0:
        # Single-run mode
        print(f"Gmail Watcher [{mode}] — polling last {args.minutes} minutes")
        created, skipped = poll_once(service, args, vault_root, log_file, processed_ids)
        if created == 0 and skipped == 0:
            print("No unread emails found.")
            log_entry(log_file, component=COMPONENT, action="poll", status="success",
                      detail="No unread emails", dry_run=not args.live)
        else:
            print(f"\nDone: {created} Needs_Action files created, {skipped} skipped")
        return

    # Daemon mode with polling interval
    import signal

    print(f"Gmail Watcher [{mode}] — daemon mode, poll every {interval}s")
    log_entry(log_file, component=COMPONENT, action="startup", status="success",
              detail=f"Daemon started, poll every {interval}s", dry_run=not args.live)

    def shutdown(signum=None, frame=None):
        print("\nGmail watcher shutting down...")
        log_entry(log_file, component=COMPONENT, action="shutdown", status="success",
                  detail="Clean shutdown via signal")
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    import time
    try:
        while True:
            created, skipped = poll_once(service, args, vault_root, log_file, processed_ids)
            if created > 0 or skipped > 0:
                print(f"  Cycle: {created} created, {skipped} skipped")
            time.sleep(interval)
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
