# Deploy workflow

`.github/workflows/deploy-production.yml` builds the stack **on the server** and restarts
compose. It does not pull from GHCR, so a failed package publish cannot block a deployment.

## Secrets to create once

Repository → Settings → Secrets and variables → Actions → **New repository secret**:

| Secret | Value |
|---|---|
| `DEPLOY_HOST` | `149.130.189.239` |
| `DEPLOY_USER` | `opc` |
| `DEPLOY_SSH_KEY` | the private key, full text including the BEGIN/END lines |
| `DEPLOY_PATH` | `/opt/fast-livery` (optional; that is the default) |

The public key must already be in `~/.ssh/authorized_keys` on the server for that user, and the
user needs passwordless `sudo` for `docker compose` (it already is).

## When it runs

- Every push to `main`.
- Manually from the Actions tab, with the commit you want.

Never runs twice at the same time: `concurrency` keeps one deployment in flight and queues the next.

## What it does

1. Packs the commit into `deploy.tar.gz`.
2. Copies it to the deploy directory.
3. Extracts it and writes the commit SHA into `DEPLOY_SOURCE.txt`.
4. Runs `docker compose -p fast-livery --env-file .env.docker up -d --build`.
5. Waits for `/api/health` to answer 200 and reads the login page.
6. Prints any container that is not healthy.

## What it does not do

- It does not run tests. `STRICT=1 ./tasks/verify.sh` stays a local or CI check before merging.
- It does not roll back. To revert, re-run the workflow on the previous commit
  (`gh workflow run deploy-production.yml --ref main` after reverting the commit).
- It does not touch the database: the API container runs `alembic upgrade head` on start.

## GHCR publish still failing

`publish-images.yml` fails with `permission_denied: write_package` because the workflow token
cannot write packages. Fix in Settings → Actions → General → **Workflow permissions**:
*Read and write permissions*, and in the package settings allow the repository to write.
It is not required for deploying: the deploy workflow builds on the server.
