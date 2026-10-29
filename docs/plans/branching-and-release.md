# Branching and release rules

## The model

| Ref | Meaning | Who can push |
|---|---|---|
| `prod` | Exactly what is running in production | Nobody directly: it only moves with a verified release |
| tag `vX.Y.Z` | Immutable snapshot of a released state | Nobody: tags are never moved |
| `main` | Integration trunk, always deployable | Pull request only |
| `feature/*` | Work in progress | Its author |

Production runs a commit that has a tag. If it is not tagged, it is not a release.

## Before deploying anything

1. `./scripts/verify_production.sh` green on the target.
2. `pytest -q`, `npm run lint`, `npx tsc --noEmit` green.
3. Migration dry run against a clone of the production dump.
4. Tag the candidate: `git tag -a v1.1.0 -m "..."`.
5. Deploy, then re-run the gate and record the sign-off in `docs/qa/signoffs/`.

## Rollback is a tag away

```
git checkout v1.0.0
git archive --format=tar.gz -o /tmp/rollback.tar.gz HEAD
# extract into a CLEAN directory on the server, then compose up --build
```

Never extract a tarball over an existing tree: leftover files from the previous
version (a migration, a compose file) are exactly what broke production on
2026-10-28.

## Why not "leave a branch in production while testing"

Deploying a branch to the same stack is not a staging environment: it shares the
database, the port and the domain, so a broken branch takes production down with
it.

A branch can feed staging, and staging needs its own:

- compose project name (`-p fast-livery-staging`)
- port (`WEB_PORT=3021`)
- database, restored from the production dump, never shared
- domain or subdomain

Only when the gate is green on staging does the commit reach `prod`.

## Next tag

`v1.1.0` when the marketing foundation (post_pieces, approval_links,
client_phones, provider_connections) is proven against a clone and deployed.
