# Deploying the Pardis panel on cPanel

cPanel (Passenger) is the only supported target. There is no Docker, Redis, Celery
worker, Node server or headless browser: tasks run in-process, the cache is
file-based, SQLite is the database, and the Vue app ships prebuilt in
`backend/static/vue`.

## 1. Create the app
cPanel → **Setup Python App**: Python **3.12**, application root `backend`
(upload the repo's `backend/` directory there), application URL = the panel domain,
startup file `passenger_wsgi.py`, entry point `application`.

Open the virtualenv shell cPanel shows and run:

```
pip install -r requirements.txt
```

## 2. Environment variables (cPanel UI, never committed)
| Variable | Value |
|---|---|
| `DJANGO_SECRET_KEY` | long random string. **Keep it forever**: Telegram bot tokens are encrypted with a key derived from it; changing it makes stored tokens unreadable. |
| `DJANGO_DEBUG` | `False` |
| `DJANGO_ALLOWED_HOSTS` | `panel.sarafipardis.co.uk,www.panel.sarafipardis.co.uk` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://panel.sarafipardis.co.uk` |
| `EXTERNAL_API_KEY` | key for the sarafipardis.co.uk rates API (`EXTERNAL_API_URL` defaults to `https://sarafipardis.co.uk/wp-json/pardis/v1/rates`) |
| `SQLITE_PATH` | optional, absolute path of the database file (default `backend/db.sqlite3`) |

## 3. First install: bring the Pardis data over
Upload the Pardis `db.sqlite3` and `public/media/` to a private directory **outside**
the web root, then, in the virtualenv shell:

```
python manage.py migrate
python manage.py import_pardis /home/USER/private/db.sqlite3 --dry-run   # verify first
python manage.py import_pardis /home/USER/private/db.sqlite3 --media-from /home/USER/private/media
python manage.py collectstatic --noinput
python manage.py ensure_default_admin   # only if you need a fresh admin
```

The source database is opened read-only and is never modified. The importer refuses
to run twice. All users keep their passwords; everyone signs in again once
(sessions are not carried over).

Verify the public feed is byte-identical to the old panel:
`curl -s https://panel.sarafipardis.co.uk/prices/live-json/` must equal the output
saved from the old panel before cut-over.

## 4. Operations
- Restart after a deploy: **Restart** in Setup Python App (or `touch tmp/restart.txt`).
- Logs: `backend/logs/app.json.log` and the Passenger error log.
- Publishing to Telegram is outbound only; there is no long-running bot process.
- Back up `db.sqlite3` and `public/media/` before every deploy.
