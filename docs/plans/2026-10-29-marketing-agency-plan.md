# Fast Livery: from chatbot to marketing agency platform

The product is a marketing agency operated by software: the brief arrives on
WhatsApp, becomes content, gets approved, is published on Instagram and Facebook,
and closes the month with a report. Meta is the foundation, not the goal.

## Architecture

```
Client (WhatsApp) -> Inbox / Agent -> Brief
Agency -> Content -> Approval -> Publishing -> Report
             ^            ^            |
      Brand brain    Link / WhatsApp   Provider gateway
                                      - Graph (IG/FB)
                                      - Higgsfield (video)
```

The provider gateway is internal to Fast Livery: it stores encrypted credentials,
runs the calls and exposes business actions. No other module sees third-party
tokens.

## Decisions already made

| Decision | Value |
|---|---|
| IG/FB accounts | Owned by each client, connected per client with OAuth |
| Tech Provider | Not needed to publish; only to onboard clients' WhatsApp numbers |
| Approval channel | WhatsApp or passwordless link, one state machine |
| Publishing | Immediate and scheduled with prior approval |
| Formats in V1 | Image, carousel, reel, story |
| Approval link | Expires after 30 days |
| Who approves | Phone must be linked to the client; others may only read |
| Report branding | Agency or client, editable by the agency only |
| Time zone | Per client |
| MCP connections | Any provider, verified: catalogue installs immediately, manual URLs need agency approval |
| Higgsfield billing | Per client: agency credit or the client's own account |

## Phases

| Phase | Scope | Days |
|---|---|---|
| F0 | Meta permissions, business verification, app review | 5-7 |
| F1 | Publish image, carousel, reel, story to IG/FB; immediate mode | 11-17 |
| F2 | Calendar, queue, per-client time zone | 5-7 |
| F3 | Approval by link (30 days) and by WhatsApp with a linked phone | 8-11 |
| F4 | Reports with real metrics, PDF, agency-configurable branding | 8-10 |
| F5 | Brand brain and a bank of 20 ideas per client | 8-11 |
| F6 | Higgsfield: create job, download MP4, publish as reel | 8-12 |
| F7 | Close-out: tests, limits, observability, manuals | 6-8 |

Total: 59-83 dev days, plus 2-6 weeks of Meta review running in parallel.

V1.1, not blocking publication: per-client MCP connections, 29-39 days.

## What already exists

- Multi-tenant agency/client isolation.
- WhatsApp Cloud connected, receiving and replying (verified in production).
- Instagram and LinkedIn OAuth channel scaffolding.
- Carousels with agency-side approval.
- Meta setup wizard, split into agency and client steps.
- Foundation tables on this branch: post_pieces, approval_links, client_phones,
  provider_connections.

## What does not exist yet

Publishing, scheduling, approval links, reports, brand brain, provider gateway.

## Critical path

1. F0 on day one: without approved permissions there is nothing to test with a
   client's accounts.
2. F1 before any cosmetic interface: if it does not publish, there is no product.
3. F3 after F2: approving without a calendar adds nothing.
4. F4 last, because reports need real publication data.

## Non-negotiables

- Test migration 0041 against a clone of the production dump, never against
  production.
- `post_pieces` is named that way because `content_items` already exists in
  production with a different shape.
- Never rename `ENCRYPTION_KEY`.
