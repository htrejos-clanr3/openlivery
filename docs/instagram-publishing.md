# Instagram Content Publishing (OpenLivery)

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

1. Clients → client → **Instagram**.
2. Click **Connect with Meta** (or use mock when `INSTAGRAM_PUBLISHING_MOCK_MODE=true`).
3. Select / authorize a Page with a linked Instagram professional account.
4. Advanced settings allow BYO token + IG user id for diagnostics.

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
