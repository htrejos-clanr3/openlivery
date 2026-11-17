# Production deploy runbook (for a terminal agent)

Paste everything below the line into an agent that has shell access to this machine.

---

## Context

- Repo: `/Users/user/Documents/R3/ChatbotApp/Sin título/openlivery` (branch `main`, remote `openlivery-fork`).
- Server: `opc@149.130.189.239`, SSH key `/Users/user/Documents/R3/WyV/OCI-OpenClaw/ssh-key-2026-05-19.key`.
- Deploy directory on the server: `/opt/fast-livery`.
- Compose project name is **`fast-livery`**. Always pass `-p fast-livery`, otherwise compose
  creates a second set of containers and can take the site down.
- Environment file on the server: `/opt/fast-livery/.env.docker`. **Do not print it.** It holds
  the database password, the encryption key and the Meta/Google credentials.
- Images are **not** pulled from GHCR (the publish workflow fails with `permission_denied`).
  Every deploy is built **on the server** from the source tree we send.

## Before deploying

```bash
cd "/Users/user/Documents/R3/ChatbotApp/Sin título/openlivery"
git checkout main
git status --short                 # must be clean
git rev-parse --short HEAD         # take note of this SHA
```

Run the local gate. It must be green before touching production:

```bash
STRICT=1 ./tasks/verify.sh
```

If it fails, stop. Do not deploy a red tree.

## Deploy

```bash
KEY=/Users/user/Documents/R3/WyV/OCI-OpenClaw/ssh-key-2026-05-19.key
REPO="/Users/user/Documents/R3/ChatbotApp/Sin título/openlivery"
SHA=$(cd "$REPO" && git rev-parse HEAD)
SHORT=$(cd "$REPO" && git rev-parse --short HEAD)

cd "$REPO"
git archive --format=tar.gz -o "/tmp/deploy-$SHORT.tar.gz" HEAD

scp -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes "/tmp/deploy-$SHORT.tar.gz" \
  opc@149.130.189.239:/opt/fast-livery/

ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes opc@149.130.189.239 "
  cd /opt/fast-livery &&
  tar xzf deploy-$SHORT.tar.gz &&
  rm -f deploy-$SHORT.tar.gz &&
  sed -i 's/^commit=.*/commit=$SHA/' DEPLOY_SOURCE.txt &&
  sudo docker compose -p fast-livery --env-file .env.docker up -d --build 2>&1 | tail -3
"
```

Build takes several minutes. Do not interrupt it; if the SSH session drops, reconnect and check
`sudo docker ps`.

## Verify

```bash
curl -s -o /dev/null -w 'web: %{http_code}\n' https://fast-livery.r3soluciones.com/login
curl -s -o /dev/null -w 'api: %{http_code}\n' https://fast-livery.r3soluciones.com/api/health
ssh -i "$KEY" opc@149.130.189.239 'grep ^commit /opt/fast-livery/DEPLOY_SOURCE.txt'
```

All three must agree with the SHA deployed. Then run the full gate:

```bash
./scripts/verify_production.sh
```

It must end with `RESULTADO: TODO PASA`. A 200 on the login page alone does not mean the deploy
worked: read the gate output.

## Rollback

```bash
ssh -i "$KEY" opc@149.130.189.239 "cd /opt/fast-livery && sed -i 's/^commit=.*/commit=<previous-sha>/' DEPLOY_SOURCE.txt"
```

and repeat the deploy block with `git checkout <previous-sha>` first. Never roll back the database
by hand; migrations are one-way and the previous image expects the previous schema.

## Rules

- One deploy at a time. Check `sudo docker ps` before starting another.
- Never `tar` over the tree without extracting first: extraction is additive, deletion needs git.
- Never run migrations against production from a laptop; the API container runs
  `alembic upgrade head` on start.
- Never commit or print `.env.docker`, the SSH key, or any secret.
- If the site is down, fix forward: deploy the last known good SHA. Do not experiment on main.
- Report: SHA deployed, gate result, and any container that is not `healthy`.
