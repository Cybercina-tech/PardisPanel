# SmartExchange Panel — Restructure Proposal & Status

## Current State (discovery)

- **Backend:** Django project `SarafiPardis` with apps at repo root. Shared utilities in top-level `core/` (dates, formatting, sorting).
- **Frontend:** No Vue 3. UI is Django templates + Tailwind + vanilla JS. Phase 2 (Vue restructuring) is **not applicable** until a Vue app is added.

---

## Proposed Backend Folder Tree (approved for execution)

```
PardisPanel/
├── SarafiPardis/              # Django project
│   ├── settings.py
│   ├── urls.py
│   ├── views.py
│   └── middleware.py
├── core/                       # Shared utilities (backend “core” — single source of truth)
│   ├── dates.py
│   ├── formatting.py
│   └── sorting.py
├── accounts/                   # Custom User, Auth
├── analysis/                   # Statistics & Dashboard logic
│   ├── services.py             # NEW: analytics business logic
│   ├── views.py
│   └── serializers.py
├── category/                   # Category & PriceType models
├── change_price/               # Rate logic, PriceHistory
├── dashboard/
├── finalize/                   # Finalization + ExternalAPIService
│   └── services.py             # (existing)
├── instagram_banner/
│   └── services.py             # (existing)
├── landing/
├── price_publisher/
│   └── services/              # (existing package)
├── setting/                    # Logo, Favicon, Site config, Logs
├── special_price/
├── telegram_app/
│   └── services/              # (existing)
├── template_editor/
├── templates/
├── static/
└── ...
```

- **No app renames** (e.g. `category` → `categories`, `setting` → `system_settings`) to avoid migration and import churn; structure is already modular by feature.
- **Service layer:** Heavy logic moved from `views.py` to `services.py` (or existing `services/` package) per app. New: `analysis/services.py`.
- **Cleaning:** `core/` remains the single source for sorting/formatting/dates. Circular import in `analysis/views.py` (importing `sort_gbp_price_types` from `finalize.views`) fixed to use `core.sorting`. No removal of in-use templates; `.pyc`/`__pycache__` already gitignored.

---

## Phase 2 (Vue 3) — Deferred

When a Vue 3 app is added, use this structure under `frontend/src/`:

- `api/` — Axios/API modules
- `components/ui/`, `components/layout/`, `components/forms/`
- `views/` by feature (e.g. `views/auth/`, `views/dashboard/`, `views/categories/`)
- `stores/` — Pinia
- `assets/` — styles, images
- `composables/` — reusable logic

---

## Phase 3 — Done as part of execution

- All imports updated: `analysis` uses `core.sorting` (no `finalize.views`); `analysis` and `dashboard` use their own `services` modules.
- No config changes required for directory layout (paths unchanged).
- Dead code: removed the erroneous `finalize.views` import from `analysis/views.py`.
- **Service layer added:** `analysis/services.py` (analytics + pricing API logic), `dashboard/services.py` (home + dashboard2 context). Existing: `finalize/services.py`, `instagram_banner/services.py`, `price_publisher/services/`, `telegram_app/services/`.
- **Note:** Running `manage.py check` requires project dependencies (e.g. `pytz`) to be installed; the restructure does not change `INSTALLED_APPS` or URL config.
