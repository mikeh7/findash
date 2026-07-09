"""Data pipeline: pull ETF holdings, company news, and quotes from Finnhub,
plus server-side article-body extraction for the in-app reader.

All network calls degrade gracefully: if Finnhub is unreachable or a key is
missing, the app still runs on the seed universe and shows whatever is cached.
"""

import hashlib
import time
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup

import db
from config import FINNHUB_KEY, ETFS, SEED_UNIVERSE, LOOKBACK_DAYS

BASE = "https://finnhub.io/api/v1"
UA = {"User-Agent": "Mozilla/5.0 (compatible; SemiDash/1.0)"}


def _hash(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _get(client: httpx.Client, path: str, **params):
    params["token"] = FINNHUB_KEY
    r = client.get(f"{BASE}{path}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def resolve_universe() -> dict:
    """Union of SOXX + SMH holdings from Finnhub, or seed list on failure."""
    if not FINNHUB_KEY:
        return dict(SEED_UNIVERSE)
    universe = {}
    try:
        with httpx.Client() as client:
            for etf in ETFS:
                data = _get(client, "/etf/holdings", symbol=etf)
                for h in data.get("holdings", []):
                    sym = (h.get("symbol") or "").upper().strip()
                    name = h.get("name") or sym
                    # Skip cash, blanks, and non-equity lines.
                    if sym and sym.isalpha() and 1 <= len(sym) <= 5:
                        universe[sym] = name
    except Exception as e:
        print(f"[universe] holdings fetch failed ({e}); using seed list")
    # Merge seed to guarantee coverage even if the endpoint returns partial data.
    for sym, name in SEED_UNIVERSE.items():
        universe.setdefault(sym, name)
    return universe


def fetch_news_and_quotes():
    """Main scheduled job. Idempotent: safe to run repeatedly."""
    tickers = [t["symbol"] for t in db.get_tickers()]
    if not tickers:
        return
    since = datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)
    frm, to = since.strftime("%Y-%m-%d"), datetime.utcnow().strftime("%Y-%m-%d")
    cutoff_ts = int(since.timestamp())

    if not FINNHUB_KEY:
        print("[job] no FINNHUB_KEY set; skipping live fetch")
        return

    market_open = 0
    with httpx.Client(headers=UA) as client:
        try:
            status = _get(client, "/stock/market-status", exchange="US")
            market_open = 1 if status.get("isOpen") else 0
        except Exception:
            pass

        for sym in tickers:
            # News
            try:
                items = _get(client, "/company-news", symbol=sym, **{"from": frm, "to": to})
                for it in items:
                    url = it.get("url")
                    if not url or not it.get("headline"):
                        continue
                    db.upsert_article({
                        "id": _hash(url),
                        "ticker": sym,
                        "headline": it["headline"].strip(),
                        "summary": (it.get("summary") or "").strip(),
                        "url": url,
                        "source": it.get("source", ""),
                        "published": int(it.get("datetime", time.time())),
                    })
            except Exception as e:
                print(f"[news] {sym} failed: {e}")

            # Quote
            try:
                q = _get(client, "/quote", symbol=sym)
                db.upsert_quote({
                    "symbol": sym,
                    "price": q.get("c"),
                    "change_pct": q.get("dp"),
                    "prev_close": q.get("pc"),
                    "market_open": market_open,
                    "updated": int(time.time()),
                })
            except Exception as e:
                print(f"[quote] {sym} failed: {e}")

    db.prune(cutoff_ts)
    print(f"[job] refresh complete at {datetime.utcnow().isoformat()}Z")


def extract_body(url: str) -> str:
    """Fetch and clean article text server-side for the in-app reader.

    Returns simplified HTML (headings + paragraphs). Bypasses X-Frame-Options
    since we render our own DOM, which also makes scroll-to-bottom detectable.
    """
    try:
        with httpx.Client(headers=UA, follow_redirects=True, timeout=20) as client:
            r = client.get(url)
            r.raise_for_status()
            html = r.text
    except Exception as e:
        return f"<p class='err'>Couldn't load this article ({e}). Use “Open original”.</p>"

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript"]):
        tag.decompose()

    article = soup.find("article") or soup.find("main") or soup.body or soup
    parts = []
    for el in article.find_all(["h1", "h2", "h3", "p", "li"]):
        text = el.get_text(" ", strip=True)
        if len(text) < 25:  # drop nav crumbs, bylines fragments
            continue
        tag = el.name if el.name in ("h1", "h2", "h3") else "p"
        parts.append(f"<{tag}>{BeautifulSoup(text, 'html.parser').get_text()}</{tag}>")
        if len(parts) > 120:
            break

    if not parts:
        return "<p class='err'>No readable text extracted. Use “Open original”.</p>"
    return "\n".join(parts)
