# WhatsApp UX Improvement Plan

## Estado actual

La pantalla `/clients/[id]/channels/whatsapp-cloud` exige configuración técnica BYO Meta:

- Agente asignado
- Phone Number ID
- WABA ID (opcional)
- Access Token permanente
- App Secret

Acciones: **Guardar credenciales** + **Conectar y verificar**.

No hay Embedded Signup, OAuth Meta ni health check dedicado. El “health check” es `POST .../connect` (Graph `GET /{phone_number_id}`).

## Arquitectura detectada

```
Agency → Client (1:1 WhatsAppCloudChannel) → Agent
                ↓
         Conversations (channel=whatsapp_cloud)
                ↓
         Inbox / Portal (mode ai|human)
```

| Capa | Stack |
|------|--------|
| Frontend | Next.js 16 App Router — `apps/web` |
| Backend | FastAPI — `apps/api` |
| DB | PostgreSQL + Alembic |
| Meta | Graph API `META_GRAPH_BASE_URL` (default v23.0) |
| QR paralelo | Baileys en `apps/whatsapp` (no tocar) |

**Modelo conceptual a conservar:** Cliente → Canal WhatsApp Cloud → Agente → Conversaciones → Inbox.

## Archivos involucrados

### Backend
- `apps/api/app/models.py` — `WhatsAppCloudChannel`
- `apps/api/app/routers/whatsapp_cloud.py` — CRUD / connect / disconnect / health / signup
- `apps/api/app/routers/whatsapp_cloud_webhook.py` — GET verify + POST inbound
- `apps/api/app/services/whatsapp_cloud.py` — Graph client
- `apps/api/app/services/whatsapp_cloud_health.py` — health diagnostics
- `apps/api/app/services/whatsapp_meta_signup.py` — OAuth state, Embedded Signup, mock
- `apps/api/app/services/whatsapp_errors.py` — humanize Meta errors
- `apps/api/app/services/whatsapp_inbound.py` — pipeline inbound + handoff
- `apps/api/app/services/whatsapp.py` — outbound unificado
- `apps/api/app/schemas_whatsapp_cloud.py`
- `apps/api/app/config.py` — Meta platform + mock settings
- `apps/api/app/security.py` — Fernet AES (`encrypt_secret` / `ENCRYPTION_KEY`)
- `apps/api/migrations/versions/0017_whatsapp_cloud_channel.py`
- `apps/api/migrations/versions/0018_whatsapp_ux_onboarding.py`
- `apps/api/tests/test_whatsapp_cloud.py`

### Frontend
- `apps/web/app/clients/[id]/channels/whatsapp-cloud/page.tsx`
- `apps/web/lib/i18n/dicts/clients.ts` (`whatsappCloud.*`)
- `apps/web/types/index.ts`
- `apps/web/app/globals.css` (estilos `.wa-*`)

### Docs
- `docs/whatsapp-meta-setup.md`
- este archivo

## Modelo de datos actual

Tabla `whatsapp_cloud_channels` (único por `client_id`):

| Campo | Notas |
|-------|--------|
| `agent_id` | Obligatorio |
| `status` | `disconnected` \| `connected` \| `error` |
| `connection_mode` | `manual` \| `managed` \| `embedded` (migración 0018) |
| `phone_number_id`, `waba_id` | Texto |
| `encrypted_access_token`, `encrypted_app_secret` | Fernet (`ENCRYPTION_KEY`) |
| `webhook_verify_token` | Plaintext (debe mostrarse al operador) |
| `phone_number`, `display_name` | Rellenados en connect / signup |
| `last_error`, `is_enabled`, `last_connected_at` | |

API **no** expone secretos; solo `has_access_token` / `has_app_secret`.

## Flujo WhatsApp actual

```
Config manual → PUT credentials → POST connect (Graph verify)
     ↓
Webhook URL: /api/public/whatsapp-cloud/channels/{channel_uuid}/webhook
     ↓
GET hub.verify_token / POST HMAC(app_secret | META_APP_SECRET)
     ↓
process_inbound → AI o human → send_text Graph
```

**Resolución de cliente:** por UUID del canal en la URL del webhook, **no** por `phone_number_id` del payload.

## Qué ya funciona (pre-cambio)

- Persistencia cifrada de token y app secret
- Connect/verify contra Graph
- Disconnect
- Webhook verification + inbound firmado
- Texto / imagen / audio inbound
- Auto-respuesta IA + handoff humano (Inbox/Portal)
- Coexistencia con canal QR Baileys
- Tests de webhook, connect, human mode
- Secretos no vuelven al frontend

## Qué faltaba (y se aborda)

