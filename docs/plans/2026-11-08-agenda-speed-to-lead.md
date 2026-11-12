# Plan: scheduling and speed-to-lead (one page)

Scope: Fast Livery systems 1 (speed-to-lead, renovation) and 4 (real estate), plus
system 6 as an automation. Out of scope: invoicing, XML, DIAN, inbound email,
suppliers, payments, voice, and any Equipia code or database.

## Verified starting point

- No `Appointment`, no `AvailabilityRule`, no `AvailabilityException` exist.
- `Client` has no `timezone` column.
- Last migration: `0041_ucp`. New migrations start at `0042`.
- Reusable today: `Lead`, `Contact`, `LeadActivity`, `AgentTool`, the WhatsApp
  template sender, the notification bell, and `POST /api/public/lead-capture/{token}`.

## Phase A: scheduling

### Models (one migration `0042_agenda`, one more per later change)

| Model | Fields that matter |
|---|---|
| `Client.timezone` | IANA string, default `America/Bogota` |
| `AvailabilityRule` | weekday, start/end time, slot duration, buffer, valid window |
| `AvailabilityException` | date, closed flag, special hours |
| `Appointment` | contact, optional lead, agent, start/end (UTC), status, source, notes, `external_event_id`, `meeting_url`, timestamps |
| `AppointmentAudit` | appointment, actor, action, before/after payload |

### Service

`services/agenda.py`: slot computation in the client time zone, no overlaps, buffer,
exceptions honoured; idempotent booking keyed by request; reschedule and cancel.
Unit tests: gaps, DST change, double booking, cancellation frees the slot.

### API (all filtered by `agency_id`)

```
GET  /api/clients/{client_id}/availability
PUT  /api/clients/{client_id}/availability
GET  /api/clients/{client_id}/availability/slots?from=&to=&duration=
GET  /api/clients/{client_id}/appointments
POST /api/clients/{client_id}/appointments
PATCH /api/clients/{client_id}/appointments/{id}
GET  /api/portal/appointments
```

### Agent

Two tools on the existing `AgentTool` mechanism: `list_slots` and `book_slot`.
The agent may only book a slot it was offered; the service re-validates.

### Connectors

Fixed link by default (no setup). Google Calendar + Meet over OAuth, encrypted with
the existing secret mechanism. Zoom optional per appointment. `.ics` fallback
generated in the API, no new dependency.

### Screens

Client detail gains an **Agenda** tab (hours, duration, buffer, time zone, connector);
lead detail gains **Schedule**; a minimal week view; portal gains **My appointment**.

### Notifications

Confirmation on booking, reminders at 24 h and 1 h, using the existing template
sender. One documented scheduler job with an injectable clock, not a new queue.

## Phase B: speed-to-lead

`LeadCaptureSettings` gains `sla_minutes`, `outbound_template_name`,
`outbound_template_language`. On lead creation: send the welcome template when
configured and consented, set `sla_due_at`; first outbound message sets
`first_response_at`; breach marks `sla_breached` and notifies the owner. Dashboard
gains average first response, share inside SLA, and leads outside business hours.
Lead origin (`form`, `widget`, `whatsapp`, `ctwa_clid`, UTM) is stored and shown.

## Phase C: vertical playbooks

Two seeds: renovation and real estate. Each ships agent script, knowledge Q&A,
qualification fields, pipeline stages and demo data. Add "create client from
playbook" and a five-minute demo script per vertical.

## Phase D: onboarding and hardening

Embedded Signup end to end per client, base template provisioning, channel health
check with readable errors, updated `docs/manual-usuario`, and a review that no new
query breaks `agency_id` isolation.

## Risks

| Risk | Mitigation |
|---|---|
| Time zone and DST bugs | Test with a zone that shifts, not only Bogota |
| Double booking under concurrency | Unique constraint on (client, start) plus idempotency key |
| Google OAuth token expiry | Store `expires_at`, refresh, mark the connector as needing reconnection |
| Scheduler without a queue | One job with an injectable clock, restartable, idempotent |
| Sending templates without consent | Consent flag checked in the same transaction as the send |

## Verification per phase

```
make test
cd apps/web && npm run lint && npm run build
cd apps/whatsapp && npm test && npm run build
```

Each phase ships one commit with its migration and its tests.

## Decision: the agent books, orchestrated by LangGraph

The agent runs the booking inside the conversation; the customer is not sent away
to a portal link. LangGraph becomes the orchestrator of the reply pipeline.

### Why it changes the estimate

Today the pipeline is a single model call: webhook, save message, one
`chat_completion`, save reply, send. There is no tool loop and no persisted graph
state. Booking needs at least one tool round trip, so the pipeline changes shape.

### Graph

```
webhook -> load_conversation -> classify -> retrieve_knowledge
        -> decide --(tool needed)--> tools(list_slots | book_slot) -> decide
                  --(answer)--------> respond -> persist -> send
                  --(human)---------> handoff (mode="human", interrupt)
```

- State: `conversation_id`, `client_id`, `agency_id`, `messages`, `lead_id`,
  `offered_slots`, `chosen_slot`, `mode`.
- Checkpointer: `langgraph-checkpoint-postgres` on the same database, so the graph
  survives a restart like the rest of the data. New tables come from its own
  migration, not from Alembic.
- `thread_id` is the conversation id. That keeps tenant isolation: a thread cannot
  span two clients.
- Handoff: an interrupt sets `mode="human"` and stops the graph, matching today's
  behaviour.

### Tools exposed to the graph

| Tool | Contract |
|---|---|
| `list_slots` | client id, from, to, duration -> free slots in the client zone |
| `book_slot` | slot start, contact, lead -> appointment, with `idempotency_key` = conversation + start |
| `reschedule_slot` | appointment, new start |
| `cancel_appointment` | appointment, reason |

The graph may only book a slot it offered in this thread; the service re-validates
availability before writing.

### Cost and risk

| Item | Impact |
|---|---|
| New dependencies | `langgraph` + `langgraph-checkpoint-postgres`; justified by the decision |
| Extra latency | Two model calls on booking turns instead of one |
| Extra cost | Tool turns consume tokens; cap the loop at two rounds per message |
| Testing | Tests need a scripted fake model, not a real provider |
| Isolation | `thread_id` = conversation id; never a global thread |

### Revised Phase A

| Block | Days |
|---|---|
| Models and migration 0042 (done) | - |
| Availability service and tests | 3 |
| API: availability and appointments | 3 |
| LangGraph pipeline with the four tools | 6-8 |
| Screens: agenda tab, schedule from lead, portal | 4 |
| Connectors: fixed link and .ics, then Google Calendar | 4-6 |

Phase A now totals 20-24 days, up from 14-18, because the orchestrator replaces the
single-call pipeline.
