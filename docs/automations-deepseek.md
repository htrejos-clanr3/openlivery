# DeepSeek automations (Fast Livery)

Five sales automations from the “$1k–$5k” playbook, **only the parts DeepSeek can do in-app**.

Open **Automatizaciones** in the sidebar. Requires a DeepSeek key in Settings (`deepseek-chat`). Other providers are not used on this screen.

Runs are **per signed-in user**, not per agency. History lives in `user_automation_runs` and `GET /api/automations/runs` only returns the current user’s rows. Another login on the same agency does not see those results.

| # | Playbook | In Fast Livery | Not in this slice |
|---|----------|---------------|-------------------|
| 1 | Form → CRM → Slack | Clean/normalize messy form JSON | HubSpot, Airtable, Slack send |
| 2 | Lead scoring | Extract fields with DeepSeek + rubric in Python | Auto-assign in a CRM |
| 3 | Documents | Fill `{{variables}}` + professional draft | E-sign, PDF storage |
| 4 | Call reminders | Email subject/body (24h, 1h, follow-up) | Calendly, calendar, sending |
| 5 | Onboarding | Welcome email copy | Drive folders, Asana, Monday |

## Rubric (automation 2)

- Budget ≥ $10,000 → +3
- Start in ≤ 30 days → +2
- Company ≥ 50 employees → +2
- Decision maker → +3
- 7+ hot (senior sales) · 4–6 warm (follow-up) · &lt;4 cold (archive)

## API

All endpoints require the session cookie. POSTs persist a run and return `{ id, user_id, kind, payload, result, created_at }` — the LLM output is in `result`.

- `GET /api/automations/status` — includes `user_id` / `user_name`
- `GET /api/automations/runs` — last 50 runs for the current user
- `GET /api/automations/runs/{id}` — 404 if the run belongs to someone else
- `POST /api/automations/normalize` `{ "payload": ... }`
- `POST /api/automations/score` `{ "payload": ... }`
- `POST /api/automations/document` `{ "template", "variables", "doc_type" }`
- `POST /api/automations/copy` `{ "kind": "reminder_24h"|"reminder_1h"|"followup"|"onboarding", "context" }`
