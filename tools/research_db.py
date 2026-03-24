#!/usr/bin/env python3
"""Research Database CRUD Tool

SQLite-backed storage for ASIN research results.
Stores research runs, product catalog data, and point-in-time snapshots
with pricing, fees, scoring, and restriction data.

Usage:
    python3 research_db.py init
    python3 research_db.py save-restrictions '<json>'
    python3 research_db.py save-research '<json>'
    python3 research_db.py export-products [--from DATE] [--to DATE] [--category CAT] [--grade G] [--restricted 0|1]
    python3 research_db.py export-runs [--limit N]
    python3 research_db.py export-stats [--from DATE] [--to DATE]
    python3 research_db.py export-history <ASIN>
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

DB_PATH = os.environ.get("RESEARCH_DB_PATH", "/cache/research.db")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS research_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp TEXT NOT NULL DEFAULT (datetime('now')),
  source TEXT NOT NULL,
  total_asins INTEGER NOT NULL DEFAULT 0,
  approved_count INTEGER DEFAULT 0,
  restricted_count INTEGER DEFAULT 0,
  notes TEXT
);

CREATE TABLE IF NOT EXISTS products (
  asin TEXT PRIMARY KEY,
  title TEXT,
  brand TEXT,
  category TEXT,
  bsr_category TEXT,
  main_image_url TEXT,
  weight_lb REAL,
  first_seen TEXT NOT NULL DEFAULT (datetime('now')),
  last_updated TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS asin_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL REFERENCES research_runs(id),
  asin TEXT NOT NULL REFERENCES products(asin),
  timestamp TEXT NOT NULL DEFAULT (datetime('now')),
  buy_box_price REAL,
  wholesale_cost REAL,
  bsr INTEGER,
  fba_offer_count INTEGER,
  fbm_offer_count INTEGER,
  amazon_is_seller INTEGER DEFAULT 0,
  estimated_monthly_sales INTEGER,
  demand_indicator TEXT,
  referral_fee REAL,
  fba_fee REAL,
  total_fees REAL,
  profit REAL,
  roi REAL,
  margin REAL,
  score REAL,
  grade TEXT,
  restricted INTEGER DEFAULT 0,
  restriction_reasons TEXT
);

CREATE INDEX IF NOT EXISTS idx_snapshots_asin ON asin_snapshots(asin);
CREATE INDEX IF NOT EXISTS idx_snapshots_asin_time ON asin_snapshots(asin, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_snapshots_run ON asin_snapshots(run_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON asin_snapshots(timestamp);
CREATE INDEX IF NOT EXISTS idx_snapshots_grade ON asin_snapshots(grade);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
"""


@contextmanager
def get_db():
    """Open (or create) the SQLite database; always closes on exit."""
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
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
    """Get a CLI flag value, e.g. --limit 10 returns '10'."""
    if flag in sys.argv:
        idx = sys.argv.index(flag)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return None


# ─── Subcommands ──────────────────────────────────────────────

def cmd_init():
    """Create tables and indexes."""
    with get_db() as conn:
        conn.executescript(SCHEMA_SQL)
    out({"ok": True})


def cmd_save_restrictions():
    """Save restriction-check results."""
    if len(sys.argv) < 3:
        err("save-restrictions requires a JSON argument")

    data = json.loads(sys.argv[2])
    source = data.get("source", "unknown")
    approved = data.get("approved", [])
    restricted = data.get("restricted", {})

    total = len(approved) + len(restricted)
    approved_count = len(approved)
    restricted_count = len(restricted)

    with get_db() as conn:
        cur = conn.cursor()

        # Create run
        cur.execute(
            "INSERT INTO research_runs (source, total_asins, approved_count, restricted_count) VALUES (?, ?, ?, ?)",
            (source, total, approved_count, restricted_count),
        )
        run_id = cur.lastrowid

        saved = 0

        # Approved ASINs
        for asin in approved:
            # Upsert product
            cur.execute(
                "INSERT INTO products (asin) VALUES (?) ON CONFLICT(asin) DO UPDATE SET last_updated=datetime('now')",
                (asin,),
            )
            # Create snapshot
            cur.execute(
                "INSERT INTO asin_snapshots (run_id, asin, restricted) VALUES (?, ?, 0)",
                (run_id, asin),
            )
            saved += 1

        # Restricted ASINs
        for asin, info in restricted.items():
            reasons = info.get("reasons", [])
            reasons_json = json.dumps(reasons) if reasons else None

            # Upsert product
            cur.execute(
                "INSERT INTO products (asin) VALUES (?) ON CONFLICT(asin) DO UPDATE SET last_updated=datetime('now')",
                (asin,),
            )
            # Create snapshot
            cur.execute(
                "INSERT INTO asin_snapshots (run_id, asin, restricted, restriction_reasons) VALUES (?, ?, 1, ?)",
                (run_id, asin, reasons_json),
            )
            saved += 1

        conn.commit()
    out({"run_id": run_id, "saved": saved})


