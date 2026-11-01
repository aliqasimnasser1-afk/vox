# Vox

A small X-style social app: sign up, post (280 chars), like, live timeline, profiles.

**Stack:** React + Vite (frontend, GitHub Pages) · Supabase (Postgres, Auth, Realtime, RLS).

## Run locally

```bash
npm install
npm run dev
```

## Database

`supabase/schema.sql` creates `profiles`, `posts`, `likes`, `follows`, their RLS policies,
a trigger that creates a profile on sign-up, and enables realtime. It has already been applied
to the project configured in `src/lib/supabase.js`. To use your own project, run the file in the
Supabase SQL editor and replace the URL and publishable key in that file.

The publishable key is safe in the browser because RLS enforces access.
**Never** put the secret / `service_role` key in this repo.

## Deploy to GitHub Pages

1. Push to a GitHub repo, branch `main`.
2. Settings → Pages → Source: **GitHub Actions**.
3. The workflow in `.github/workflows/deploy.yml` builds and publishes on every push.
4. In Supabase → Authentication → URL Configuration, add your Pages URL to **Site URL**
   (needed for email confirmation links).

## Roadmap

`follows` table already exists. Next: follow button and "following" timeline, replies,
hashtags and search, notifications, images (Supabase Storage), pagination.
