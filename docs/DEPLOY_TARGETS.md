# Deploy targets — which URLs this repo owns

## The collision this fixes

`vessel-ops-494701.web.app` is the GCP project's **default** Firebase Hosting
site. This repo used to publish there on every push to `main`, and so did
another branch of the project (an event-medicine variant — "Griztronics"). Two
apps, one URL: whichever built last silently replaced the other, with no error
on either side.

The tell was subtle. The two share ancestry, so the variant still renders this
repo's offline banner verbatim
(`frontend/src/components/ui/OfflineBanner.tsx:60`, including the word "Hub",
which is event language left over in this codebase). It looked like a broken
version of this app rather than a different app.

## What this repo deploys now

| Thing | Target | Set in |
|---|---|---|
| Frontend | Hosting site **`vessel-ops-ai`** → `https://vessel-ops-ai.web.app` | `frontend/firebase.json` → `hosting.site` |
| Backend | Cloud Run service **`sail-pal`** (unchanged) | `cloudbuild.yaml` → `_RUN_SERVICE` |

The default site `vessel-ops-494701.web.app` is no longer touched by this
repo's builds. Whatever is there stays there.

The Hosting site is created automatically on first deploy
(`firebase hosting:sites:create`, allowed to fail if it already exists). To do
it by hand:

```bash
firebase hosting:sites:create vessel-ops-ai --project vessel-ops-494701
```

Renaming it is a one-line edit to `hosting.site` — the build reads the name
from `firebase.json` rather than hardcoding it in the pipeline.

## The backend is still shared

`_RUN_SERVICE` deliberately still points at the existing `sail-pal` service, so
nothing moved unexpectedly. That means **both apps still share one backend and
one database** if the other branch is still deployed.

For a fully isolated stack, set `_RUN_SERVICE` to a new name on the Cloud Build
trigger. A new service is created on the next build and the frontend picks up
its URL automatically (the pipeline reads the live URL back before building).
The hosted database is ephemeral `/tmp` SQLite today, so there is nothing to
migrate — but if `USE_FIRESTORE=true` is on by then, the new service reads the
same Firestore data unless you change `FIREBASE_PROJECT_ID` too.

## If the other app needs its old backend

Pushes to `main` from this repo have already deployed this codebase's image to
`sail-pal`. If the variant needs the revision it was on:

```bash
gcloud run revisions list --service=sail-pal --region=us-west1
gcloud run services update-traffic sail-pal --region=us-west1 \
  --to-revisions=<older-revision>=100
```

Then move this repo to its own `_RUN_SERVICE` so the two stop trading places.

## Removed: Hosting → Cloud Run rewrites

`firebase.json` used to rewrite `/crew`, `/health`, `/components`,
`/maintenance`, `/ai`, `/sync`, `/setup/**` and `/healthz` to Cloud Run. Those
are gone, for two reasons:

1. **They were unused.** The frontend calls the backend at the absolute Cloud
   Run URL baked in as `NEXT_PUBLIC_API_BASE` at build time, never at a
   same-origin path.
2. **They shadowed real pages.** `/crew`, `/health` and `/maintenance` are app
   routes. Loading or refreshing one directly was forwarded to Cloud Run, which
   serves those endpoints under `/api/...` and so returned 404. Only in-app
   client-side navigation worked.

What remains is the SPA catch-all, which is what a static export needs.
