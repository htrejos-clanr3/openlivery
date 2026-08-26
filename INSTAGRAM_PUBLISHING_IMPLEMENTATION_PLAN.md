# Instagram Publishing — Implementation Plan

**Branch:** `instagram-publishing`  
**Fork:** OpenLivery (htrejos-clanr3)  
**Date:** 2026-08-25  
**Scope:** Content publishing (image / carousel / Reel). **Instagram Messaging / DM is out of MVP** (`PHASE_FUTURE_INSTAGRAM_MESSAGING`).

---

## 1. Arquitectura actual

| Capa | Stack | Notas |
|------|--------|--------|
| API | FastAPI + SQLAlchemy 2 + Alembic + Postgres | `apps/api` |
| Web | Next.js 16 App Router + React 19 | `apps/web` |
| WhatsApp | Baileys bridge + WhatsApp Cloud (Meta Graph) | Canal nativo por cliente |
| Multi-tenant | `Agency → Client → Channels / Agents` | Aislamiento por `agency_id` |
| Auth | JWT cookie agency + portal | Sin RBAC fino |
| Secretos | Fernet (`encrypt_secret` / `decrypt_secret`) | Tokens Meta cifrados |
| Medios | Postgres `LargeBinary` (logos, slides, PDFs) | **No S3/CDN** hoy |
| Jobs | **Ninguno** | Schedule de carousels solo marca `status=scheduled` |
| IA | OpenAI/Anthropic agency keys + `carousels.generate_carousel_content` | Brand DNA en `Client` |

Dominio existente relevante:

- `WhatsAppCloudChannel` — OAuth Embedded Signup, health, tokens cifrados.
- `Carousel` / `CarouselSlide` / `CarouselEvent` — flujo editorial agency→portal con `ig_media_id` y schedule stub (“Instagram publishing pending”).
- Canales UI: WhatsApp live; Instagram/Facebook/Webchat = “Coming soon”.

---

## 2. Componentes reutilizables

| Componente | Reutilizar para |
|------------|-----------------|
| `whatsapp_cloud` router + UX (`wa-*` CSS) | Página Connect Instagram / advanced / health |
| `whatsapp_meta_signup` (state HMAC, code exchange) | OAuth Instagram vía Facebook Login |
| `encrypt_secret` | Page/IG access tokens |
| `FileDropzone` / `useFileDrop` | Upload de medios |
| `Client.brand_*` + `general_context` | Tono de marca para IA |
| `services/carousels.py` (JSON slides + caption) | Base de `SocialContentGenerationService` |
| `humanize_whatsapp_error` patrón | `instagram_errors.humanize` |
| `META_APP_ID` / `META_APP_SECRET` / `META_GRAPH_BASE_URL` | Misma Meta App de plataforma |
| Tests `authenticated_client` + `test_whatsapp_cloud` | Aislamiento tenant / mock Graph |

**No duplicar:** editor de agentes, inbox, nuevo LLM provider, nuevo storage S3 si no hace falta, app paralela.

**Relación con Carousels existentes:** flujo de **aprobación agency/portal** en `/carousels`. Bridge implementado: carrusel `approved` → `ContentItem` + `Publication` vía `carousel_publish_bridge` (`POST /carousels/{id}/publish` o `/schedule`). Escribe `ig_media_id` / status de vuelta en `carousels`.

---

## 3. Integraciones Meta existentes

- Graph base: `META_GRAPH_BASE_URL` (default `v23.0`).
- WhatsApp: Embedded Signup (`META_WHATSAPP_CONFIG_ID`), webhooks firmados, BYO o managed.
- `META_MOCK_MODE` para onboarding WhatsApp sin Meta real.
- **No hay** Instagram Login, IG User ID, ni Content Publishing hoy.

---

## 4. Documentación oficial Meta (vigente consultada)

