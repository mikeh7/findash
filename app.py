"""FastAPI application: serves the API and the single-page frontend,
and runs the 08:00 / 13:00 Europe/London refresh via APScheduler.
"""

import os
import time
from datetime import datetime, timedelta

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import db
import pipeline
from config import SCHEDULE_HOURS, TIMEZONE, LOOKBACK_DAYS

HERE = os.path.dirname(__file__)
app = FastAPI(title="SemiDash")

scheduler = BackgroundScheduler(timezone=TIMEZONE)


@app.on_event("startup")
def startup():
    db.init_db()
    universe = pipeline.resolve_universe()
    db.upsert_tickers(universe)
    # Populate immediately so the dashboard isn't empty on first run.
    try:
        pipeline.fetch_news_and_quotes()
    except Exception as e:
        print(f"[startup] initial fetch skipped: {e}")
    for hour in SCHEDULE_HOURS:
        scheduler.add_job(
            pipeline.fetch_news_and_quotes,
            CronTrigger(hour=hour, minute=0, timezone=TIMEZONE),
            id=f"refresh-{hour}",
            replace_existing=True,
        )
    scheduler.start()
    print(f"[startup] scheduled refresh at {SCHEDULE_HOURS} {TIMEZONE}")


@app.on_event("shutdown")
def shutdown():
    if scheduler.running:
        scheduler.shutdown(wait=False)


@app.get("/api/tickers")
def api_tickers():
    return db.get_tickers()


# On the free tier the service sleeps when idle, so scheduled jobs may not fire
# while it's asleep. As a safety net, if the newest article is older than this
# many seconds when someone opens the dashboard, do a fresh pull on wake.
STALE_AFTER = 3 * 3600  # 3 hours


def _refresh_if_stale():
    try:
        recent = db.get_articles(int(time.time()) - STALE_AFTER)
        if not recent:
            pipeline.fetch_news_and_quotes()
    except Exception as e:
        print(f"[wake-refresh] skipped: {e}")


@app.get("/api/articles")
def api_articles(tickers: str = ""):
    _refresh_if_stale()
    since = int((datetime.utcnow() - timedelta(days=LOOKBACK_DAYS)).timestamp())
    selected = [t for t in tickers.split(",") if t] or None
    rows = db.get_articles(since, selected)
    return rows


@app.get("/api/article/{article_id}")
def api_article(article_id: str):
    a = db.get_article(article_id)
    if not a:
        raise HTTPException(404, "Article not found")
    if not a.get("fetched_body"):
        body = pipeline.extract_body(a["url"])
        db.save_body(article_id, body)
        a["fetched_body"] = body
    return a


@app.post("/api/article/{article_id}/read")
def api_mark_read(article_id: str):
    if not db.get_article(article_id):
        raise HTTPException(404, "Article not found")
    db.mark_read(article_id)
    return {"ok": True}


@app.post("/api/refresh")
def api_refresh():
    """Manual trigger, handy for the prototype."""
    pipeline.fetch_news_and_quotes()
    return {"ok": True, "at": int(time.time())}


@app.get("/")
def index():
    return FileResponse(os.path.join(HERE, "static", "index.html"))


app.mount("/static", StaticFiles(directory=os.path.join(HERE, "static")), name="static")
