# Meta Developer Tools MCP — Implementation Plan

**Branch:** `meta-devtools-mcp`  
**Date:** 2026-08-25  
**Official product note:** Meta renamed this surface to **Meta Social Technologies MCP** (as of 2026-08-18). Endpoint and tool namespace remain DevTools-oriented (`https://mcp.facebook.com/devtools`, `devtools_*`). OpenLivery docs keep the familiar “Developer Tools MCP” name and mention the rename.

Official docs: [developers.facebook.com/documentation/mcp/devtools-mcp](https://developers.facebook.com/documentation/mcp/devtools-mcp) (page fetch timed out during planning; tool inventory cross-checked against Meta’s June 2026 announcement + secondary technical write-ups). **If Meta’s live docs differ, prefer the live docs.**

---

## 1. Arquitectura actual

| Pieza | Ubicación |
|-------|-----------|
| WhatsApp Cloud Graph | `services/whatsapp_cloud.py`, `whatsapp_meta_signup.py` |
| WhatsApp webhook | `routers/whatsapp_cloud_webhook.py` (verify + HMAC) |
| WhatsApp health | `services/whatsapp_cloud_health.py` |
| Instagram Graph publish | `services/instagram_graph.py`, `instagram_publishing.py` |
| Instagram health | inline in `routers/instagram.py` |
| Agent MCP client (reuse) | `services/tools/mcp_client.py` (Streamable HTTP / SSE) |
| Settings UI | `apps/web/app/settings/page.tsx` (agency + AI keys) |
| Cache / Redis | **No Redis** — in-memory + DB only |
| Auth | Agency cookie JWT; `User.role` exists but **not enforced** |
| Alembic head | `0021_carousel_instagram_bridge` |

Mensajería productiva **no** pasa por MCP.

---

## 2. Integración Meta actual

- Env: `META_APP_ID`, `META_APP_SECRET`, `META_GRAPH_BASE_URL`, mocks WhatsApp/Instagram.
- Canal por cliente: tokens cifrados, health Graph-specific.
- MCP mencionado solo en docs/acordeón WhatsApp como herramienta de builder, no integrado.

---

## 3. Capacidades MCP oficiales (inventario)

Endpoint: `https://mcp.facebook.com/devtools` · Transport: **Streamable HTTP** · Auth: **OAuth** (cuenta developer Meta) · Scopes por app: **Read** / **Manage**.

| Tool | Scope | Uso en OpenLivery |
|------|-------|-------------------|
| `devtools_discovery` | none | Docs (opcional, no MVP UI) |
| `devtools_api_changelog` | none | Deprecations complementarias |
| `devtools_app_list` | Read | Resolver `app_id` |
| `devtools_app` | Read | Salud / settings app |
| `devtools_app_review` | Read | App Review card |
| `devtools_compliance` | Read | Compliance card |
| `devtools_api_usage` | Read | API usage + rate limits + deprecations signals |
| `devtools_webhook_list` | Read | Webhook inspector |
| `devtools_webhook_manage` | **Manage** | Repair (con confirmación) |
| `devtools_webhook_test` | Manage* | Test webhook (*docs: write pair; treat as manage) |

\*Write surface is webhook manage/test only.

**Diferencia vs prompt:** no hardcodear schemas de respuesta; normalizar a DTOs OpenLivery. Auth interactiva OAuth no encaja 1:1 en backend headless → soportar token opcional + **mock mode** + degradación si MCP off/unavailable.

---

## 4. Dónde encaja MCP

```text
Graph API  →  canal (mensajes, WABA, IG publish)
MCP        →  plataforma (usage, review, compliance, webhooks app-level)
MetaPlatformHealthService → /settings/meta + snippet en channel health
```

---

## 5. Cambios backend

1. Config: `META_DEVTOOLS_MCP_*` + thresholds.
2. `MetaDeveloperToolsProvider` (real + mock).
3. `MetaPlatformHealthService` (cache TTL, diagnostics, webhook diff/test/repair).
4. Router `/api/meta/*`.
5. Tabla ligera `meta_webhook_tests` (historial).
6. Enrich WhatsApp/Instagram health con `platform` opcional (no rompe si MCP off).

## 6. Cambios frontend

- `/settings/meta` — dashboard Meta Platform.
- Link desde Settings.
- Snippet “Meta Platform” en WhatsApp Cloud health (global, etiquetado).

## 7. Seguridad

- Frontend **nunca** habla con `mcp.facebook.com`.
- Token MCP solo env/backend; nunca en JSON de respuesta.
- Repair solo con `confirm: true`.
- MCP opcional: canales siguen vivos.

## 8. Riesgos

| Riesgo | Mitigación |
|--------|------------|
| Beta / OAuth IDE-centric | Mock + disabled-by-default |
| Tool schemas cambian | Parser tolerante + UNKNOWN |
| Confundir API usage con mensajes | Copy explícito “Uso de API Meta” |
| Repair borra subscriptions ajenas | Nunca delete desconocidas |

## 9. Plan por fases

| Fase | Estado |
|------|--------|
| 1 Auditoría + este plan | Done |
| 2 Adapter + mock + timeouts | Next |
| 3 Health / API usage / rate limits | Next |
| 4 Webhook inspect / diff / test | Next |
| 5 Repair con confirmación | Next |
| 6 App Review / Compliance / Deprecations | Next |
| 7 UI dashboard | Next |
| 8 Channel health snippet | Next |
| 9 Tests + docs | Next |

---

## 10. Matriz de responsabilidades

| Funcionalidad | MCP | Graph/canal |
|---------------|-----|-------------|
| API usage / app rate limits | Sí | No |
| App Review / Compliance / Deprecations | Sí | No |
| Webhook inspect/test/repair (app) | Sí | Complementario |
| Recibir/enviar mensajes | **No** | **Sí** |
| WABA / Phone / IG account | No | Sí |
| Publishing limit IG | No | `content_publishing_limit` |
