# Pardis Exchange Panel

Price operations for the Pardis exchange desk: staff update prices, a manager
finalizes them, the panel renders branded banners and publishes them to Telegram,
and pushes the GBP/USDT rates to the Pardis website.

Built on the SmartExchange architecture (Django + DRF backend, Vue 3 SPA), reduced
to the features Pardis uses. Deployment target: cPanel only — see
[docs/CPANEL_DEPLOY.md](docs/CPANEL_DEPLOY.md).

## Public contracts (do not change)
- `GET /prices/live-json/` — unauthenticated JSON feed read by other sites.
- Finalize pushes `GBP_BUY`, `GBP_SELL`, `USDT_BUY`, `USDT_SELL` to
  `EXTERNAL_API_URL` as `{currency, rate, api_key}` (`finalize/services.py`).

## Behaviour notes
- Lira (TRY) price types are never finalized, rendered, published or pushed.
- A special-price banner can be downloaded without publishing:
  `GET /api/finalize/special-price/<history_id>/banner/`.

## Layout
`backend/` Django project (`MrExchangePanel`), `frontend/` Vue SPA (built into
`backend/static/vue`), `docs/` deployment notes, `template_editor.readme` editor notes.

## Local development
```
cd backend && python -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python manage.py migrate && python manage.py runserver
cd ../frontend && npm ci && npm run dev
```
Tests: `python manage.py test`.
