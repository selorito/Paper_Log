"""Settings loaded from the .env file next to this script."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NOTES_DIR = ROOT / "notes"
CACHE_DIR = ROOT / ".cache"


def _load_env():
    env_file = ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_env()

PORT = int(os.environ.get("PORT", "5050"))
SITE_URL = os.environ.get("SITE_URL", f"http://localhost:{PORT}")
GITHUB_REPO_URL = os.environ.get("GITHUB_REPO_URL", "").rstrip("/")
CHALLENGE_TAG = os.environ.get("CHALLENGE_TAG", "#100DaysOfPapers")

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
MAIL_TO = os.environ.get("MAIL_TO", SMTP_USER)
