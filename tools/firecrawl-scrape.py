#!/usr/bin/env python3
"""Firecrawl Web Scraping Tool

Usage:
    python3 firecrawl-scrape.py <url> [--format markdown|json]
"""

import json
import os
import sys
import urllib.request
import urllib.error
from pathlib import Path


def load_env():
    """Load .env file from same directory as this script."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip("'\"")
                if key and value and key not in os.environ:
                    os.environ[key] = value


load_env()

FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


def scrape_url(url, output_format="markdown"):
    """Scrape a URL using Firecrawl API."""
    if not FIRECRAWL_API_KEY:
        print(json.dumps({"error": "FIRECRAWL_API_KEY not configured in tools/.env"}))
        sys.exit(1)

    data = json.dumps({
        "url": url,
        "formats": [output_format],
    }).encode()

    req = urllib.request.Request(
        f"{FIRECRAWL_BASE}/scrape",
        data=data,
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {FIRECRAWL_API_KEY}")

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            if output_format == "markdown":
                content = result.get("data", {}).get("markdown", "")
                if len(content) > 10000:
                    content = content[:10000] + "\n\n... [truncated]"
                print(content)
            else:
                print(json.dumps(result, indent=2))
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(json.dumps({"error": f"HTTP {e.code}: {body[:500]}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 firecrawl-scrape.py <url> [--format markdown|json]")
        sys.exit(1)

    url = sys.argv[1]
    fmt = "markdown"
    if "--format" in sys.argv:
        fmt = sys.argv[sys.argv.index("--format") + 1]

    scrape_url(url, fmt)


if __name__ == "__main__":
    main()
