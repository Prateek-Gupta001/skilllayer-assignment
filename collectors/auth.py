"""
Shared Google OAuth helper for Gmail + Drive collectors.

SETUP REQUIRED BEFORE RUNNING (one-time):

1. Go to https://console.cloud.google.com/ and create a project (or reuse one).

2. Enable APIs: APIs & Services > Library > enable both:
     - Gmail API
     - Google Drive API

3. Configure consent screen: APIs & Services > OAuth consent screen
     - User type: External
     - Add yourself as a Test User (your own Gmail address) — required since
       the app won't be verified by Google, and test users can still authorize it.

4. Create credentials: APIs & Services > Credentials > Create Credentials > OAuth client ID
     - Application type: Desktop app
     - Download the JSON, save it as `credentials.json` in this same directory
       (next to this file).

5. First run opens a browser window asking you to authorize access. A
   `token.json` gets cached locally afterward so you won't need to re-auth
   on every run (it auto-refreshes).

NOTE (WSL): `flow.run_local_server()` below spins up a tiny local server and
opens your default browser. WSL2 forwards localhost to Windows automatically
on modern builds, so this should just work — if the browser doesn't open
automatically, it'll print a URL in the terminal, paste that into your
Windows browser manually.

Scopes are read-only for both Gmail and Drive — this script cannot modify or
delete anything in your account.
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.json"


def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    f"{CREDENTIALS_FILE} not found. See setup instructions at "
                    f"the top of auth.py — you need to download it from "
                    f"Google Cloud Console first."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds