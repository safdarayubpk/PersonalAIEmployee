"""Email actions using Gmail API with OAuth2.

Reuses the same OAuth2 credentials as gmail-watcher (credentials.json / token.json).
Requires: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2

Functions:
    send_email  — Send an email (HITL required)
    draft_email — Create a local draft in vault Plans/ (no HITL)
"""

import base64
import json
import os
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    raise ImportError(
        "Gmail API dependencies not installed. "
        "Run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
    )

PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT",
                    Path(__file__).resolve().parent.parent.parent))
CREDENTIALS_FILE = PROJECT_ROOT / "credentials.json"
TOKEN_FILE = PROJECT_ROOT / "token.json"
DEFAULT_VAULT_PATH = "/home/safdarayub/Documents/AI_Employee_Vault"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]


def _get_gmail_service():
    """Authenticate and return Gmail API service object."""
    creds = None

    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"credentials.json not found at {CREDENTIALS_FILE}. "
                    "See .claude/skills/gmail-watcher/references/gmail_api_setup.md"
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
            creds = flow.run_local_server(port=0)

        TOKEN_FILE.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _build_mime(to: str, subject: str, body: str,
                cc: str = "", bcc: str = "",
                is_html: bool = False,
                attachments: list | None = None) -> MIMEMultipart:
    """Build a MIME message."""
    msg = MIMEMultipart()
    msg["To"] = to
    msg["Subject"] = subject
    if cc:
        msg["Cc"] = cc
    if bcc:
        msg["Bcc"] = bcc

    content_type = "html" if is_html else "plain"
    msg.attach(MIMEText(body, content_type))

    for attachment_path in (attachments or []):
        path = Path(attachment_path)
        if not path.exists():
            raise FileNotFoundError(f"Attachment not found: {attachment_path}")
        part = MIMEBase("application", "octet-stream")
        part.set_payload(path.read_bytes())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", "attachment", filename=path.name)
        msg.attach(part)

    return msg


def send_email(to: str, subject: str, body: str,
               cc: str = "", bcc: str = "",
               is_html: bool = False,
               attachments: list | None = None,
               **kwargs) -> dict:
    """Send an email via Gmail API.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body (plain text or HTML)
        cc: CC recipients (comma-separated)
        bcc: BCC recipients (comma-separated)
        is_html: Whether body is HTML
        attachments: List of file paths to attach

    Returns:
        dict with status, message_id, to, subject
    """
    service = _get_gmail_service()
    mime_msg = _build_mime(to, subject, body, cc, bcc, is_html, attachments)

    raw = base64.urlsafe_b64encode(mime_msg.as_bytes()).decode("ascii")
    result = service.users().messages().send(
        userId="me",
        body={"raw": raw}
    ).execute()

    return {
        "status": "sent",
        "message_id": result.get("id", ""),
        "to": to,
        "subject": subject,
    }


def draft_email(to: str, subject: str, body: str,
                cc: str = "", bcc: str = "",
                is_html: bool = False,
                **kwargs) -> dict:
    """Create a local email draft as a markdown file in vault Plans/.

    Does NOT use Gmail API — writes locally only. Safe, no HITL needed.

    Args:
        to: Recipient email address
        subject: Email subject line
        body: Email body content
        cc: CC recipients
        bcc: BCC recipients
        is_html: Whether body is HTML

    Returns:
        dict with status, draft_file path
    """
    vault_path = kwargs.get("vault_path",
                            os.environ.get("VAULT_PATH", DEFAULT_VAULT_PATH))
    vault_root = Path(vault_path)
    plans_dir = vault_root / "Plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc)
    ts_str = ts.strftime("%Y-%m-%dT%H:%M:%S")
    ts_file = ts.strftime("%Y%m%d-%H%M%S")

    slug = subject[:40].lower().replace(" ", "-").replace("/", "-")
    filename = f"draft-email-{slug}-{ts_file}.md"
    filepath = plans_dir / filename

    content = f"""---
title: "Email Draft: {subject}"
created: "{ts_str}"
type: email-draft
source: action-executor
status: draft
---

## Email Draft

- **To**: {to}
- **Subject**: {subject}
"""
    if cc:
        content += f"- **CC**: {cc}\n"
    if bcc:
        content += f"- **BCC**: {bcc}\n"
    content += f"- **Format**: {'HTML' if is_html else 'Plain text'}\n"
    content += f"\n## Body\n\n{body}\n"

    # Atomic write
    tmp = filepath.with_suffix(filepath.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.rename(tmp, filepath)

    return {
        "status": "drafted",
        "draft_file": str(filepath),
        "to": to,
        "subject": subject,
    }
