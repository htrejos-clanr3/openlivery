# Instagram Content Publishing (Fast Livery)

Publish images, carousels, and Reels from each client’s Instagram professional account. **Direct messages are not part of this feature** (see `PHASE_FUTURE_INSTAGRAM_MESSAGING` in `INSTAGRAM_PUBLISHING_IMPLEMENTATION_PLAN.md`).

## Requirements (Meta)

- Instagram **Professional** account (Business or Creator) linked to a Facebook Page.
- Meta App with Facebook Login + Instagram permissions (App Review for production).
- Required scopes for the Facebook Login connection:

  - `pages_show_list`
  - `pages_read_engagement`
  - `instagram_basic`
  - `instagram_content_publish`

  The current dialog also requests `business_management`. The backend checks the permissions Meta granted before connecting the channel.

- A public HTTPS origin so Meta can fetch signed media URLs (`/api/public/media-assets/{id}?exp=&sig=`). The Docker Compose gateway serves them through `FRONTEND_URL` when `BACKEND_URL` is the internal `http://api:8000` service.

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
| `BACKEND_URL` | Public media origin for a separately hosted API. The internal Docker Compose URL falls back to `FRONTEND_URL`. |
| `INSTAGRAM_PUBLISHING_MOCK_MODE` | Simulate containers/publish without Meta |
| `INSTAGRAM_OAUTH_REDIRECT_PATH` | Default `/api/instagram/oauth/callback` |
| `INSTAGRAM_CONTAINER_POLL_MAX_ATTEMPTS` | Polling ceiling (default 30) |
| `INSTAGRAM_CONTAINER_POLL_DELAY_SECONDS` | Delay between polls (default 2) |
| `INSTAGRAM_SCHEDULER_INTERVAL_SECONDS` | Due-job poll interval (default 20) |

## How to connect

Open **Clients → your client → Channels → Instagram**. The **Connect with Meta** option uses the app configured by the Fast Livery administrator.

### Connect with Meta

1. Confirm that the client's Instagram account is a Business or Creator account linked to a Facebook Page you manage.
2. Click **Connect with Meta**, confirm your authorization, then sign in to Facebook. If Meta shows several Pages, authorize only the Page linked to this client's Instagram account.
3. Back in Fast Livery, verify the displayed `@username` and click **Check connection**. Confirm you can see a healthy connection before preparing a post.

### Configure the Meta app

Open **Set up the Meta app** in the connection guide to see the app's links, domain, callback URI, and requested permissions.

1. In **App settings → Basic**, add the public hostname to **App Domains** and check the privacy, terms and data-deletion URLs. Save and reload.
2. In **Facebook Login for Business → Settings**, enable **Client OAuth Login** and **Web OAuth Login**. Copy the exact callback URI into **Valid OAuth Redirect URIs**, then save and reload.
3. In **Use cases → Instagram → API setup with Facebook login**, click **Add required content permissions**. In **Permissions and features**, verify **Ready for testing** for the requested permissions. Include `pages_read_engagement` for Instagram publishing.
4. Test with an existing administrator or tester of the app who can access the real Page and Instagram account.

### Manual connection

An administrator with an authorized Facebook Page token can use **Advanced setup**. The token needs `instagram_basic`, `instagram_content_publish`, and `pages_read_engagement`. Look up the Instagram account ID using `GET /{page-id}?fields=instagram_business_account{id,username}`. Paste the Instagram account ID and token, add the Page ID and username if available, save, then click **Check connection**.

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
| OAuth unavailable | Ask the platform administrator to verify the Meta app configuration on the server |
| Domain or callback rejected | Check that the public domain and exact callback in Fast Livery are registered in Meta |
| `Invalid Scopes: pages_read_engagement` | Enable the permission in the Instagram use case and confirm it is ready for testing |
| Meta returned no eligible account | Check the Page–Instagram link and the Facebook account's access to both assets |
| Media rejected by Meta | The signed media URL must be reachable over public HTTPS |
| Partial connection | Missing `instagram_content_publish` — reconnect |
| Schedule never fires | API process must be running (in-process scheduler) |
| Tenant errors | Content/channel always scoped by `agency_id` + `client_id` |

## Related carousels product

`/carousels` is the agency↔portal **approval** workflow (Pomelli). When a carousel is **approved**:

1. Connect Instagram for that client.
2. Ensure each slide has an image (`with_images` or equivalent).
3. **Publish to Instagram now** (`POST /api/carousels/{id}/publish`) or **Schedule** (`POST /api/carousels/{id}/schedule`).

The bridge materializes a `ContentItem` (CAROUSEL) + `Publication`, reuses `InstagramPublishingService`, and writes back `ig_media_id` / status on the carousel.
