# Unified channel connection: WhatsApp and Instagram by OAuth

Decision: OAuth is the main path for both channels; the manual credentials form
stays only as an escape hatch for a client that brings its own Meta app.

Instagram requires a Facebook Page linked to the Instagram Business account. No
Page, no publishing: the wizard blocks at that step instead of failing later.

## Why not copy Equipia's model as is

Equipia stores per-tenant `app_secret`, `verify_token` and `access_token` typed by
an operator. It has no Instagram support and no OAuth. What we take from it is the
secret-reference pattern: secrets are stored encrypted and referenced, never in
clear text, and the UI shows references instead of values.

## Agency, once

| Step | Action | Verification |
|---|---|---|
| 1 | Connect with Meta (owner OAuth) | Meta returns the app token |
| 2 | Store App ID and secret encrypted | Meta confirms the pair |
| 3 | Select permissions per channel | Meta lists the granted scopes |

The manual form at /settings/meta remains for the escape hatch.

## Per client

| Step | WhatsApp | Instagram |
|---|---|---|
| 4 | Connect with Meta | Connect with Instagram |
| 5 | Pick WABA and phone number | Pick Page and Instagram account |
| 6 | Webhook: messages | Webhook: messages and comments |
| 7 | Test message | Test publication |

## Blocked by Meta, not by code

Instagram publishing and reading messages need approved permissions:
instagram_basic, instagram_content_publish, instagram_manage_messages,
instagram_manage_comments, pages_show_list, pages_manage_posts,
business_management.

Until they are approved the wizard can be built and will show amber on those
steps, for reasons outside our code.

## Work breakdown

| Item | Days |
|---|---|
| Agency OAuth | 3-4 |
| Instagram wizard, same eight steps | 5-7 |
| Single wizard component for both channels | 2-3 |
| Secret references in the model | 2 |

Total: 12-16 days.

## Order

1. Agency OAuth, because both wizards depend on it.
2. Instagram wizard reusing the WhatsApp component.
3. Secret references, which touch the model and must land before more providers.
