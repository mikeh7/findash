"""Storage layer with two interchangeable backends.

- If DATABASE_URL is set (as on Render), uses Postgres via psycopg — data
  persists across restarts and redeploys.
- Otherwise falls back to a local SQLite file, so the app still runs on a
  laptop with zero setup.

The rest of the app calls the same functions regardless of backend.
"""

import os
import threading
from contextlib import contextmanager

from config import DB_PATH

DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_PG = bool(DATABASE_URL)

if USE_PG:
    import psycopg
    from psycopg.rows import dict_row
    # Render sometimes hands out a postgres:// URL; psycopg wants postgresql://
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    PH = "%s"          # Postgres placeholder
else:
    import sqlite3
    PH = "?"           # SQLite placeholder
    _local = threading.local()


# ---- connection handling -------------------------------------------------

@contextmanager
def cursor():
    if USE_PG:
        conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, autocommit=False)
        try:
            with conn.cursor() as cur:
                yield cur
            conn.commit()
        finally:
            conn.close()
    else:
        if not hasattr(_local, "conn"):
            _local.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            _local.conn.row_factory = sqlite3.Row
            _local.conn.execute("PRAGMA journal_mode=WAL")
        conn = _local.conn
        cur = conn.cursor()
        try:
            yield cur
            conn.commit()
        finally:
            cur.close()


def _rows(cur):
    return [dict(r) for r in cur.fetchall()]


# ---- schema --------------------------------------------------------------

def init_db():
    read_default = "BOOLEAN DEFAULT FALSE" if USE_PG else "INTEGER DEFAULT 0"
    with cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS tickers (
                symbol TEXT PRIMARY KEY,
                name   TEXT NOT NULL
            )
        """)
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS articles (
                id           TEXT PRIMARY KEY,
                ticker       TEXT NOT NULL,
                headline     TEXT NOT NULL,
                summary      TEXT,
                url          TEXT NOT NULL,
                source       TEXT,
                published    BIGINT NOT NULL,
                read         {read_default},
                fetched_body TEXT
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                symbol       TEXT PRIMARY KEY,
                price        DOUBLE PRECISION,
                change_pct   DOUBLE PRECISION,
                prev_close   DOUBLE PRECISION,
                market_open  INTEGER,
                updated      BIGINT
            )
        """) if USE_PG else cur.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                symbol       TEXT PRIMARY KEY,
                price        REAL,
                change_pct   REAL,
                prev_close   REAL,
                market_open  INTEGER,
                updated      INTEGER
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_pub ON articles(published DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_articles_ticker ON articles(ticker)")


# ---- writes --------------------------------------------------------------

def upsert_tickers(universe: dict):
    with cursor() as cur:
        for symbol, name in universe.items():
            cur.execute(
                f"INSERT INTO tickers(symbol, name) VALUES ({PH}, {PH}) "
                "ON CONFLICT(symbol) DO UPDATE SET name=EXCLUDED.name",
                (symbol, name),
            )


def upsert_article(a: dict):
    """Insert if new; never overwrite read-state on existing rows."""
    with cursor() as cur:
        cur.execute(
            f"INSERT INTO articles(id, ticker, headline, summary, url, source, published) "
            f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}, {PH}) "
            "ON CONFLICT(id) DO NOTHING",
            (a["id"], a["ticker"], a["headline"], a["summary"],
             a["url"], a["source"], a["published"]),
        )


def upsert_quote(q: dict):
    with cursor() as cur:
        cur.execute(
            f"INSERT INTO quotes(symbol, price, change_pct, prev_close, market_open, updated) "
            f"VALUES ({PH}, {PH}, {PH}, {PH}, {PH}, {PH}) "
            "ON CONFLICT(symbol) DO UPDATE SET "
            "price=EXCLUDED.price, change_pct=EXCLUDED.change_pct, "
            "prev_close=EXCLUDED.prev_close, market_open=EXCLUDED.market_open, "
            "updated=EXCLUDED.updated",
            (q["symbol"], q["price"], q["change_pct"], q["prev_close"],
             q["market_open"], q["updated"]),
        )


def save_body(article_id: str, body: str):
    with cursor() as cur:
        cur.execute(f"UPDATE articles SET fetched_body = {PH} WHERE id = {PH}",
                    (body, article_id))


def mark_read(article_id: str):
    val = True if USE_PG else 1
    with cursor() as cur:
        cur.execute(f"UPDATE articles SET read = {PH} WHERE id = {PH}", (val, article_id))


def prune(before_ts: int):
    with cursor() as cur:
        cur.execute(f"DELETE FROM articles WHERE published < {PH}", (before_ts,))


# ---- reads ---------------------------------------------------------------

def get_tickers():
    with cursor() as cur:
        cur.execute("SELECT symbol, name FROM tickers ORDER BY symbol")
        return _rows(cur)


def get_articles(since_ts: int, tickers=None):
    q = ("SELECT a.*, t.name AS company, "
         "q.price, q.change_pct, q.prev_close, q.market_open "
         "FROM articles a "
         "JOIN tickers t ON t.symbol = a.ticker "
         "LEFT JOIN quotes q ON q.symbol = a.ticker "
         f"WHERE a.published >= {PH} ")
    params = [since_ts]
    if tickers:
        placeholders = ",".join([PH] * len(tickers))
        q += f"AND a.ticker IN ({placeholders}) "
        params += list(tickers)
    q += "ORDER BY a.published DESC"
    with cursor() as cur:
        cur.execute(q, params)
        rows = _rows(cur)
    # Normalise the read flag to 0/1 so the frontend logic is backend-agnostic.
    for r in rows:
        r["read"] = 1 if r.get("read") else 0
    return rows


def get_article(article_id: str):
    with cursor() as cur:
        cur.execute(f"SELECT * FROM articles WHERE id = {PH}", (article_id,))
        rows = _rows(cur)
    if not rows:
        return None
    r = rows[0]
    r["read"] = 1 if r.get("read") else 0
    return r
