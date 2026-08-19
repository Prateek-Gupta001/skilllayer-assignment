"""
Entry point: runs both collectors, then tells you the gbrain commands to
ingest the results.

Usage:
    python collect_all.py
"""

from gmail_collector import collect_gmail
from drive_collector import collect_drive

if __name__ == "__main__":
    print("=== Collecting Gmail ===")
    collect_gmail()

    print("\n=== Collecting Drive ===")
    collect_drive()

    print("\nDone. Now run inside ~/skilllayer-brain:")
    print("  gbrain sync")
    print("  gbrain embed --all")