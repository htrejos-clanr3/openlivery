# Release plan: the whole product, not just scheduling

Shipping means a pilot client can go from a message to a booked, reminded
appointment, and the agency can see what happened. Everything else is optional.

## Definition of done

1. A stranger writes on WhatsApp or fills the form.
2. The agent answers within the SLA and qualifies the lead.
3. The agent offers real slots and books one, or the customer books from the portal.
4. The customer gets a confirmation and two reminders.
5. The agency sees the appointment, the lead score and the first-response time.
6. The client never sees agency administration.

When those six hold, the product is sellable. Publishing to Instagram, reports
and content are a second release.

## Ordered blocks

| # | Block | Why it blocks shipping | Days |
|---|---|---|---|
| 1 | Portal "Mi cita": book and see own appointment | The customer must finish the cycle without the agency | 2 |
| 2 | Reminders 24 h and 1 h over WhatsApp templates | No-shows destroy the perceived value | 2 |
| 3 | Agent booking: LangGraph with list_slots and book_slot, fallback to today's single call | The core promise: speed-to-lead with a real slot | 6-8 |
| 4 | One vertical playbook (renovation) with script, Q&A, qualification fields and demo data | Without it the agent improvises and the pilot fails | 3 |
| 5 | First-response SLA on the lead: due time, first response, breach alert | The commercial argument, measured | 2 |
| 6 | Role separation: who sees agency settings, who sees the client portal | A pilot with several people needs permissions | 2 |
| 7 | Hide agency steps in the WhatsApp wizard, as done for Instagram | A client must not see the agency app | 1 |

Total: 18-20 days, plus Meta approvals already pending for publishing.

## Explicitly out of this release

Google Calendar and Zoom connectors (fixed link and .ics cover the pilot),
Instagram publishing, reports, brand brain, MCP marketplace, invoicing.

## Verification per block

```
make test
cd apps/web && npm run lint && npm run build
./scripts/verify_production.sh
```

Plus, for this release, one manual pass of the six points above with a real
phone number and a real inbox.

## What can go wrong, and the order that limits it

- The graph replacing the single-call pipeline is the riskiest change: it can
  silence the agent. Ship it behind a flag, keep the current path as fallback,
  and cap tool rounds at two per message.
- Reminders need a scheduler. One documented job with an injectable clock, not a
  queue.
- Portal booking needs its own auth path; reuse the existing portal session, do
  not invent a second login.

## Current state

| Piece | State |
|---|---|
| WhatsApp Cloud receiving, replying, storing | works in production |
| Leads with score, evaluation and follow-up panel | works |
| Scheduling: models, service, API, agency screen | works, verified with a real booking |
| Agent booking, portal booking, reminders, SLA, roles | do not exist |
