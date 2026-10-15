# WhatsApp Meta setup (Fast Livery)

**Audience:** each **client** in Fast Livery usually configures their **own** Meta WhatsApp credentials.

There is **no official QR** for Cloud API. QR in Fast Livery is a separate unofficial channel. Cloud API = Meta App + IDs + token + webhook (once per client).

Domain model: **Client → WhatsAppCloudChannel → Agent → Conversations → Inbox**.

## Primary path — per client (recommended for multi-tenant)

Do this **for every client** that should use Cloud API:

### A. In Meta

1. Open [Meta for Developers](https://developers.facebook.com/apps/) → create/open a **Business** app → add **WhatsApp**.
2. Go to **WhatsApp → API setup**.
3. Under **From**, copy **Phone number ID** (long numeric ID — not the `+57…` display number).
4. On the same page, copy **WhatsApp Business Account ID (WABA)**.  
   If missing: [Meta Business Suite](https://business.facebook.com/) → Settings → Accounts → WhatsApp accounts → ID.
5. Create a **System User** permanent token with WhatsApp messaging permissions  
   (Business settings → Users → System users).
6. Copy **App Secret**: App settings → Basic.

Official overview: [Cloud API Get Started](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started/).

### B. In Fast Livery (that client)

1. Clients → client → **WhatsApp Cloud**.
2. Assign the agent that will answer.
3. Open **Advanced settings**.
4. Paste Phone Number ID, WABA, token, App Secret → **Save**.
5. **Connect / verify** — Fast Livery validates the token and **tries to register the webhook in Meta** (`override_callback_uri` on the phone number). Retry with `POST …/register-webhook` if Meta rejects it (usually missing `whatsapp_business_management`).
6. If auto-register fails or the Meta app has never had a webhook: paste **Callback URL** + **Verify token** once in Meta → WhatsApp → **Configuration**, subscribe to **messages** (and `message_template_status_update` if you use templates).

Each client has a **unique** webhook URL (`…/channels/{channel_id}/webhook`).

If a WABA already has an **agency/brain override**, Fast Livery **does not** overwrite it (same safety as Vocero).

**Templates:** `GET /api/whatsapp-cloud/channels/{client_id}/templates` lists WABA templates; `POST …/templates/send` sends an approved template (outside the 24h window).

In the product UI, the accordion **Cómo conectar este cliente** mirrors this guide (collapsed by default).

## Instagram on the same Meta App

WhatsApp Cloud and Instagram Content Publishing can share **one** Meta Business App:

| Product | Needs on the Meta App | Fast Livery env |
|---------|----------------------|-----------------|
| WhatsApp Cloud | WhatsApp product + WABA + System User token (or Embedded Signup config) | per-client token **or** `META_APP_ID` + `META_WHATSAPP_CONFIG_ID` |
| Instagram publishing | Instagram / Facebook Login + Page linked to IG Business + App Review for publish scopes | same `META_APP_ID` + `META_APP_SECRET`; redirect `INSTAGRAM_OAUTH_REDIRECT_PATH` |

Additional for Instagram (not covered by WhatsApp alone): Facebook Page, Instagram professional account linked to that Page, and scopes such as `instagram_content_publish` / `pages_show_list`. WhatsApp messaging tokens do **not** grant Instagram publish by themselves — OAuth (or BYO IG token) is still required per client.

Equipia’s OAuth pattern (signed `state`, code exchange, secrets in a vault, frontend return query) matches Fast Livery’s WhatsApp Embedded Signup + Instagram OAuth helpers; Equipia itself uses Baileys/Cloud BYO for WhatsApp more than Embedded Signup.

## Optional path — one Meta App for the whole platform

Only if you operate a **single** Meta App for all clients (**Embedded Signup**):

```bash
META_APP_ID=
META_APP_SECRET=
META_WHATSAPP_CONFIG_ID=
META_GRAPH_BASE_URL=https://graph.facebook.com/v23.0
FRONTEND_URL=https://your-public-host
META_OAUTH_REDIRECT_PATH=/api/whatsapp-cloud/oauth/callback
```

Redirect URI:

```text
{FRONTEND_URL}/api/whatsapp-cloud/oauth/callback
```

Then operators can use **Connect with Meta**. Without these env vars, use the per-client path above.

## Webhook

```text
{FRONTEND_URL}/api/public/whatsapp-cloud/channels/{channel_id}/webhook
```

- Verify token: shown in the UI (plaintext by design).
- Signature: channel App Secret, or platform `META_APP_SECRET` if the channel has none.

## QR vs Cloud API

| | QR (Baileys) | Cloud API |
|--|--------------|-----------|
| Official | No | Yes |
| Per-client setup | Scan once | Meta IDs + webhook once |
| Risk | Session/WhatsApp Web breaks | Needs Meta App + HTTPS |

Keep QR for demos if it works; use Cloud API per client for production.

## Meta Developer Tools MCP

[MCP DevTools](https://developers.facebook.com/documentation/mcp/devtools-mcp) helps **developers** manage Meta Apps from an IDE (webhooks, docs, health). It does **not** replace the per-client form in Fast Livery.

## Environment variables

| Variable | When |
|----------|------|
| `META_GRAPH_BASE_URL` | Always (Graph version) |
| `ENCRYPTION_KEY` | Always (encrypts tokens) |
| `META_APP_ID` / `META_APP_SECRET` / `META_WHATSAPP_CONFIG_ID` | Only Embedded Signup / platform app |
| `META_MOCK_MODE` | Local UX without Meta |
| `FRONTEND_URL` | Public origin for webhooks/redirects |

## Troubleshooting

| Symptom | Check |
|---------|--------|
| Wrong IDs | Phone number ID ≠ display phone; WABA on API setup or Business Suite |
| Signature invalid | App Secret matches the Meta App that signs webhooks |
| Verification failed | Verify token matches this channel’s UI value |
| Token expired | New System User token or reconnect |
| Wrong client | Webhook URL must use that channel’s UUID |
