# Commerce account linking: requirements, automation and validations

Goal: a new client links their store with the least friction. This note covers,
per platform, what account is needed, how much can be automated, and what we can
validate automatically before asking a human to approve anything.

Status of the facts: Google Merchant Center and Meta Commerce flows are public
and documented. ChatGPT Ads is an access-gated program; its account and API
shape are **assumed** and must be confirmed in the console before building.
Anything marked "verify" is a task, not an established fact.

## Summary

| Platform | Account needed | Access type | How much is automated | Human approval |
|---|---|---|---|---|
| Google (Merchant Center / UCP) | Google account, Merchant Center account, verified domain, shipping and returns | **OAuth 2.0** (Google Identity), Content API for Shopping | Account creation for the *client* can be delegated through a multi-client account; linking is OAuth + a few confirmations | Domain verification (often automatic via Search Console), Google's program approval |
| Meta (Instagram Shopping) | Facebook account, Business Manager, Commerce account, catalog, Page, Instagram professional account | **OAuth 2.0** (Facebook Login for Business) + Graph API | OAuth gives catalog, IG account and domain status in one flow; catalog and feed creation are API calls | Commerce eligibility review by Meta |
| ChatGPT Ads | OpenAI organization, ad account, billing, country enabled | **API key or account id** (verify) | Unknown until documented; assume manual onboarding plus a stored credential | OpenAI allowlist |

## Google

**What the client needs.** A Google account that owns (or can access) a Merchant
Center account; the store domain verified in that account; shipping and returns
policy; a product feed. For an agency managing many clients, a **multi-client
account** lets one login administer many Merchant Center accounts, which is the
single biggest friction reduction: the agency authorizes once per client, not
once per platform.

**How automated.** OAuth 2.0 with the Content API scope. From the token we can
list the merchant accounts the user can access, read account status, verify
whether the domain is already verified, and push the product feed. What cannot be
automated is Google approving the account for UCP.

**Pre-flight checks we run on connect (all read-only):**

1. Token obtained and scopes granted.
2. At least one Merchant Center account visible; otherwise deep link to create one.
3. Domain verified for the selected account (status read from the API).
4. Shipping and returns declared; if empty, link to that section.
5. Feed accepted: push one sample product and read back the result.

## Meta / Instagram Shopping

**What the client needs.** A Facebook account, a Business Manager, a Commerce
account, a catalog, a Facebook Page and an Instagram professional account linked
to that Page. Domain verification in Business Manager. Meta then reviews commerce
eligibility.

**How automated.** Facebook Login for Business with explicit scopes. In one flow
we get the business, its pages, the linked Instagram account, the catalogs and
domain verification status; catalog and feed creation are Graph API calls.

**Pre-flight checks we run on connect (all read-only):**

1. Token valid; requested scopes actually granted (Meta returns granted scopes,
   so we must compare, not assume).
2. Business Manager present and the user is an admin.
3. Instagram professional account linked to a Page.
4. Catalog present; if not, offer to create one.
5. Domain verification status; if not verified, show the exact DNS record to add.
6. Catalog diagnostics: product count, rejected items and reasons.

## ChatGPT Ads

**What the client needs.** An OpenAI organization for ads, billing set up, the
country enabled, and access to the program. What we do not know yet: whether the
API exists, whether it is key or OAuth based, and what the ad-account model is.

**Proposed handling.** Treat it as a **credential field plus account id**, behind
a flag, with a capability probe: on save, call a cheap read endpoint. If the
program is unavailable, show "programa no disponible para este país" instead of a
broken form.

**Pre-flight checks.** Key present, account id present, probe returns the account
and its status, country listed as supported.

## The linking flow we should build

1. **One screen, three cards.** "Conectar comercio" inside the client, with
   Google, Meta and ChatGPT Ads. Each card states the account it needs and an
   estimated time.
2. **OAuth first, files second.** Google and Meta are OAuth buttons with no
   fields to paste. The file feed remains the fallback when a client cannot grant
   OAuth.
3. **Read-only first.** Ask for read scopes and validation before write scopes.
   A client can link, see diagnostics and stop; publishing is a second act.
4. **Automatic checklist.** On connect, run the checks above and show a green,
   amber or red item per requirement, each with a deep link to the provider
   screen that fixes it.
5. **Delegated access.** For agencies, prefer connecting once at agency level and
   then selecting the client's merchant/business asset, instead of one full OAuth
   per client.
6. **Status model, not booleans.** `not_connected`, `authorizing`, `read_only`,
   `verified`, `live`, `error`. The UI always says what the next step is.
7. **Never store what we do not need.** Encrypted tokens, account ids, granted
   scopes and last error; no credentials in logs.

## What we can promise and what we cannot

- We can automate: authorization, account discovery, catalog creation, feed
  generation, diagnostics and re-checks.
- We cannot automate: Google's program approval, Meta's commerce eligibility
  review, OpenAI's allowlist, and country availability.
- So the honest promise to a client is: "conectas en minutos y te decimos
  exactamente qué falta", not "queda publicado al instante".

## Before building

Confirm in each console: the exact OAuth scopes, the endpoints for account,
catalog and diagnostics, the multi-client account behaviour, and the OpenAI Ads
API. Until then, only the catalog, import and validation phases are safe to
implement.
