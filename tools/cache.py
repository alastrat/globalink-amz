#!/usr/bin/env python3
"""File-based JSON cache with TTL.

Usage:
    python3 cache.py get <prefix> <id> [ttl_hours]  -> JSON or "null"
    python3 cache.py put <prefix> <id> <json>        -> "cached"
    python3 cache.py clear [prefix]                   -> "cleared"

Cache stored at /opt/nanoclaw/groups/owner/cache/ (host) or /workspace/group/cache/ (container).
"""

import json
import os
import sys
import time
from pathlib import Path

# Default TTL in hours per prefix
DEFAULT_TTL = {
    "catalog": 168,    # 7 days
    "pricing": 4,      # prices fluctuate
    "fees": 24,        # stable day-to-day
    "restrictions": 24,
    "scrape": 12,
    "exa": 24,
}

FALLBACK_TTL = 24  # hours


def get_cache_dir():
    """Resolve cache directory (works on host and in container)."""
    for d in ["/workspace/group/cache", str(Path(__file__).parent.parent / "cache")]:
        parent = os.path.dirname(d)
        if os.path.isdir(parent):
            os.makedirs(d, exist_ok=True)
            return d
    # Fallback to sibling of tools dir
    fallback = str(Path(__file__).parent.parent / "cache")
    os.makedirs(fallback, exist_ok=True)
    return fallback


def cache_path(cache_dir, prefix, item_id):
    """Get the file path for a cache entry."""
    safe_id = item_id.replace("/", "_").replace("\\", "_")
    prefix_dir = os.path.join(cache_dir, prefix)
    os.makedirs(prefix_dir, exist_ok=True)
    return os.path.join(prefix_dir, f"{safe_id}.json")


def cmd_get(prefix, item_id, ttl_hours=None):
    """Get cached value if not expired."""
    cache_dir = get_cache_dir()
    fpath = cache_path(cache_dir, prefix, item_id)

    if not os.path.exists(fpath):
        print("null")
        return

    try:
        with open(fpath, "r") as f:
            entry = json.load(f)
    except (json.JSONDecodeError, OSError):
        print("null")
        return

    if ttl_hours is None:
        ttl_hours = DEFAULT_TTL.get(prefix, FALLBACK_TTL)

    cached_at = entry.get("cached_at", 0)
    age_hours = (time.time() - cached_at) / 3600

    if age_hours > ttl_hours:
        print("null")
        return

    print(json.dumps(entry.get("data")))


def cmd_put(prefix, item_id, data_json):
    """Store a value in cache."""
    cache_dir = get_cache_dir()
    fpath = cache_path(cache_dir, prefix, item_id)

    try:
        data = json.loads(data_json)
    except json.JSONDecodeError:
        print(json.dumps({"error": "Invalid JSON data"}))
        sys.exit(1)

    entry = {"cached_at": time.time(), "data": data}
    with open(fpath, "w") as f:
        json.dump(entry, f)

    print("cached")


def cmd_clear(prefix=None):
    """Clear cache entries."""
    cache_dir = get_cache_dir()

    if prefix:
        prefix_dir = os.path.join(cache_dir, prefix)
        if os.path.isdir(prefix_dir):
            for f in os.listdir(prefix_dir):
                os.remove(os.path.join(prefix_dir, f))
    else:
        for d in os.listdir(cache_dir):
            dpath = os.path.join(cache_dir, d)
            if os.path.isdir(dpath):
                for f in os.listdir(dpath):
                    os.remove(os.path.join(dpath, f))

    print("cleared")


# --- Module API (for import from sp-api-query.py) ---

def get(prefix, item_id, ttl_hours=None):
    """Get cached value. Returns parsed data or None."""
    cache_dir = get_cache_dir()
    fpath = cache_path(cache_dir, prefix, item_id)

    if not os.path.exists(fpath):
        return None

    try:
        with open(fpath, "r") as f:
            entry = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

    if ttl_hours is None:
        ttl_hours = DEFAULT_TTL.get(prefix, FALLBACK_TTL)

    cached_at = entry.get("cached_at", 0)
    age_hours = (time.time() - cached_at) / 3600

    if age_hours > ttl_hours:
        return None

    return entry.get("data")


def put(prefix, item_id, data):
    """Store a value in cache. Data should be a dict/list (not JSON string)."""
    cache_dir = get_cache_dir()
    fpath = cache_path(cache_dir, prefix, item_id)

    entry = {"cached_at": time.time(), "data": data}
    with open(fpath, "w") as f:
        json.dump(entry, f)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 cache.py <get|put|clear> [args]")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "get":
        if len(sys.argv) < 4:
            print("Usage: python3 cache.py get <prefix> <id> [ttl_hours]")
            sys.exit(1)
        ttl = float(sys.argv[4]) if len(sys.argv) > 4 else None
        cmd_get(sys.argv[2], sys.argv[3], ttl)

    elif cmd == "put":
        if len(sys.argv) < 5:
            print("Usage: python3 cache.py put <prefix> <id> <json>")
            sys.exit(1)
        cmd_put(sys.argv[2], sys.argv[3], sys.argv[4])

    elif cmd == "clear":
        prefix = sys.argv[2] if len(sys.argv) > 2 else None
        cmd_clear(prefix)

    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
