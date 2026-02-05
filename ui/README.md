# AceForge New UI

Ported from [fspecii/ace-step-ui](https://github.com/fspecii/ace-step-ui). Maintained in-tree; **no external dependency** on that repository.

- **Dev:** `npm run dev` — Vite dev server (port 3000) proxies `/api` and `/audio` to Flask (5056).
- **Build:** `npm run build` — Output in `dist/`; served by Flask at `/` in production.
