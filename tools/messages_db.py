#!/usr/bin/env python3
"""Messages Database Query Tool

Read-only queries against NanoClaw's WhatsApp messages SQLite database.
Returns JSON to stdout for use by the Inngest worker API.

Usage:
    python3 messages_db.py list-chats
    python3 messages_db.py get-messages <chat_jid> [--limit 100] [--before TIMESTAMP]
"""

import json
import os
import sqlite3
import sys
from contextlib import contextmanager
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

DB_PATH = os.environ.get("MESSAGES_DB_PATH", "/data/store/messages.db")


@contextmanager
def get_db():
    """Open the messages SQLite database read-only; always closes on exit."""
    db_path = Path(DB_PATH)
    if not db_path.exists():
        yield None
        return
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def out(data):
    """Print JSON to stdout and exit."""
    print(json.dumps(data))
    sys.exit(0)


def err(msg):
    """Print error JSON to stdout and exit."""
    print(json.dumps({"error": msg}))
    sys.exit(1)


def get_arg(flag):
    """Get a CLI flag value, e.g. --limit 100 returns '100'."""
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return None


# --- Subcommands ---


def cmd_list_chats():
    """List all chats ordered by last_message_time DESC with message counts."""
    with get_db() as conn:
        if conn is None:
            out({"chats": []})

        rows = conn.execute(
            """
            SELECT
                c.jid,
                c.name,
                c.last_message_time,
                c.is_group,
                COUNT(m.id) AS message_count,
                (
                    SELECT m2.content
                    FROM messages m2
                    WHERE m2.chat_jid = c.jid
                    ORDER BY m2.timestamp DESC
                    LIMIT 1
                ) AS last_message_preview
            FROM chats c
            LEFT JOIN messages m ON m.chat_jid = c.jid
            WHERE c.jid NOT LIKE '%group_sync%'
              AND c.jid NOT LIKE '%status@%'
              AND c.name NOT LIKE '%group_sync%'
            GROUP BY c.jid
            HAVING message_count > 0
            ORDER BY c.last_message_time DESC
            """
        ).fetchall()

        chats = []
        for row in rows:
            chat = dict(row)
            # Truncate preview
            preview = chat.get("last_message_preview") or ""
            if len(preview) > 80:
                preview = preview[:80] + "..."
            chat["last_message_preview"] = preview
            chats.append(chat)

    out({"chats": chats})


def cmd_get_messages():
    """Get messages for a specific chat JID."""
    if len(sys.argv) < 3:
        err("get-messages requires a chat_jid argument")

    jid = sys.argv[2]

    limit = int(get_arg("--limit") or 200)
    if limit < 1:
        limit = 1
    if limit > 500:
        limit = 500

    before = get_arg("--before")

    with get_db() as conn:
        if conn is None:
            out({"messages": []})

        conditions = ["m.chat_jid = ?"]
        params = [jid]

        if before:
            conditions.append("m.timestamp < ?")
            params.append(before)

        where = " AND ".join(conditions)
        params.append(limit)

        rows = conn.execute(
            f"""
            SELECT
                m.id,
                m.sender,
                m.sender_name,
                m.content,
                m.timestamp,
                m.is_from_me,
                m.is_bot_message
            FROM messages m
            WHERE {where}
            ORDER BY m.timestamp ASC
            LIMIT ?
            """,
            params,
        ).fetchall()

        messages = [dict(row) for row in rows]

    out({"messages": messages})


# --- Main ---


def main():
    try:
        if len(sys.argv) < 2:
            err("Usage: python3 messages_db.py <command> [args]")

        cmd = sys.argv[1].lower()

        if cmd == "list-chats":
            cmd_list_chats()
        elif cmd == "get-messages":
            cmd_get_messages()
        else:
            err(f"Unknown command: {cmd}")
    except SystemExit:
        raise
    except Exception as e:
        err(str(e))


if __name__ == "__main__":
    main()
