# YouTube Shorts — design

Date: 2026-10-05  
Branch: `youtube-shorts` (from `main`)  
Status: validated — implement in **Phase 2** of Content Studio  
Parent direction: [`2026-10-05-content-studio-phased.md`](./2026-10-05-content-studio-phased.md)

## Goal

Video vertical as a **canonical content type** with YouTube as primary destination: brief + optional assets → BYO video generation → simple FFmpeg brand wrap → human approval → upload as **private** via Google OAuth owned by the platform.

Not a standalone “desk” parallel to LinkedIn copy tools. Fits Studio: create once → select networks → publish.

## Decisions

| Topic | Choice |
|---|---|
| Scope | Full pipeline (generate + wrap + upload), not upload-only |
| Video generation | BYO fal / Replicate (agency or client API key); mock mode for local/tests |
| User input | Brief (objective, tone, duration) + optional logo/product assets |
| Audio | No TTS in MVP; silence (stock music deferred) |
| Montage | Single Wan clip + optional logo intro/outro via local FFmpeg |
| Visibility | Always `private` until a compliance flag is enabled |
| Legal | Reuse gates B (pre-connect) and F (human publish approval) |
| Not in MVP | Multi-scene editor, ElevenLabs, Creatomate, n8n embed, public uploads, AI budget hard-caps |

## Architecture

```
UI compose → quote → generate job → wrap job → preview → approve → YouTube videos.insert (private)
                ↑                         ↑
         fal/Replicate BYO          FFmpeg local
```

- Platform Google Cloud OAuth app; user consents per client channel.
- Tokens encrypted per tenant (same pattern as LinkedIn / Instagram).
- Async job statuses polled by the UI (same spirit as Instagram scheduled pubs).

## Data model

### `youtube_channels`

Per client: `status`, YouTube `channel_id`, encrypted tokens, scopes, `connection_mode` (`oauth` | `mock`), `last_error`, timestamps.

### `youtube_shorts`

Per Short job/draft:

- Brief fields + asset refs  
- Script/caption  
- `provider`: `fal` | `replicate` | `mock`  
- `status`: `draft` → `quoting` → `generating` → `wrapping` → `ready` → `publishing` → `published` | `failed`  
- Media paths, `privacy_status` (default `private`), `provider_video_id`  
- Estimated / actual cost fields  

Migration: `0037_youtube_shorts` (after `0036_legal_acceptances`).

## Config

| Setting | Role |
|---|---|
| `GOOGLE_OAUTH_CLIENT_ID` / `SECRET` | Platform OAuth (YouTube Data API) |
| `YOUTUBE_MOCK_MODE` | Local/tests without Google |
| `YOUTUBE_FORCE_PRIVATE` | Default `true`; blocks public until compliance |

fal / Replicate keys: BYO via existing provider credential storage — not a shared global operator key.

## API (`/api/youtube`)

**Channel**

- `GET/PUT /channels/{client_id}`
- `POST /channels/{client_id}/oauth/session` (channel-connect consent)
- `POST /channels/{client_id}/oauth/complete`
- `POST /channels/{client_id}/disconnect`
- `GET /channels/{client_id}/health`

**Shorts**

- `POST /channels/{client_id}/shorts` — create from brief + assets  
- `POST /shorts/{id}/quote`  
- `POST /shorts/{id}/generate`  
- `GET /shorts/{id}`  
- `POST /shorts/{id}/publish` — requires `human_approved` + `reviewed_exact_content`; forces `private`

## UI

- Card on `/channels` (alongside Instagram / LinkedIn)
- `/clients/[id]/channels/youtube` — connect, health, guide, compose
- Compose: brief, assets, provider select, quote → generate → preview → gate F → publish
- Persistent banner: uploads remain private until compliance audit
- i18n: `dicts/youtube.ts` + channel strings in `dicts/channels.ts`

## Testing

- Mock OAuth connect / disconnect  
- Mock generate → wrap → `ready`  
- Publish rejected without human approval  
- Publish always `private` when `YOUTUBE_FORCE_PRIVATE`  
- Tenant isolation  
- Legal consent reused from existing gates  

## Implementation order

1. Migration + models + schemas  
2. OAuth + channel health (mock first)  
3. Shorts CRUD + quote + mock generate  
4. FFmpeg wrap (logo optional)  
5. Publish private + legal gate F  
6. fal / Replicate BYO adapters  
7. Channels card + channel page UI + i18n  
8. Tests + docs env examples  

## Residual risks

- YouTube API compliance audit required before public uploads or scale  
- Quota costs are on the Google Cloud project; BYO video cost is on the client key  
- FFmpeg must be available in the API container/image  
- Wan job latency/timeouts need long-running job handling  

## References

- `docs/plans/transparent-platform-connections-legal.md`  
- `docs/plans/ai-generation-tiers-and-budgets.md`  
- `docs/plans/Guia_Shorts_Automaticos_n8n.pdf` (inspiration only; not embedded)
