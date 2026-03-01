# Auth Production Checklist

## 1) Vercel Environment Variables
Set these in Vercel for the production environment:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `NEXT_PUBLIC_SITE_URL=https://<your-production-domain>`

Rules:

- `NEXT_PUBLIC_SITE_URL` must be the stable production origin.
- Do not set `NEXT_PUBLIC_SITE_URL` to `localhost`, `127.0.0.1`, or preview URLs in production.

## 2) Supabase Authentication URL Configuration
In Supabase Dashboard > Authentication > URL Configuration:

- Site URL: `https://<your-production-domain>`
- Redirect URLs:
  - `https://<your-production-domain>/auth/callback`

## 3) Supabase Providers
In Supabase Dashboard > Authentication > Providers:

- Google: Enabled
- Email: Enabled

If Google is disabled, OAuth login will be blocked by UI and callback normalization.
If Email is disabled, OTP login will be blocked by UI.

## 4) Callback Validation Behavior (Implemented)
- Only internal `next` paths are accepted (`/something`).
- `//...` or external redirects are rejected and fallback to `/dashboard`.
- Callback failures are normalized to:
  - `oauth_provider_disabled`
  - `invalid_callback`
  - `auth_failed`

## 5) CSP Note (Important)
Do not loosen CSP to allow `localhost:*` in production for this issue.

Reason:

- This auth incident is caused by redirect URL mismatch/configuration drift, not by CSP.
- DevTools-related requests like `/.well-known/appspecific/com.chrome.devtools.json` are not the root cause of OAuth callback misrouting.
