# Firestore + Firebase Auth setup

What the hosted deployment needs before vessel records actually persist. These
are console steps that require your Google account — the code is already wired.

**Why this exists:** Cloud Run runs with `--min-instances=0` and a
container-local `/tmp`, so the SQLite database is erased whenever the instance
goes idle, and `web_entrypoint.py` re-seeds MV Resolute demo data into the empty
file on the next cold start. Anything recorded from a phone was gone within the
hour. Firestore fixes that.

The desktop app is unaffected by all of this — it keeps SQLite on your laptop
and needs no account.

---

## 1. Provision Firestore

[Firebase Console](https://console.firebase.google.com) → your project →
**Build → Firestore Database → Create database**.

- Mode: **Native** (not Datastore)
- Location: **us-west1**, matching the Cloud Run region — cross-region reads add
  latency to every request
- Rules: start locked. The repo's `firestore.rules` denies all direct client
  access on purpose; the backend uses the Admin SDK, which bypasses rules, and
  enforces vessel membership itself in `backend/auth.py`.

Deploy the rules:

```bash
firebase deploy --only firestore:rules --project <project-id>
```

## 2. Let Cloud Run reach Firestore

The backend authenticates with the runtime service account, so it needs read and
write on Firestore:

```bash
PROJECT_ID=<project-id>
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/datastore.user"
```

Sharing a boat also looks users up by email, which needs the Admin SDK's auth
API:

```bash
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/firebaseauth.admin"
```

> If the Cloud Run service runs as a dedicated (non-default) service account,
> substitute that address in both commands.

## 3. Turn on sign-in methods

**Firebase Console → Build → Authentication → Get started**, then enable:

- **Google** — set the public-facing name to *Vessel Ops AI* and pick a support email
- **Email/Password** — for crew without a Google account

Under **Authentication → Settings → Authorized domains**, add the Firebase
Hosting domain (`<project>.web.app`) if it isn't already listed. Google sign-in
fails silently from unlisted domains.

## 4. Give the frontend its Firebase config

**Project settings → General → Your apps → Web app**. Copy the config values into
the Cloud Build trigger as substitution variables:

| Substitution | Firebase config field |
|---|---|
| `_FIREBASE_API_KEY` | `apiKey` |
| `_FIREBASE_AUTH_DOMAIN` | `authDomain` |
| `_FIREBASE_APP_ID` | `appId` |

`projectId` is taken from `$PROJECT_ID` automatically.

These are **not secrets** — Firebase web config is public by design; it names the
project, it does not grant access. Authorization is enforced server-side against
each vessel's membership.

> **Leave them empty and the hosted app builds with no sign-in**, which means
> every visitor shares one vessel. Fine for a public demo, wrong for real crew
> medical records. `AuthGate` decides purely on whether these values are present.

## 5. Deploy

Push to `main`. That deploys the code but leaves the app on its current
behaviour: `_USE_FIRESTORE` and `_REQUIRE_AUTH` default to `false` in
`cloudbuild.yaml`, so a deploy can never land on a half-provisioned project.

Once steps 1–4 are done, turn both on together — either as trigger substitutions,
or directly on the running service with no redeploy:

```bash
gcloud run services update sail-pal --region=us-west1 \
  --update-env-vars=USE_FIRESTORE=true,REQUIRE_AUTH=true
```

Turn them on **together**. Firestore without auth would leave real crew medical
records readable by anyone who finds the URL.

Verify:

```bash
curl -s https://<cloud-run-url>/api/crew        # expect 401
curl -s https://<cloud-run-url>/healthz         # expect 200
```

A 200 on `/api/crew` means auth did not engage — check `REQUIRE_AUTH=true`
reached the service. These flags are explicit and are *not* implied by
`CLOUD_MODE`.

---

## How the data is laid out

```
vessels/{vessel_id}
    name, imo_number, created_at
    members:     { "<uid>": "owner" | "editor" | "viewer" }
    member_uids: [ "<uid>", ... ]
  crew/{crew_id}
  components/{component_id}
  health_events/{event_id}
  maintenance_logs/{log_id}
```

Sub-collections rather than top-level collections keyed by `vessel_id`: a boat's
data lives in one subtree, so sharing, exporting, or deleting a vessel is one
operation instead of five fan-out queries.

`members` is a map for cheap role checks; `member_uids` duplicates its keys as an
array because Firestore can `array_contains` an array but cannot query map keys.
They are always written together — see `FirestoreStore._write_members`.

## Sharing a boat

| Role | Can |
|---|---|
| `owner` | Everything, including adding and removing members |
| `editor` | Read and write all records |
| `viewer` | Read only |

```
POST   /api/vessels/{vessel_id}/members     {"email": "chris@example.com", "role": "editor"}
GET    /api/vessels/{vessel_id}/members
DELETE /api/vessels/{vessel_id}/members/{uid}
```

The invitee must have signed in at least once — Firebase only has a uid for an
account that exists. The last owner cannot be removed, or the boat would become
unadministrable.

There is no UI for this yet; it is API-only yet fully tested
(`backend/tests/test_auth_membership.py`).

## Multiple boats

Clients send `X-Vessel-Id` to pick one. Without it the backend falls back to the
caller's first vessel, and mints an empty one on first sign-in so a new user
never lands on a 404. The frontend stores the active vessel in `localStorage`
(`getActiveVesselId` in `frontend/src/lib/api.ts`).

## What is *not* done

- **Desktop ↔ hosted sync.** The two stores are independent. `SyncQueue` and
  `/api/sync` are still the old stubs — nothing writes to the queue, and
  `sync_now` logs fields (`action`, `entity_type`) that don't exist on the model,
  so it would raise if the queue ever had rows. Records entered on the laptop do
  not appear in the hosted app or vice versa.
- **Membership UI.** Sharing works over the API only.
- **Firestore-side history/audit.** No record of who changed what.
