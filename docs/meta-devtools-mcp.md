# Meta Developer Tools MCP (Social Technologies MCP)

Fast Livery uses Meta’s hosted MCP **only for platform diagnostics** — not for sending/receiving WhatsApp or Instagram messages.

Official docs: [Meta DevTools MCP](https://developers.facebook.com/documentation/mcp/devtools-mcp)  
Endpoint: `https://mcp.facebook.com/devtools` (Streamable HTTP)  
Rename note (2026-08-18): Meta also calls this **Social Technologies MCP**.

## What Fast Livery uses MCP for

| Capability | Tool (official names) |
|------------|------------------------|
| App list / settings | `devtools_app_list`, `devtools_app` |
| API usage / rate limits / deprecation signals | `devtools_api_usage` |
| Webhook inspect | `devtools_webhook_list` |
| Webhook test / manage | `devtools_webhook_test`, `devtools_webhook_manage` (Manage scope) |
| App Review | `devtools_app_review` |
| Compliance | `devtools_compliance` |

## What does **not** depend on MCP

- Inbound/outbound WhatsApp messages  
- Instagram content publishing  
- Inbox / agents  
- Channel Graph health (phone, token, WABA)

If MCP is off or down, messaging continues. Only advanced diagnostics degrade.

## Configuration

```bash
META_DEVTOOLS_MCP_ENABLED=true
META_DEVTOOLS_MCP_URL=https://mcp.facebook.com/devtools
META_DEVTOOLS_MCP_TIMEOUT=25
META_DEVTOOLS_MCP_ACCESS_TOKEN=   # optional bearer if your Meta access allows server use
META_DEVTOOLS_MCP_MOCK_MODE=true  # UI/dev without live MCP OAuth
META_DEVTOOLS_MCP_MANAGE_ENABLED=false  # set true only with Manage scope
META_API_WARNING_THRESHOLD=70
META_API_CRITICAL_THRESHOLD=90
```

**Auth reality:** Meta’s MCP is primarily OAuth for IDE agents. Server-side Fast Livery supports optional bearer + **mock mode**. Prefer mock for local UI; use live MCP when your Meta account/token path is available.

## UI

**Settings → Meta Platform** (`/settings/meta`)

Shows App, API usage (% Graph calls — **not** WhatsApp message quota), rate limits, webhooks, App Review, Compliance, deprecations, full diagnostics, webhook test/repair (confirm required).

WhatsApp channel health may show a **Meta Platform (global)** note linking here.

## API

| Method | Path |
|--------|------|
| GET | `/api/meta/status` |
| GET | `/api/meta/health` |
| POST | `/api/meta/health/refresh` |
| POST | `/api/meta/diagnostics` |
| GET | `/api/meta/webhooks` |
| POST | `/api/meta/webhooks/test` |
| GET | `/api/meta/webhooks/repair/preview` |
| POST | `/api/meta/webhooks/repair` `{ "confirm": true }` |

Repair never deletes unknown subscriptions.

## Responsibility matrix

| Concern | MCP | Graph / channel API |
|---------|-----|---------------------|
| API usage / app rate limits | Yes | No |
| App Review / Compliance | Yes | No |
| Webhook app subscriptions | Yes | Complement |
| Send/receive messages | **No** | **Yes** |
| WABA / phone / IG account | No | Yes |

## Troubleshooting

| Symptom | Action |
|---------|--------|
| “Diagnostics not configured” | Enable MCP or mock |
| 503 UNAVAILABLE | Timeout/token/beta access — messaging unaffected |
| Repair disabled | Need Manage scope + `META_DEVTOOLS_MCP_MANAGE_ENABLED=true` |
| Confused “message quota” | Remember API usage ≠ WhatsApp messaging limits |
