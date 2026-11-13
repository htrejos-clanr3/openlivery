# Release plan: the agency platform first, capture and scheduling second

## Objective

Fast Livery is the platform an agency uses to run its clients' marketing: plan,
produce, approve and publish content on the client's social accounts, with the AI
writing in each brand's voice, and hand the client the result without friction.

```
idea or request -> content in the brand voice -> client approval
     -> publish on Instagram and Facebook -> monthly report
```

Lead capture and scheduling are the **complement**: they turn the audience the
publication generates into conversations and appointments. WhatsApp is the entry
channel for both.

## Core release: publishing

| # | Block | Days | Depends on |
|---|---|---|---|
| 1 | Publish on Instagram and Facebook: image, carousel, reel, story; states, retries, idempotency | 11-17 | Meta permissions approved |
| 2 | Calendar and grid: schedule per client time zone, queue, cancel | 5-7 | 1 |
| 3 | Approval: passwordless link valid 30 days, and approval by WhatsApp from a phone linked to the client | 8-11 | 2 |
| 4 | Monthly report: real metrics per network, PDF, branding chosen by the agency | 8-10 | 1 |
| 5 | Brand voice: tone, rules and published examples applied to captions | 8-11 | 1 |
| 6 | Connectors beyond Instagram and Facebook (TikTok, YouTube, LinkedIn) | 15-25 | one Meta/TikTok review per network |

Core total: 40-56 days, plus the Meta review time, which runs in parallel.

## Complement: capture and scheduling

| # | Block | Days | State |
|---|---|---|---|
| 7 | Scheduling: availability, appointments, booking API, agency screen | done | working in production, booking verified |
| 8 | Portal "my appointment" and booking from the lead | 2 | missing |
| 9 | Reminders 24 h and 1 h over WhatsApp templates | 2 | missing |
| 10 | Agent books inside the conversation (LangGraph, flagged, with fallback) | 6-8 | missing |
| 11 | First-response SLA on the lead | 2 | missing |
| 12 | Roles: agency staff versus client portal | 2 | missing |

## Meta permissions, the real critical path

| Permission | Needed for |
|---|---|
| `instagram_basic`, `instagram_content_publish` | Publish and read the account |
| `instagram_manage_messages`, `instagram_manage_comments` | Leads from DMs and comments |
| `pages_show_list`, `pages_manage_posts` | Publish to the client's Facebook page |
| `business_management` | Manage the client's assets |

Advanced access requires App Review. Accounts belong to each client, so the
connection is OAuth per client; Tech Provider is only needed to onboard a client's
WhatsApp numbers through Embedded Signup.

Start the review on day one: without it, block 1 cannot be tested with real
accounts, and no amount of code fixes that.

## Definition of done for the core release

1. The agency schedules a post for a client and it publishes at the right hour in
   the client's time zone.
2. The client approves a piece from a link or from WhatsApp, and the approval
   shows in the panel.
3. A failed publication is retryable and never duplicates.
4. The monthly report shows the same numbers as Meta for the same range.
5. Captions sound like the brand, not like a template.

## Out of scope for this release

Invoicing, XML, DIAN, inbound email, suppliers, payments, voice, content
marketplaces, and any Equipia code or database.

## What exists today

- Multi-tenant agency/client isolation, WhatsApp Cloud receiving and replying,
  leads with score and follow-up, an MCP endpoint for assistants.
- Scheduling: models, service with tests, API, agency screen. Booking, duplicate
  rejection and cancellation verified against production.
- Instagram and LinkedIn OAuth channels, carousels with agency-side approval.

## What does not exist

Publishing to any network, calendar, approval links, reports, brand voice, and the
complement blocks 8-12.