Fuentes: [Content Publishing](https://developers.facebook.com/docs/instagram-platform/content-publishing), [IG User Media](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/media/), [content_publishing_limit](https://developers.facebook.com/docs/instagram-platform/instagram-graph-api/reference/ig-user/content_publishing_limit/), [Resumable uploads](https://developers.facebook.com/docs/instagram-platform/content-publishing/resumable-uploads/).

### Flujo de publicación (oficial)

```text
POST /{ig-user-id}/media          → creation_id (container)
GET  /{container-id}?fields=status_code  → EXPIRED | ERROR | FINISHED | IN_PROGRESS | PUBLISHED
POST /{ig-user-id}/media_publish?creation_id={container} → published media id
```

### Tipos

| Tipo | Contenedor | Notas |
|------|------------|--------|
| Imagen | `image_url` (+ caption opcional) | URL **pública** (Meta hace cURL) |
| Carrusel | Hijos `is_carousel_item=true` → padre `media_type=CAROUSEL` + `children` | Hasta **10** items (imagen/video mix). Reels **no** como hijo. |
| Reel | `media_type=REELS` + `video_url` o `upload_type=resumable` | Polling obligatorio |

### Permisos (Facebook Login / Instagram API with Facebook Login)

Típico para publicar:

- `instagram_basic` / o `instagram_business_basic`
- `instagram_content_publish` / o `instagram_business_content_publish`
- `pages_show_list`, `pages_read_engagement`

(App Review en producción. Desarrollo: roles en la app.)

### Límites (seguir `content_publishing_limit`, no hardcodear)

- Endpoint: `GET /{ig-user-id}/content_publishing_limit?fields=quota_usage,config`
- Docs actuales muestran `quota_total` ≈ **50** / `quota_duration` **86400** (algunas páginas mencionan 100; **fuente de verdad = respuesta `config`**).
- Contenedores: caducan ~24h; tope de creación de contenedores en ventana rodante (doc Media).
- Carrusel cuenta como **1** publicación.

### Diferencias vs prompt del producto

| Prompt | Docs / decisión |
|--------|------------------|
| Límite fijo inventado | Usar `content_publishing_limit` + UI “Usadas X / Y” solo con datos oficiales |
| Media sin URL pública | Obligatorio `image_url`/`video_url` o resumable; OpenLivery hoy guarda blobs → **URL firmada pública** en `BACKEND_URL` |
| QR Instagram | No existe en Content Publishing oficial |
| MCP DevTools para publicar | **No**; solo Graph API |

---

## 5. Modelo de datos propuesto

### `instagram_channels` (cuenta por cliente)

Campos: `id`, `agency_id`, `client_id` (unique), `instagram_user_id`, `page_id`, `username`, `display_name`, `encrypted_access_token`, `token_expires_at`, `granted_scopes` (JSON), `status`, `connection_mode` (`oauth`\|`manual`\|`mock`), `last_error`, `is_enabled`, timestamps.

### Editorial reutilizable (no solo `InstagramPost`)

```text
content_items     → pieza editorial del cliente
media_assets      → blob + metadatos
content_media     → content_id + media_id + position
publications      → intento de publicar en un canal/provider
```

**content_items:** `content_type` (`IMAGE`\|`CAROUSEL`\|`REEL`), `status` editorial (`DRAFT`\|`READY`\|`SCHEDULED`\|`PUBLISHED`\|`FAILED`\|`ARCHIVED`), `title`, `caption`, `hashtags`, `cta`, `timezone`, `created_by_user_id`, opcional `ai_meta` JSON.

**publications:** `channel` (`instagram`), `provider_account_id`, `status` (`DRAFT`\|`QUEUED`\|`PROCESSING`\|`PUBLISHED`\|`FAILED`\|`CANCELLED`), `scheduled_at`, `published_at`, `timezone`, `provider_publication_id`, `provider_container_id`, `idempotency_key`, `error_code`, `error_message`, `error_class` (`TRANSIENT`\|`PERMANENT`\|`AUTH`\|`VALIDATION`\|`RATE_LIMIT`), `locked_at`, `attempt_count`.

**media_assets:** bytes en DB + `mime_type`, `file_name`, `file_size`, `width`/`height`/`duration` opcionales.

### Futuro messaging

Sin tablas de DM. El `instagram_channels` queda listo para un `instagram_messaging` posterior.

---

## 6. Almacenamiento de medios

- Persistir en `media_assets.file_data` (patrón existente).
- Exponer `GET /api/public/media-assets/{id}?exp=&sig=` firmado HMAC (sin cookie) para que Meta descargue.
- URL absoluta: `{BACKEND_URL}/api/public/...` (debe ser alcanzable por Meta; en local usar tunnel o mock).
- Validación previa: MIME, tamaño, count carrusel 2–10, duración Reel (config).

---

## 7. Scheduler

No existe Quartz/Celery. **Introducir un único worker ligero** en lifespan FastAPI:

- Poll cada N segundos publicaciones `QUEUED` con `scheduled_at <= now()`.
- `SELECT … FOR UPDATE SKIP LOCKED` (o transición atómica `QUEUED → PROCESSING` con `locked_at`).
- Idempotencia: `idempotency_key` único + no republicar si ya hay `provider_publication_id`.
- Reintentos solo `TRANSIENT` / `RATE_LIMIT` con backoff; no retry infinito en `AUTH` / `VALIDATION`.

---

## 8. Capacidades de IA existentes

- Reutilizar `resolve_provider_credentials` + chat completion / patrón `carousels.py`.
- Nuevo `SocialContentGenerationService`: caption + hashtags + CTA + slides estructurados JSON.
- **No** auto-publicar. **No** generación de imágenes en MVP (solo `visualSuggestion` / `imagePrompt`).
- Interfaz futura: `MediaGenerationProvider` (stub).

---

## 9. Cambios necesarios (resumen)

### Backend

1. Migración `0020_instagram_publishing`.
2. Models + schemas.
3. `InstagramGraphProvider` + mock.
4. OAuth Facebook Login → Pages → `instagram_business_account`.
5. Content CRUD, media upload, publish/schedule, health, publishing limit.
6. Public signed media.
7. Scheduler loop.
8. Error humanization.
9. Tests.

### Frontend

1. `/clients/[id]/channels/instagram` — connect + dashboard.
2. Crear publicación (IMAGE / CAROUSEL / REEL).
3. Biblioteca básica, borradores, programadas, publicadas.
4. Activar Instagram en `/channels` y tab cliente.
5. i18n EN/ES.

### Docs

- `docs/instagram-publishing.md`
- README snippet operativo
- Env: `INSTAGRAM_PUBLISHING_MOCK_MODE`, poll settings, scopes.

---

## 10. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| `BACKEND_URL` no público → Meta no baja media | Mock mode local; docs tunnel/ngrok; validar URL en health |
| App Review / permisos | UI “parcialmente conectado” + reconnect; mock |
| Doble publicación | Lock + idempotency_key + status machine |
| Confusión Carousel vs ContentItem | Plan: bridge posterior; MVP UI Instagram usa ContentItem |
| Tokens Page vs User | Guardar token de Page con IG Business Account |
| Límite 50 vs 100 en docs | Leer `config.quota_total` en runtime |

---

## 11. Dependencias externas

- Meta App con productos Instagram + Facebook Login.
- Cuentas Instagram **Professional** (Business/Creator) vinculadas a Facebook Page.
- HTTPS público para OAuth redirect y media URL en producción.
- Agency OpenAI/Anthropic key para IA.

---

## 12. Plan por fases

| Fase | Entrega | Estado |
|------|---------|--------|
| 1 | Auditoría + este plan | Done |
| 2 | Conexión Instagram (OAuth + BYO advanced + mock + health) | Done |
| 3 | Modelo editorial Content / Media / Publication | Done |
| 4 | Publicar imagen E2E (+ mock) | Done |
| 5 | Carrusel (containers hijos + padre) | Done |
| 6 | Reels (si API + tipo de cuenta lo permiten) | Done (path + mock; real needs public video URL) |
| 7 | Borradores, schedule, idempotencia, retries | Done |
| 8 | IA caption + carrusel estructurado | Done |
| 9 | Biblioteca / historial / límite API card | Done (basic library + stats + limit card) |
| 10 | Docs, tests, lint/build | Done |
| **FUTURE** | `PHASE_FUTURE_INSTAGRAM_MESSAGING` (DM, Inbox, agent) | Deferred |

---

## 13. Criterios MVP (checklist)

- [ ] Conectar cuenta IG al cliente correcto
- [ ] Subir medios / biblioteca
- [ ] Borrador, publicar imagen, carrusel, Reel (mock + real path)
- [ ] Programar sin duplicados
- [ ] Errores humanizados; tokens no expuestos
- [ ] IA caption + estructura carrusel editable; publish humano
- [ ] Aislamiento tenant; mock mode; tests + build

---

## 14. PHASE_FUTURE_INSTAGRAM_MESSAGING

No implementar ahora. Cuando se aborde: webhooks messaging, conversaciones en Inbox, agent assignment, human takeover — reutilizando `Conversation` / Inbox, **sin** mezclar con Content Publishing.
