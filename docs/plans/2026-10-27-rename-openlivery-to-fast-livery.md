# Rename openlivery to Fast Livery

The product name is **Fast Livery**. The codebase still carries `openlivery` in
38 files across three layers that must be renamed in order, because renaming a
lower layer without the one above it breaks a running deployment.

## Layer 1 - prose (done)

`README.md` and `CHANGELOG.md` already say Fast Livery. No runtime effect.

## Layer 2 - code identifiers (no downtime)

- `apps/web/types/index.ts`, scripts and comments: text only.
- `docker-compose.yml`: image names (`ghcr.io/.../openlivery-api` becomes
  `fast-livery-api`) and the `name:` field.
- `.github/workflows/publish-images.yml`: image tags.
- Container names (`openlivery_api`, `openlivery_web`, `openlivery_db`).

Verification: `docker compose config` renders, images build, containers start
under the new names, health endpoints return 200.

## Layer 3 - database and server (needs a window)

Renaming the database user or name requires a backup and a maintenance window.

1. `pg_dump -Fc` of the production database, stored off-host.
2. Stop the stack.
3. Create the new role and database; restore the dump.
4. Point `DATABASE_URL` at the new names.
5. Start the stack and verify: migrations at head, one inbound message stored,
   one reply sent.
6. Keep the old database untouched for seven days.

Rollback: restore `DATABASE_URL` to the old names and start the previous image.

## Never rename

`ENCRYPTION_KEY`. Changing it makes every stored secret unreadable: AI keys,
WhatsApp tokens, the agency Meta app secret and session state.
