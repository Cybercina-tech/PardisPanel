# MrExchange Panel – Frontend

Vue 3 SPA with Vite.

## Structure

```
src/
├── assets/           # Global styles (main.css)
├── components/
│   ├── layout/       # Layout (Sidebar, Header, Drawer, Footer)
│   └── ui/           # Reusable UI components
├── layouts/          # App layout wrapper
├── router/           # Vue Router config
├── services/         # API client
├── stores/           # Pinia stores (auth, theme, siteSettings)
└── views/            # Route views by feature
    ├── auth/         # Login, Landing
    ├── dashboard/
    ├── prices/
    ├── special-prices/
    ├── categories/
    ├── finalize/
    ├── settings/
    ├── analysis/
    ├── telegram/
    └── templates/
```

## Scripts

- `npm run dev` – Dev server
- `npm run build` – Production build → `../static/vue/`
