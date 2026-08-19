"""
Pulls the last N Gmail messages and writes one frontmatter .md file per
message into <BRAIN_DIR>/gmail/.

No LLM calls here, on purpose — every field comes straight off the Gmail API
response. Classification/status reasoning happens later at query-time via
gbrain's hybrid retrieval + the synthesis LLM call reading real content, not
here at ingestion.
"""

import base64
import re
from pathlib import Path

from googleapiclient.discovery import build

from auth import get_credentials
from frontmatter_utils import write_frontmatter_file

COLLECTORS_DIR = Path(__file__).resolve().parent
GMAIL_OUT_DIR = COLLECTORS_DIR / "gmail"
MAX_MESSAGES = 50


def _get_header(headers, name):
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _extract_body(payload):
    """Walk the MIME tree and pull the best available text body."""
    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data")

    if mime_type == "text/plain" and body_data:
        return _b64_decode(body_data)

    if mime_type == "text/html" and body_data:
        return _strip_html(_b64_decode(body_data))

    for part in payload.get("parts", []) or []:
        text = _extract_body(part)
        if text:
            return text

    return ""


def _b64_decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def collect_gmail(max_messages: int = MAX_MESSAGES):
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    msg_list = service.users().messages().list(
        userId="me", maxResults=max_messages, labelIds=["SENT"]
    ).execute()

    messages = msg_list.get("messages", [])
    print(f"Found {len(messages)} messages, fetching details...")

    written = []
    for m in messages:
        full = service.users().messages().get(
            userId="me", id=m["id"], format="full"
        ).execute()

        headers = full["payload"].get("headers", [])
        subject = _get_header(headers, "Subject")
        sender = _get_header(headers, "From")
        to = _get_header(headers, "To")
        date = _get_header(headers, "Date")

        body = _extract_body(full["payload"]) or full.get("snippet", "")

        frontmatter = {
            "source": "gmail",
            "message_id": full["id"],
            "thread_id": full["threadId"],
            "from": sender,
            "to": to,
            "subject": subject,
            "date": date,
            "labels": full.get("labelIds", []),
        }

        path = write_frontmatter_file(GMAIL_OUT_DIR, full["id"], frontmatter, body)
        written.append(path)

    print(f"Wrote {len(written)} gmail frontmatter files to {GMAIL_OUT_DIR}")
    return written


if __name__ == "__main__":
    collect_gmail()