- UX comercial (CTA Meta, estado, avanzada)
- Embedded Signup / OAuth Meta
- App Meta de plataforma (`META_APP_ID` / `META_APP_SECRET`)
- Health check dedicado (sin secretos)
- Traducción de errores Meta → mensajes humanos
- Reconexión / progreso de pasos
- Mock de Meta para desarrollo local
- Docs de setup Meta
- Asistente ligero post-conexión (enlace a configurar agente)

## Problemas de UX

1. Formulario técnico como experiencia principal → **resuelto** (avanzada)
2. App Secret pedido al cliente final → **solo en avanzada / BYO**
3. Errores Meta crudos → **humanize + Ver detalles**
4. Sin tarjeta de estado ni diagnóstico → **health + UI**
5. Sin feedback de progreso → **pasos desde backend**

## Por qué se pide App Secret hoy

El webhook POST valida `X-Hub-Signature-256` con el **App Secret de la Meta App** que firma los eventos. Cada canal BYO trae su propia Meta App → cada cliente pega su secret.

**Modo administrado:** OpenLivery usa `META_APP_SECRET` del servidor; el canal puede no guardar app secret propio. El webhook cae al secret de plataforma si el canal no tiene uno.

## Cambios propuestos → estado

| Fase | Objetivo | Estado |
|------|----------|--------|
| 1 Auditoría + plan | Este documento | ✅ |
| 2 UX | CTA / estado / avanzada | ✅ |
| 3 Health | `GET .../health` + `POST .../test` | ✅ |
| 4 Embedded Signup | session / complete / callback / mock / FB SDK | ✅ código; Meta real **BLOCKED** |
| 5 Secretos | Ya Fernet; fallback plataforma | ✅ |
| 6 Reconnect / disconnect | UI + endpoints existentes | ✅ |
| 7 Asistente agente | CTA post-conexión → página agente | ✅ mínimo |

## Riesgos

- Embedded Signup requiere Meta App + Config ID + redirect público + permisos
- Webhook multi-tenant por UUID: cambiar a phone_number_id exige índice único y migración cuidadosa (índice añadido; routing sigue por UUID)
- Mock mal cableado podría divergir del camino real (mismo path de persistencia)
- Imágenes Docker en ejecución pueden no incluir estos cambios hasta `make build`

## Dependencias Meta

| Recurso | Uso |
|---------|-----|
| Meta App + WhatsApp product | Obligatorio para Embedded Signup real |
| Embedded Signup Config ID | FB.login `config_id` |
| Graph API version | Centralizado en `META_GRAPH_BASE_URL` |
| Redirect / dominio | Callback OAuth |
| Webhook subscription | Manual en Meta (URL por canal) |

---

## Implementado

### UX
- Pantalla principal: **Conectar con Meta**, beneficios, agente, accordion **Configuración avanzada**
- Tarjeta de estado conectado: número, cuenta, agente, webhook, última actividad
- Probar conexión, Abrir Inbox, Desconectar, Reconectar
- Progress steps reales desde backend (mock/signup complete)
- CTA opcional “Configurar agente” tras conectar

### API
- `GET /api/whatsapp-cloud/signup/options`
- `POST /api/whatsapp-cloud/channels/{client_id}/signup/session`
- `POST /api/whatsapp-cloud/channels/{client_id}/signup/complete`
- `GET /api/whatsapp-cloud/oauth/callback`
- `GET /api/whatsapp-cloud/channels/{client_id}/health`
- `POST /api/whatsapp-cloud/channels/{client_id}/test`
- `PATCH /api/whatsapp-cloud/channels/{client_id}/agent`
- Webhook: secret de canal **o** `META_APP_SECRET`

### Seguridad / datos
- Migración `0018_whatsapp_ux_onboarding` (`connection_mode` + índice `phone_number_id`)
  - Revisa `0017_whatsapp_cloud_channel` (cadena limpia para `main`)
  - Si una DB local quedó en el stub WIP `0018_carousels_pomelli` / `0019_*`, hacer
    `alembic stamp 0018_whatsapp_ux_onboarding` (el schema `connection_mode` ya aplicado)
- State OAuth firmado + cifrado, TTL, binding agency/client/user
- Secretos no en health ni channel GET
- Mock Graph verify cuando `META_MOCK_MODE` / token mock

### Docs / env
- `docs/whatsapp-meta-setup.md`
- Variables documentadas en `.env.example` / `.env.docker.example`

### Tests (locales vs Postgres Docker)
```
tests/test_whatsapp_cloud.py — 14 passed
```
Incluye: health sin secretos, mock signup, state binding, platform secret webhook, humanize, aislamiento de agente, webhook/human mode existentes.

### Frontend validación
- `eslint` OK
- `tsc --noEmit` OK

## Pendiente

1. **Rebuild / migrate stack Docker** (imágenes actuales son GHCR y no montan código local):
   ```bash
   make build && make up && make migrate
   ```
