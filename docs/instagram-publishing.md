# Instagram Content Publishing (Fast Livery)

Publish images, carousels, and Reels from each client’s Instagram professional account. **Direct messages are not part of this feature** (see `PHASE_FUTURE_INSTAGRAM_MESSAGING` in `INSTAGRAM_PUBLISHING_IMPLEMENTATION_PLAN.md`).

## Requirements (Meta)

- Instagram **Professional** account (Business or Creator) linked to a Facebook Page.
- Meta App with Facebook Login + Instagram permissions (App Review for production).
- Typical scopes (Facebook Login path):

  - `pages_show_list`
  - `pages_read_engagement`
  - `instagram_basic`
  - `instagram_content_publish`

  Newer Instagram API product names (`instagram_business_basic`, `instagram_business_content_publish`) are also accepted when granted.

- Public `BACKEND_URL` so Meta can download media via signed URLs (`/api/public/media-assets/{id}?exp=&sig=`).

Official guides:

- [Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing)
- [IG User Media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/)
- [Publishing limit](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit/)

## Environment variables

| Variable | Purpose |
|----------|---------|
| `META_APP_ID` / `META_APP_SECRET` | Platform Meta App for OAuth |
| `META_GRAPH_BASE_URL` | Graph root (default `https://graph.facebook.com/v23.0`) |
| `FRONTEND_URL` | OAuth redirect origin |
| `BACKEND_URL` | Absolute URL Meta uses to fetch media |
| `INSTAGRAM_PUBLISHING_MOCK_MODE` | Simulate containers/publish without Meta |
| `INSTAGRAM_OAUTH_REDIRECT_PATH` | Default `/api/instagram/oauth/callback` |
| `INSTAGRAM_CONTAINER_POLL_MAX_ATTEMPTS` | Polling ceiling (default 30) |
| `INSTAGRAM_CONTAINER_POLL_DELAY_SECONDS` | Delay between polls (default 2) |
| `INSTAGRAM_SCHEDULER_INTERVAL_SECONDS` | Due-job poll interval (default 20) |

## How to connect

Every entry point (Channels hub → Configure Instagram, Client → Channels → Instagram, Carousel → Connect / open Instagram) lands on the same client Instagram page with:

1. **Connect actions** — Meta OAuth when `META_APP_ID` + `META_APP_SECRET` are set. If guided login is blocked, **Connect with Meta** stays visible but opens/scrolls the in-app guide (human-readable notice; the `BLOCKED_BY_EXTERNAL_CONFIGURATION` string is secondary).
2. **Step-by-step guide** (accordion, open by default when disconnected) — prerequisites, what to copy (IG user ID, Page ID, username, token), where those values appear in Meta, numbered BYO steps ending in Advanced setup → Save. Optional OAuth / mock sections; no Instagram QR.
3. **Advanced setup** — paste Instagram user ID, optional Page ID / username, and access token.

### Recommended path (BYO — always works)

1. Convert the client’s Instagram to **Professional** (Business or Creator).
2. Link it to a **Facebook Page** the client controls.
3. In [Meta for Developers](https://developers.facebook.com/apps/), create/open a Meta App and enable Instagram Content Publishing products / Facebook Login as needed.
4. Issue a **Page access token** with `instagram_basic` + `instagram_content_publish` (or `instagram_business_basic` / `instagram_business_content_publish`).
5. Copy the **Instagram user ID** (numeric IG Business Account id — not `@username`). Often: Graph `GET /{page-id}?fields=instagram_business_account`.
6. In Fast Livery → that client → Instagram → **Advanced setup**, paste ID + token (and optional Page ID / username) → **Save credentials**.
7. Status becomes **Connected**. Use **New publication** or publish an approved carousel to verify.

### Guided Meta login (optional)

Only when the Fast Livery server has `META_APP_ID` and `META_APP_SECRET`:

1. Click **Connect with Meta**.
2. Authorize permissions and choose the Page linked to the professional Instagram account.
3. Return to Fast Livery; status becomes Connected when account + publish permission are valid.

### Mock (local)

```bash
INSTAGRAM_PUBLISHING_MOCK_MODE=true
```

Use **Connect with mock account** to exercise the UI without Meta.

Tokens are stored encrypted. API responses expose `access_token_configured` only.

## Create & publish

1. **Nueva publicación** → type IMAGE / CAROUSEL / REEL.
2. Upload media (JPEG/PNG; MP4/MOV for video/Reel). Carrusel: 2–10 items, reorderable.
3. Caption / hashtags / CTA — optional **Generar con IA** (editable; never auto-publishes).
4. **Guardar borrador**, **Programar** (timezone required), or **Publicar ahora**.

Publishing flow (Graph):

```text
create media container(s) → wait status FINISHED → media_publish → store provider id
```

## Mock mode

```bash
INSTAGRAM_PUBLISHING_MOCK_MODE=true
```

Simulates container creation, processing, and publish IDs so the full UI works without a Meta account.

## Publishing limits

UI can show usage from `GET /{ig-user-id}/content_publishing_limit` when Meta returns `config.quota_total` / `quota_usage`. Do not hardcode the quota; docs have varied historically (often 50/24h).

## Troubleshooting

| Symptom | Check |
|---------|--------|
| OAuth blocked | `META_APP_ID` + `META_APP_SECRET` |
| Media rejected by Meta | `BACKEND_URL` must be publicly reachable |
| Partial connection | Missing `instagram_content_publish` — reconnect |
| Schedule never fires | API process must be running (in-process scheduler) |
| Tenant errors | Content/channel always scoped by `agency_id` + `client_id` |

## Related carousels product

`/carousels` is the agency↔portal **approval** workflow (Pomelli). When a carousel is **approved**:

1. Connect Instagram for that client.
2. Ensure each slide has an image (`with_images` or equivalent).
3. **Publish to Instagram now** (`POST /api/carousels/{id}/publish`) or **Schedule** (`POST /api/carousels/{id}/schedule`).

The bridge materializes a `ContentItem` (CAROUSEL) + `Publication`, reuses `InstagramPublishingService`, and writes back `ig_media_id` / status on the carousel.
