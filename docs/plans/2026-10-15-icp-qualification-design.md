# Ideal customer profile and lead qualification

## Context

Leads already land in this product from WhatsApp, the widget, public forms and
webhooks. The pipeline ships with the stages `New -> Contacted -> Qualified ->
Proposal -> Won -> Lost`, and `leads.score` exists in the schema but is never
written: the UI hint still says scoring "will come from a later automation".

What is missing is the criterion to score against. Without it every lead is
equally interesting and the pipeline only records what a human decided.

## What we take from Prospector AI

Prospector AI (a product by IAGENCY) describes three steps: define the ideal
customer, let the AI find and qualify companies, and save them to a base that
also contacts them.

We already have steps two and three for everything that reaches us: contacts,
leads, pipeline stages, notifications, and outreach over WhatsApp, Instagram and
LinkedIn. We deliberately do **not** copy discovery: where that product gets its
company data is not published, and scraping personal data carries cost, terms of
service and data-protection exposure.

What we adopt is the missing loop: **an explicit ideal-customer definition, and
a score computed against it.** It improves every lead we already receive, not
only imported ones.

## Decisions

- **One profile per client**, edited by the agency. Same tenancy rule as the rest
  of the product: always scoped by `agency_id`.
- **Score 0-100**, stored in `leads.score`. The previous 0-10 scale in
  `services/automations.py` is an ad-hoc text automation and never persisted;
  it stays untouched and is not reused here.
- **Deterministic scoring**, no LLM call. It must be cheap, testable and stable
  when applied in bulk. An LLM can be layered later for reasons.
- **Accent- and case-insensitive matching**, because the data is Spanish.
  `"Bogotá"` must match `"bogota"`.
- **Disqualifiers hard-stop**: a matched disqualifier sets the score to 0.
- **Opt-in auto-qualification** through `auto_qualify`. Scoring writes an
  activity row, so it must be a decision the agency makes, not a surprise.
- **CSV import** is the bridge for externally sourced lists. It reuses the
  existing contact dedupe by email/phone and skips rows whose contact already
  has an open lead.

## Data model

New table `ideal_customer_profiles`, unique on `client_id`:

| Column | Type | Notes |
|---|---|---|
| `agency_id` | uuid, indexed | tenant scope |
| `client_id` | uuid, unique | one profile per client |
| `sectors` | json list | e.g. `["inmobiliaria", "constructora"]` |
| `cities` | json list | e.g. `["bogota", "medellin"]` |
| `keywords` | json list | product or use-case terms |
| `disqualifiers` | json list | terms that zero the score |
| `size_min` / `size_max` | int, null | employee range, optional |
| `hot_min` / `warm_min` | int, defaults 75 / 45 | band thresholds |
| `auto_qualify` | bool, default false | score on capture |

## Scoring

Weights, capped at 100:

| Signal | Points |
|---|---|
| Sector match | 30 |
| City match | 20 |
| Employee range match | 15 |
| Keywords (5 each) | up to 20 |
| Has email | 10 |
| Has phone | 5 |
| Disqualifier match | score = 0, band `disqualified` |

Bands: `hot` at or above `hot_min`, `warm` at or above `warm_min`, otherwise
`cold`. Every run stores the score on the lead and appends a
`lead_activities` row of kind `qualification` with the breakdown, so the
reasoning is visible in the lead timeline without a new table.

## API

All routes live under `leads_router` and inherit `agency_id` scoping.

- `GET /clients/{client_id}/leads/icp` - profile or 404.
- `PUT /clients/{client_id}/leads/icp` - upsert; validates lists and thresholds.
- `POST /clients/{client_id}/leads/{lead_id}/qualify` - qualify one.
- `POST /clients/{client_id}/leads/qualify` - qualify every lead of the client,
  capped at 500 per call.
- `POST /clients/{client_id}/leads/import` - CSV upload, max 5 MB and 5000 rows.

## UI

Inside the existing leads panel: a collapsible "Ideal customer" form (sectors,
cities, keywords, disqualifiers, size, thresholds, auto-qualify), an "Import
CSV" control, a per-row "Qualify" action, and a "Qualify all" button. The score
column shows the band colour. Copy goes through `dicts/leads.ts` in English and
Spanish.

## Testing

`tests/test_icp_qualification.py`:

- profile upsert and read, scoped by agency (another agency gets 404);
- scoring cases: sector hit, city hit, disqualifier zeroing, missing profile;
- qualification persists `leads.score` and appends an activity;
- bulk qualification covers all leads;
- CSV import creates leads, skips rows with an open lead, reports bad rows;
- auto-qualify honours the flag.

## Rollout

Additive migration. No existing column changes meaning. The deploy follows the
established path: build on the server with `-p fast-livery`, alembic runs on api
start.

## Out of scope

Discovery and enrichment providers, outbound webhooks, per-stage canned replies,
and LLM-written qualification reasons.
