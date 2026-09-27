# Demo frontend (optional)

Small Vite + React + TypeScript SPA that talks to the API. You can keep it or
delete `frontend/`. The backend does not depend on it.

## Routes

| Path | Access | Purpose |
|------|--------|---------|
| `/` | Public | Landing page with Sign in |
| `/callback` | Public (Cognito only) | Hosted UI return URL |
| `/app` | Protected | Dashboard with role-gated widgets |

Visits to `/app` without a token go back to `/`. The bearer token lives in
memory only, not `localStorage`. A hard reload of `/app` therefore signs you
out. That is on purpose.

## Local dev (offline auth)

1. Start the backend with `AUTH_ISSUER=local` and `DEBUG=True` (see root README).
2. Copy `.env.example` to `.env.local` and set `VITE_AUTH_MODE=dev`.
3. `npm ci && npm run dev` opens http://localhost:5173.
4. Choose a demo role on the landing page. Dashboard is at `/app`.

## Cognito

Set `VITE_AUTH_MODE=cognito` and the `VITE_COGNITO_*` values from your public
app client (authorization code + PKCE, no client secret in the browser). Set
`VITE_COGNITO_REDIRECT_URI` to your callback URL
(e.g. `http://localhost:5173/callback`).

## Changing the look

Edit branding and UI here. Leave `src/auth/*` and `src/api/*` alone.

| What | File(s) |
|------|---------|
| Brand name | `src/brand.ts` |
| Colours, spacing, type | `src/styles/theme.css` |
| Landing page | `src/pages/Landing.tsx` + `Landing.module.css` |
| Dashboard shell | `src/pages/app/AppShell.tsx` + `AppShell.module.css` |
| Widgets | `src/pages/app/widgets/` |

Styling is CSS Modules plus tokens in `theme.css`. No Tailwind.

## Scripts

- `npm run dev`: Vite dev server
- `npm run build`: typecheck + production bundle
- `npm run lint`: ESLint
- `npm run typecheck`: `tsc --noEmit`
- `npm test`: Vitest
