#!/usr/bin/env python3
"""Exa Search Tool

Usage:
    python3 exa-search.py <query> [--num-results N] [--type neural|keyword]
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

EXA_API_KEY = os.environ.get("EXA_API_KEY", "")
EXA_BASE = "https://api.exa.ai"


def search(query, num_results=5, search_type="neural"):
    """Search using Exa API."""
    if not EXA_API_KEY:
        print(json.dumps({"error": "EXA_API_KEY not configured in tools/.env"}))
        sys.exit(1)

    data = json.dumps({
        "query": query,
        "numResults": num_results,
        "type": search_type,
        "contents": {
            "text": {"maxCharacters": 1000},
        },
    }).encode()

    req = urllib.request.Request(
        f"{EXA_BASE}/search",
        data=data,
        method="POST",
    )
    req.add_header("Content-Type", "application/json")
    req.add_header("User-Agent", "FBA-Research/1.0")
    req.add_header("x-api-key", EXA_API_KEY)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            results = result.get("results", [])
            output = []
            for i, r in enumerate(results, 1):
                output.append({
                    "rank": i,
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "snippet": r.get("text", "")[:300],
                    "published": r.get("publishedDate", ""),
                })
            print(json.dumps(output, indent=2))
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else ""
        print(json.dumps({"error": f"HTTP {e.code}: {body[:500]}"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 exa-search.py <query> [--num-results N] [--type neural|keyword]")
        sys.exit(1)

    query = sys.argv[1]
    num_results = 5
    search_type = "neural"

    if "--num-results" in sys.argv:
        num_results = int(sys.argv[sys.argv.index("--num-results") + 1])
    if "--type" in sys.argv:
        search_type = sys.argv[sys.argv.index("--type") + 1]

    search(query, num_results, search_type)


if __name__ == "__main__":
    main()
