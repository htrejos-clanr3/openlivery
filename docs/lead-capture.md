# Lead capture and commercial leads (per client)

A **contact** is a known person. A **lead** is a commercial opportunity linked to that contact (one contact can have many leads). Capture is an automation; the Leads tab is for working the pipeline.

Tenant isolation is mandatory: every query uses `agency_id` + `client_id`. There is no `tenant_id` column.

## Where to configure what

| Need | Place |
| --- | --- |
| List, filter, create, and update opportunities | Client → **Leads** |
| Simple on/off + channels + default owner/stage | Bottom of **Leads** |
| Form/webhook URL, token, rotate | Client → **Channels** → Forms / Webhooks |
| Triggers, tags, notify, commercial-intent flag | Client → **Automatizaciones**, or agency **Automations** with a client picker |

Capture stays **off** until you enable it.

## Flow

1. Inbound message or form identifies/creates a **Contact** (dedupe by phone, email, `channel_identifier`).
2. `LeadDetectionService` (rule today, LLM-ready later) decides if it is commercial.
3. If an **open** lead exists for that contact (not Ganado/Perdido), update last activity and conversation. Do **not** create another lead automatically.
4. Otherwise create a Lead, assign owner, notify, write `lead_capture_events`.
5. Later messages only refresh activity (`safe_touch_open_lead`). They never open a second automatic lead.

WhatsApp (Cloud and QR) and the widget hook on first conversation; later messages update activity. Instagram/Facebook DMs are not ingested yet; send `source=instagram` or `source=facebook` to the public URL.

## Public ingest (unchanged contract)

`POST /api/public/lead-capture/{token}`

```json
{
  "source": "form",
  "name": "...",
  "email": "...",
  "phone": "...",
  "channel_identifier": "..."
}
```

`source`: `form` | `webhook` | `instagram` | `facebook`.

## Stages

Nuevo, Contactado, Calificado, Propuesta, Ganado, Perdido.

Closed stages (Ganado / Perdido) allow a new automatic lead for the same contact.

## Notifications

On create: notify the lead owner, or every agency user if none is set. History lives on the lead. Unread items appear on the app-shell bell, not as a block on the Leads tab.

## Isolation

Listing, get, patch, and retry always filter `agency_id` + `client_id`. Another agency gets 404 even with a UUID in the URL.
