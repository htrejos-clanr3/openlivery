# Conversation lifecycle: status, priority and response clocks

## Context

Conversations carry `mode` (`ai` or `human`), `assigned_user_id`, `labels` and
`operator_read_at`, but no lifecycle state. The inbox exposes fixed tabs
(`all`, `mine`, `unread`, `human`, `ai`) and the only way to express "this is
done" is to stop answering.

The queue therefore mixes three different things: conversations the AI is
handling, conversations abandoned to a human, and conversations already closed.
Priority is absent, so ordering is by last activity only.

## Decision: what `pending` means

**`pending` means "waiting for a human".** `open` means "someone is actively on
it" (the AI or an operator, depending on `mode`). `resolved` closes the
conversation. `snoozed` hides it until `snoozed_until`.

Rationale: this product is AI-first. A customer message is answered in seconds,
so an "unattended" state would almost never be observable, while "the AI handed
this off and nobody picked it up" is the one signal an agency actually needs.
It also makes the queue actionable: the `pending` tab is the human backlog.

Alternatives considered and rejected:

- **`open` = unattended, `pending` = waiting on the customer.** Faithful to how
  many helpdesks read, but it hides the human backlog and conflicts with the AI
  answering immediately.
- **No `pending` at all** (`open` / `resolved` / `snoozed`). Fewer columns, but
  loses the only queue that matters operationally.

## Data model

Migration `0039`, additive on `conversations`:

| Column | Type | Notes |
|---|---|---|
| `status` | `str(20)`, index, default `open` | `open` `pending` `resolved` `snoozed` |
| `priority` | `str(10)`, default `medium` | `low` `medium` `high` `urgent` |
| `snoozed_until` | timestamptz null | when the conversation returns to the queue |
| `status_changed_at` | timestamptz null | audit of the last transition |
| `waiting_since` | timestamptz null | since when a human reply is owed |
| `first_reply_created_at` | timestamptz null | first **human** reply; base for FRT |

Indexes `(agency_id, status)` and `(status, snoozed_until)`.

Backfill: `mode = 'human'` becomes `pending`, everything else `open`;
`waiting_since` takes the last visitor message time on pending rows;
`first_reply_created_at` takes the first `sender_type = 'human'` message where
one exists, so reporting works from day one.

Columns with defaults are a fast, additive change on Postgres 17. No existing
column changes meaning.

## Transitions

All of it lives in `services/conversation_lifecycle.py`, so the rules are not
scattered across routers.

| Event | Effect |
|---|---|
| Visitor message | `resolved`/`snoozed` reopen to `open` when `mode = ai`, `pending` when `mode = human`; clear `snoozed_until`; set `waiting_since` if null |
| AI reply | no change to status, `waiting_since` or `first_reply_created_at` |
| Handoff (`mode` -> `human`) | `open` becomes `pending` |
| Human reply (`POST /reply`) | `waiting_since = null`; set `first_reply_created_at` if null; `pending` becomes `open` |
| `PATCH status` | validate the enum; `resolved` clears `waiting_since`; `snoozed` requires a future `snoozed_until` |
| Snooze expiry | on read, `snoozed` with `snoozed_until <= now` reports as `open`/`pending` according to `mode` |

Snooze expiry is computed on read; no scheduler is needed.

AI replies deliberately do not stop the clock. `waiting_since` measures the
human backlog, and AI response time is already derivable from the messages.

## API

- `PATCH /conversations/{id}/status` with `{status, snoozed_until?}`.
- `PATCH /conversations/{id}/priority` with `{priority}`.
- `GET /conversations/inbox` gains `status` and `priority` filters; default
  ordering becomes priority descending, then last message, keeping `limit` and
  `offset`.
- `ConversationOut` and `ConversationInboxOut` expose the six new fields.

Everything stays filtered by the authenticated user's `agency_id`; tenant
isolation is the boundary that must not regress.

## UI

Inside the existing agent inbox: a status badge and a priority dot per row;
tabs **Pending** and **Resolved**; actions **Resolve**, **Reopen** and
**Snooze** (1 h, 4 h, tomorrow) plus a priority selector in the detail pane.
Copy goes through `apps/web/lib/i18n/dicts/inbox.ts` in English and Spanish.

## Testing

`tests/test_conversation_lifecycle.py`:

- visitor message reopens `resolved` and clears snooze;
- handoff sets `pending`; the first human reply sets `open`, stops the clock and
  records `first_reply_created_at`;
- an AI reply leaves all three clocks untouched;
- snooze expiry reports `open` or `pending` per mode;
- filters by status and priority, and the new ordering;
- invalid status or a past `snoozed_until` returns 422;
- another agency cannot read or patch the conversation.

## Rollout

Migration `0039` runs automatically when the api starts. Deploy follows the
established path: build on the server with `-p fast-livery`, verify health, keep
the `rollback-*` image tags.

## Out of scope

SLA policies, CSAT surveys, teams, automation rules (event/condition/action),
per-agent capacity and real-time transport. Each needs its own design; the
lifecycle columns here are the prerequisite for most of them.