2. Activar mock local (opcional) en `.env.docker`:
   ```bash
   META_MOCK_MODE=true
   META_APP_ID=dev-mock
   ```
3. Asistente NL completo (fase 7 ampliada): generar prompt/instrucciones con IA y preview antes de aplicar — solo CTA a `/agents/{id}` por ahora.
4. Suscripción automática de webhook vía Graph (hoy sigue manual con URL/verify token en UI).

## Configuración externa requerida — BLOCKED_BY_EXTERNAL_CONFIGURATION

Para Embedded Signup **real** (no mock):

| Requisito | Variable / acción |
|-----------|-------------------|
| Meta App ID | `META_APP_ID` |
| Meta App Secret | `META_APP_SECRET` |
| Embedded Signup Config ID | `META_WHATSAPP_CONFIG_ID` |
| Redirect URI pública | `{FRONTEND_URL}/api/whatsapp-cloud/oauth/callback` |
| Producto WhatsApp + permisos vigentes | Consola Meta |
| HTTPS público (prod / tunnel) | Webhook + OAuth |

Sin eso, la UI muestra mensaje de no disponible y abre **configuración avanzada**. El código no se marca como “probado en producción Meta”.

## Archivos creados

- `WHATSAPP_UX_IMPROVEMENT_PLAN.md` (este)
- `docs/whatsapp-meta-setup.md`
- `apps/api/migrations/versions/0018_whatsapp_ux_onboarding.py`
- `apps/api/app/services/whatsapp_cloud_health.py`
- `apps/api/app/services/whatsapp_meta_signup.py`
- `apps/api/app/services/whatsapp_errors.py`

## Archivos modificados (principales)

- `apps/api/app/routers/whatsapp_cloud.py`
- `apps/api/app/routers/whatsapp_cloud_webhook.py`
- `apps/api/app/services/whatsapp_cloud.py`
- `apps/api/app/models.py`
- `apps/api/app/config.py`
- `apps/api/app/schemas_whatsapp_cloud.py`
- `apps/api/tests/test_whatsapp_cloud.py`
- `apps/web/app/clients/[id]/channels/whatsapp-cloud/page.tsx`
- `apps/web/lib/i18n/dicts/clients.ts`
- `apps/web/types/index.ts`
- `apps/web/app/globals.css`
- `.env.example`, `.env.docker.example`

## Endpoints nuevos

| Método | Ruta |
|--------|------|
| GET | `/api/whatsapp-cloud/signup/options` |
| POST | `/api/whatsapp-cloud/channels/{client_id}/signup/session` |
| POST | `/api/whatsapp-cloud/channels/{client_id}/signup/complete` |
| GET | `/api/whatsapp-cloud/oauth/callback` |
| GET | `/api/whatsapp-cloud/channels/{client_id}/health` |
| POST | `/api/whatsapp-cloud/channels/{client_id}/test` |
| PATCH | `/api/whatsapp-cloud/channels/{client_id}/agent` |

## Migraciones

- `0018_whatsapp_ux_onboarding` — `connection_mode`, índice `phone_number_id`

## Variables de entorno nuevas

```bash
META_APP_ID=
META_APP_SECRET=
META_WHATSAPP_CONFIG_ID=
META_MOCK_MODE=false
META_OAUTH_REDIRECT_PATH=/api/whatsapp-cloud/oauth/callback
# existente:
META_GRAPH_BASE_URL=https://graph.facebook.com/v23.0
ENCRYPTION_KEY=   # ya cifraba tokens
```

## Cómo probar

1. Rebuild + migrate (ver Pendiente).
2. Mock: `META_MOCK_MODE=true` + `META_APP_ID=dev-mock` → Cliente → WhatsApp Cloud → **Conectar con Meta** → estado conectado + health.
3. Manual: Configuración avanzada → Phone ID / token / secret → Guardar y verificar (compatibilidad).
4. Tests: `make test` (tras rebuild api con pytest) o:
   ```bash
   TEST_DATABASE_URL=postgresql+psycopg://...@127.0.0.1:5432/openlivery_test \
     pytest apps/api/tests/test_whatsapp_cloud.py -q
   ```

## Cómo configurar Meta

Ver `docs/whatsapp-meta-setup.md`.

## Limitaciones

- Embedded Signup real no verificado end-to-end sin App Meta / Config ID / HTTPS.
- Mensajes humanizados del backend están en español (UI i18n cubre la mayoría de textos de pantalla).
- Webhook multi-cliente sigue por **channel UUID** en la URL (diseño existente).
- Fase 7 NL (generar instrucciones con preview) no implementada más allá del enlace al editor del agente.
- Rama de trabajo: `whatsapp-ux-onboarding` (no merge automático a `main`).
