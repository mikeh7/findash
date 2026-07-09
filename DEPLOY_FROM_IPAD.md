# Deploy SemiDash from an iPad (no computer, no terminal)

Everything below happens in Safari. Two accounts needed, both free: GitHub and Render.
Total time ~15 minutes. You'll paste in one secret (your Finnhub key) and click through the rest.

---

## Step 1 — Get a Finnhub API key (2 min)

1. Go to **finnhub.io** and sign up (free).
2. On your dashboard, copy the **API key**. Keep the tab open — you'll paste it in Step 4.

## Step 2 — Put the code on GitHub (5 min)

1. Go to **github.com**, sign up / log in.
2. Tap **+** (top right) → **New repository**.
3. Name it `semidash`, leave it **Public**, tap **Create repository**.
4. On the new repo page, tap **uploading an existing file** (the link in the
   "Quick setup" box), or go to **Add file → Upload files**.
5. Upload **all** the project files, keeping the structure:
   - `app.py`, `db.py`, `pipeline.py`, `config.py`
   - `requirements.txt`, `render.yaml`
   - the **`static`** folder containing `index.html`
   > Tip: to upload the `static` folder from an iPad, use **Add file → Create new file**,
   > type `static/index.html` as the name (the `static/` prefix makes the folder), then
   > paste the file contents. Or upload a zip via the Files app and extract first.
6. Tap **Commit changes**.

## Step 3 — Create the Render blueprint (3 min)

1. Go to **render.com**, sign up with your **GitHub** account (simplest — no card needed).
2. Tap **New +** → **Blueprint**.
3. Connect your `semidash` GitHub repo when prompted.
4. Render reads `render.yaml` and shows two things it will create:
   a **web service** (semidash) and a **Postgres database** (semidash-db). Approve it.

## Step 4 — Add your key and deploy (2 min)

1. During setup Render asks for the value of **FINNHUB_KEY** (marked "sync: false").
   Paste the key from Step 1.
2. Tap **Apply** / **Create**. Render installs everything and starts the app.
3. When the build finishes, Render shows a URL like
   **https://semidash.onrender.com** — tap it. That's your live dashboard.

---

## What to expect

- **First load after idle is slow.** The free tier sleeps when unused; the first
  request wakes it and takes ~1 minute. After that it's snappy.
- **Data persists** now (Postgres), so read/greyed-out tiles survive restarts.
- **Refresh timing:** it fetches on startup and at 08:00 / 13:00 UK. Because the free
  tier sleeps, there's also a safety net: opening the dashboard after ~3h of staleness
  triggers a fresh pull automatically. So just open it in the morning and it updates.
- **Bookmark the URL** on your iPad home screen (Share → Add to Home Screen) and it
  behaves like an app.

## Keeping it awake (optional)

If you want the 08:00 / 13:00 jobs to fire even when you're not looking, use a free
uptime pinger (e.g. a cron-ping service) to hit your Render URL every 10–14 minutes.
This keeps the app from sleeping. Not required — the wake-refresh covers normal use.

## Free Postgres note

Render's free Postgres lasts 30 days, then you create a fresh one (a couple of clicks)
and update the DATABASE_URL link. Your app keeps working; only stored history resets.
For always-on with permanent storage, Render's paid tiers remove sleep and expiry.
