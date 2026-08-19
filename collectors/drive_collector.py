"""
Pulls the last N modified Drive files and writes one frontmatter .md file per
file into <BRAIN_DIR>/drive/.

Text content is extracted for Google-native docs (via export) and plain text
files. Other binary types (PDF, images, etc.) are recorded as metadata-only —
a stated non-goal for this scope, not a bug: full binary text extraction
(PDF parsing, OCR) is a separate concern from proving cross-source retrieval.
"""

import io
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from auth import get_credentials
from frontmatter_utils import write_frontmatter_file

COLLECTORS_DIR = Path(__file__).resolve().parent
DRIVE_OUT_DIR = COLLECTORS_DIR / "drive"
MAX_FILES = 50

# Google-native types we know how to export as plain text
EXPORTABLE_MIMETYPES = {
    "application/vnd.google-apps.document": "text/plain",
}

# Non-exportable but directly downloadable-as-text types
DIRECT_TEXT_MIMETYPES = {"text/plain", "text/markdown", "text/csv"}


def _extract_text(service, file_id: str, mime_type: str) -> str:
    try:
        if mime_type in EXPORTABLE_MIMETYPES:
            data = service.files().export(
                fileId=file_id, mimeType=EXPORTABLE_MIMETYPES[mime_type]
            ).execute()
            return data.decode("utf-8", errors="replace") if isinstance(data, bytes) else data

        if mime_type in DIRECT_TEXT_MIMETYPES:
            request = service.files().get_media(fileId=file_id)
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buf.getvalue().decode("utf-8", errors="replace")

    except Exception as e:
        return f"[content extraction failed: {e}]"

    return "[binary file — content not extracted for this scope, see metadata above]"


def collect_drive(max_files: int = MAX_FILES):
    creds = get_credentials()
    service = build("drive", "v3", credentials=creds)

    results = service.files().list(
        pageSize=max_files,
        orderBy="modifiedTime desc",
        fields="files(id, name, mimeType, modifiedTime, webViewLink, owners, size)",
    ).execute()

    files = results.get("files", [])
    print(f"Found {len(files)} files, fetching content...")

    written = []
    for f in files:
        body = _extract_text(service, f["id"], f["mimeType"])

        owner_email = ""
        if f.get("owners"):
            owner_email = f["owners"][0].get("emailAddress", "")

        frontmatter = {
            "source": "drive",
            "file_id": f["id"],
            "filename": f["name"],
            "mime_type": f["mimeType"],
            "modified_time": f.get("modifiedTime", ""),
            "owner": owner_email,
            "web_view_link": f.get("webViewLink", ""),
            "size_bytes": f.get("size", ""),
        }

        path = write_frontmatter_file(DRIVE_OUT_DIR, f["id"], frontmatter, body)
        written.append(path)

    print(f"Wrote {len(written)} drive frontmatter files to {DRIVE_OUT_DIR}")
    return written


if __name__ == "__main__":
    collect_drive()