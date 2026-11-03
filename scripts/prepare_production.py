"""Create untracked production configuration and secrets with restrictive permissions."""
import os
import re
import secrets
import sys
from pathlib import Path

DEST = Path(__file__).resolve().parent.parent / ".env.production"


def main():
    if DEST.exists():
        sys.exit(".env.production exists; refusing to overwrite.")
    if len(sys.argv) != 3:
        sys.exit("Usage: python scripts/prepare_production.py example.org admin@example.org")
    domain, email = sys.argv[1:]
    if not re.fullmatch(r"(?=.{4,253}$)[a-z0-9]+(?:[.-][a-z0-9]+)+", domain):
        sys.exit("Enter a lowercase public DNS domain, without https://")
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        sys.exit("Enter a valid email.")
    lines = ["# Never commit these secrets.",
             "SITE_DOMAIN=" + domain,
             "ACME_EMAIL=" + email,
             "DJANGO_SECRET_KEY=" + secrets.token_urlsafe(60),
             "DB_PASSWORD=" + secrets.token_urlsafe(40), ""]
    fd = os.open(DEST, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("Created .env.production (private permissions). Store secrets securely.")


if __name__ == "__main__":
    main()
