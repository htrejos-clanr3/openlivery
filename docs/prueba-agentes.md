# WhatsApp webhook: three checks

The Cloud API webhook is the only door for client messages. These three checks
prove it accepts real events, rejects foreign ones and never loses a message.
Run them in this order; each one assumes the previous passed.

## Check 1: a signed event is accepted

Send a payload signed with the agency app secret to:

```
POST /api/public/whatsapp-cloud/channels/<channel_id>/webhook
X-Hub-Signature-256: sha256=<hmac of the raw body>
```

Expected: **200** and a row in `messages` with the sender's phone as
`external_chat_id`. If it answers 403, the signature check failed: the channel
secret and the agency secret do not match the one used to sign.

## Check 2: an event for another number is rejected

Same call, but with `metadata.phone_number_id` set to a number that does not
belong to the channel.

Expected: **200** and **no new rows**. The handler answers 200 on purpose (Meta
retries non-2xx), but it must skip the event. If a conversation appears under the
wrong client, tenant isolation is broken.

## Check 3: a retry does not duplicate

Send the same payload twice, with the same `messages[0].id`.

Expected: one row in `messages` and one conversation. The external message id is
the idempotency key; a second insert must be ignored, not stored again.

## How to run them

`scripts/e2e_full.py` covers check 1 as part of the full journey. Checks 2 and 3
are the ones worth automating next: they are the two that protect the tenant and
the inbox.

## What to record

For each check: timestamp, channel id, HTTP status, and the row counts before and
after. A check without numbers is an opinion.