def cmd_save_research():
    """Save full product research results."""
    if len(sys.argv) < 3:
        err("save-research requires a JSON argument")

    data = json.loads(sys.argv[2])
    source = data.get("source", "unknown")
    products = data.get("products", [])

    total = len(products)
    approved_count = sum(1 for p in products if not p.get("restricted"))
    restricted_count = sum(1 for p in products if p.get("restricted"))

    with get_db() as conn:
        cur = conn.cursor()

        # Create run
        cur.execute(
            "INSERT INTO research_runs (source, total_asins, approved_count, restricted_count) VALUES (?, ?, ?, ?)",
            (source, total, approved_count, restricted_count),
        )
        run_id = cur.lastrowid

        saved = 0
        for p in products:
            asin = p.get("asin")
            if not asin:
                continue

            # Upsert product catalog fields
            cur.execute(
                """INSERT INTO products (asin, title, brand, category, bsr_category, main_image_url, weight_lb)
                   VALUES (?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(asin) DO UPDATE SET
                     title=COALESCE(excluded.title, products.title),
                     brand=COALESCE(excluded.brand, products.brand),
                     category=COALESCE(excluded.category, products.category),
                     bsr_category=COALESCE(excluded.bsr_category, products.bsr_category),
                     main_image_url=COALESCE(excluded.main_image_url, products.main_image_url),
                     weight_lb=COALESCE(excluded.weight_lb, products.weight_lb),
                     last_updated=datetime('now')""",
                (
                    asin,
                    p.get("title"),
                    p.get("brand"),
                    p.get("category"),
                    p.get("bsr_category"),
                    p.get("main_image_url"),
                    p.get("weight_lb"),
                ),
            )

            # Create snapshot with all fields
            restriction_reasons = p.get("restriction_reasons")
            if isinstance(restriction_reasons, list):
                restriction_reasons = json.dumps(restriction_reasons)

            cur.execute(
                """INSERT INTO asin_snapshots (
                     run_id, asin, buy_box_price, wholesale_cost, bsr,
                     fba_offer_count, fbm_offer_count, amazon_is_seller,
                     estimated_monthly_sales, demand_indicator,
                     referral_fee, fba_fee, total_fees,
                     profit, roi, margin, score, grade,
                     restricted, restriction_reasons
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run_id,
                    asin,
                    p.get("buy_box_price"),
                    p.get("wholesale_cost"),
                    p.get("bsr"),
                    p.get("fba_offer_count"),
                    p.get("fbm_offer_count"),
                    p.get("amazon_is_seller", 0),
                    p.get("estimated_monthly_sales"),
                    p.get("demand_indicator"),
                    p.get("referral_fee"),
                    p.get("fba_fee"),
                    p.get("total_fees"),
                    p.get("profit"),
                    p.get("roi"),
                    p.get("margin"),
                    p.get("score"),
                    p.get("grade"),
                    1 if p.get("restricted") else 0,
                    restriction_reasons,
                ),
            )
            saved += 1

        conn.commit()
    out({"run_id": run_id, "saved": saved})


def cmd_export_products():
    """Query latest snapshot per ASIN with optional filters."""
    # Build WHERE clauses from flags
    conditions = []
    params = []

    cat = get_arg("--category")
    if cat:
        conditions.append("p.category = ?")
        params.append(cat)

    grade = get_arg("--grade")
    if grade:
        conditions.append("s.grade = ?")
        params.append(grade)

    restricted = get_arg("--restricted")
    if restricted is not None:
        conditions.append("s.restricted = ?")
        params.append(int(restricted))

    from_date = get_arg("--from")
    if from_date:
        conditions.append("s.timestamp >= ?")
        params.append(from_date)

    to_date = get_arg("--to")
    if to_date:
        conditions.append("s.timestamp <= ?")
        params.append(to_date)

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    query = f"""
        SELECT p.asin, p.title, p.brand, p.category, p.bsr_category,
               p.main_image_url, p.weight_lb, p.first_seen, p.last_updated,
               s.buy_box_price, s.wholesale_cost, s.bsr,
               s.fba_offer_count, s.fbm_offer_count, s.amazon_is_seller,
               s.estimated_monthly_sales, s.demand_indicator,
               s.referral_fee, s.fba_fee, s.total_fees,
               s.profit, s.roi, s.margin, s.score, s.grade,
               s.restricted, s.restriction_reasons, s.timestamp as snapshot_time
        FROM products p
        JOIN (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY asin ORDER BY timestamp DESC, id DESC) as rn
            FROM asin_snapshots
        ) s ON p.asin = s.asin AND s.rn = 1
        {where}
        ORDER BY s.score DESC NULLS LAST
    """

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        products = [dict(row) for row in rows]
    # Remove the internal rn column
    for p in products:
        p.pop("rn", None)

    out({"products": products})


def cmd_export_runs():
    """List recent research runs."""
    limit = int(get_arg("--limit") or 30)

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM research_runs ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        ).fetchall()
        runs = [dict(row) for row in rows]
    out({"runs": runs})


def cmd_export_stats():
    """Aggregate KPIs across latest snapshots."""
    conditions = []
    params = []

    from_date = get_arg("--from")
    if from_date:
        conditions.append("s.timestamp >= ?")
        params.append(from_date)

    to_date = get_arg("--to")
    if to_date:
        conditions.append("s.timestamp <= ?")
        params.append(to_date)

    where = ""
    if conditions:
        where = "WHERE " + " AND ".join(conditions)

    # Latest snapshot per ASIN (with optional date filters applied)
    latest_query = f"""
        SELECT *
        FROM (
            SELECT *, ROW_NUMBER() OVER (PARTITION BY asin ORDER BY timestamp DESC, id DESC) as rn
            FROM asin_snapshots
            {where}
        ) WHERE rn = 1
    """

    with get_db() as conn:
        # Total products and runs
        total_products = conn.execute(
            f"SELECT COUNT(DISTINCT asin) FROM ({latest_query})", params
        ).fetchone()[0]

        total_runs = conn.execute("SELECT COUNT(*) FROM research_runs").fetchone()[0]

        # Aggregates from latest snapshots
        agg = conn.execute(
            f"""SELECT
                  AVG(roi) as avg_roi,
                  AVG(score) as avg_score,
                  SUM(CASE WHEN restricted = 0 THEN 1 ELSE 0 END) as approved_count,
                  SUM(CASE WHEN restricted = 1 THEN 1 ELSE 0 END) as restricted_count
                FROM ({latest_query})""",
            params,
        ).fetchone()

        avg_roi = round(agg["avg_roi"], 2) if agg["avg_roi"] is not None else 0
        avg_score = round(agg["avg_score"], 2) if agg["avg_score"] is not None else 0
        approved_count = agg["approved_count"] or 0
        restricted_count = agg["restricted_count"] or 0

        # Grade distribution
        grade_rows = conn.execute(
            f"SELECT grade, COUNT(*) as cnt FROM ({latest_query}) WHERE grade IS NOT NULL GROUP BY grade",
            params,
        ).fetchall()
        grade_distribution = {row["grade"]: row["cnt"] for row in grade_rows}

        # Category distribution (from products table joined with latest snapshots)
        cat_rows = conn.execute(
            f"""SELECT p.category, COUNT(*) as cnt
                FROM ({latest_query}) s
                JOIN products p ON s.asin = p.asin
                WHERE p.category IS NOT NULL
                GROUP BY p.category""",
            params,
        ).fetchall()
        category_distribution = {row["category"]: row["cnt"] for row in cat_rows}

    out({
        "total_products": total_products,
        "total_runs": total_runs,
        "avg_roi": avg_roi,
        "avg_score": avg_score,
        "approved_count": approved_count,
        "restricted_count": restricted_count,
        "grade_distribution": grade_distribution,
        "category_distribution": category_distribution,
    })


def cmd_export_history():
    """Time-series snapshots for one ASIN."""
    if len(sys.argv) < 3:
        err("export-history requires an ASIN argument")

    asin = sys.argv[2]
    with get_db() as conn:
        rows = conn.execute(
            """SELECT s.*, r.source
               FROM asin_snapshots s
               JOIN research_runs r ON s.run_id = r.id
               WHERE s.asin = ?
               ORDER BY s.timestamp ASC""",
            (asin,),
        ).fetchall()
        snapshots = [dict(row) for row in rows]
    out({"asin": asin, "snapshots": snapshots})


# ─── Main ─────────────────────────────────────────────────────

def main():
    try:
        if len(sys.argv) < 2:
            err("Usage: python3 research_db.py <command> [args]")

        cmd = sys.argv[1].lower()

        if cmd == "init":
            cmd_init()
        elif cmd == "save-restrictions":
            cmd_save_restrictions()
        elif cmd == "save-research":
            cmd_save_research()
        elif cmd == "export-products":
            cmd_export_products()
        elif cmd == "export-runs":
            cmd_export_runs()
        elif cmd == "export-stats":
            cmd_export_stats()
        elif cmd == "export-history":
            cmd_export_history()
        else:
            err(f"Unknown command: {cmd}")
    except SystemExit:
        raise
    except Exception as e:
        err(str(e))


if __name__ == "__main__":
    main()
