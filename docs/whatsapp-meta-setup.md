# WhatsApp Meta setup (OpenLivery)

OpenLivery supports two ways to connect WhatsApp Cloud API per client:

1. **Managed / Embedded Signup (recommended)** — OpenLivery owns a Meta App; the operator clicks **Connect with Meta**.
2. **Advanced / BYO Meta App** — paste Phone Number ID, WABA ID, access token and app secret manually.

The domain model stays: **Client → WhatsAppCloudChannel → Agent → Conversations → Inbox**.

## 1. Create / configure a Meta App

1. Go to [Meta for Developers](https://developers.facebook.com/).
2. Create an app (type Business) or use an existing one.
3. Add the **WhatsApp** product.
4. Note **App ID** and **App Secret**.

## 2. Activate WhatsApp

In the app dashboard → WhatsApp → API setup:

- Create or select a WhatsApp Business Account (WABA).
- Add / verify a phone number for development or production.

## 3. Embedded Signup

1. Configure [Embedded Signup](https://developers.facebook.com/docs/whatsapp/embedded-signup/) for your app.
2. Create a configuration and copy the **Config ID**.
3. Set environment variables on the API:

```bash
META_APP_ID=...
META_APP_SECRET=...
META_WHATSAPP_CONFIG_ID=...
META_GRAPH_BASE_URL=https://graph.facebook.com/v23.0
FRONTEND_URL=https://your-public-host
```

Without these, the UI shows **Connect with Meta** but falls back to advanced setup (or mock mode).

## 4. Redirect URI

Callback path (proxied through the gateway):

```text
{FRONTEND_URL}/api/whatsapp-cloud/oauth/callback
```

Register that exact URL in the Meta App OAuth redirect settings.

`META_OAUTH_REDIRECT_PATH` defaults to `/api/whatsapp-cloud/oauth/callback`.

## 5. Webhook

Each channel has its own webhook URL:

```text
{FRONTEND_URL}/api/public/whatsapp-cloud/channels/{channel_id}/webhook
```

- **Verify token**: shown in the UI after the channel exists (plaintext by design).
- **Signature**: HMAC-SHA256 with the channel app secret, or platform `META_APP_SECRET` when the channel has no BYO secret.

Subscribe to the `messages` field.

Routing is by **channel UUID in the URL**, not by Phone Number ID in the payload.

## 6. Verify token

Generated per channel (`webhook_verify_token`). Copy from the WhatsApp Cloud page.

## 7. Permissions

Confirm current Meta docs for Embedded Signup. Typically related scopes include business management and WhatsApp messaging permissions granted during signup. Do not hardcode outdated names without checking Meta’s current list.

## 8. Environment variables

| Variable | Purpose |
|----------|---------|
| `META_GRAPH_BASE_URL` | Graph root + version |
| `META_APP_ID` | Platform Meta App |
| `META_APP_SECRET` | Platform secret (webhook + code exchange) |
| `META_WHATSAPP_CONFIG_ID` | Embedded Signup config |
| `META_MOCK_MODE` | Local signup without Meta |
| `META_OAUTH_REDIRECT_PATH` | OAuth callback path |
| `ENCRYPTION_KEY` | Fernet encryption for tokens / secrets |
| `FRONTEND_URL` | Public origin for webhook + redirects |

## 9. Local development

```bash
# .env.docker or .env
META_MOCK_MODE=true
META_APP_ID=dev-mock
```

Then open a client → WhatsApp Cloud → **Connect with Meta**. Mock mode completes signup and marks the channel connected without Graph calls.

For real Graph calls locally you need a public HTTPS URL (tunnel) for webhooks and OAuth.

## 10. Production

- Set real `META_*` values; keep `META_MOCK_MODE=false`.
- Use strong `ENCRYPTION_KEY` / `SECRET_KEY`.
- `COOKIE_SECURE=true` behind HTTPS.
- Register production redirect + webhook domains in Meta.

## 11. Troubleshooting

| Symptom | Check |
|---------|--------|
| Managed unavailable | `META_APP_ID` / `META_WHATSAPP_CONFIG_ID` / mock mode |
| Signature invalid | App secret matches the Meta App that signs webhooks |
| Verification failed | Verify token matches UI |
| Token expired | Reconnect with Meta or paste a new permanent token |
| Wrong client | Webhook URL must use that channel’s UUID |

## Managed vs manual

| Mode | Operator provides | Secret for webhook |
|------|-------------------|--------------------|
| Managed / Embedded | Click Connect with Meta | `META_APP_SECRET` (platform) |
| Manual (advanced) | Phone ID, token, app secret | Channel `encrypted_app_secret` |

## BLOCKED_BY_EXTERNAL_CONFIGURATION

Full production Embedded Signup cannot be marked “verified” until you supply a real Meta App, Config ID, public HTTPS redirect, and complete Meta’s business verification / permissions. Code paths exist; enable them with env + Meta console.
