# Fast Livery install prompt

Copy everything inside the block into an AI assistant (Claude Code, Codex, Cursor)
running on the target machine. It installs Fast Livery, connects one client to
WhatsApp Cloud and verifies the result. The assistant does the work; the operator
only provides the accounts and the secrets.

---

```
You are installing Fast Livery on this machine. Work in order, stop on the first
failure, and never continue with a broken step.

Rules
- Never invent credentials. If something is missing, ask and stop.
- Never change ENCRYPTION_KEY after the first start: it decrypts every stored secret.
- Always run a step's verification before moving to the next one.

Step 1. Check prerequisites
  docker --version && docker compose version && node --version && python3 --version
Verify: Docker 24+, Node 20+, Python 3.12+.

Step 2. Configure the environment
  ./scripts/generate-docker-env.sh
  $EDITOR .env.docker
Set: FRONTEND_URL (public https URL), API_PORT, WEB_PORT, DB_PORT.
Verify: grep -c "ENCRYPTION_KEY" .env.docker returns 1 and the value is not empty.

Step 3. Start the stack
  docker compose -p fast-livery --env-file .env.docker up -d --build
Verify: docker ps shows db, api, web, whatsapp and proxy, all healthy.
  curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$WEB_PORT/

Step 4. Create the agency account
Open /register in the browser and create the first user. That user owns the agency.
Verify: login succeeds and the panel loads.

Step 5. Register the agency Meta app (once per agency)
Open /settings/meta and save the App ID and App Secret.
Verify: the card reports the app as verified by Meta.

Step 6. Connect one client
Create the client, create its agent, then open the client's Meta wizard
(/clients/<id>/channels/meta-setup) and complete the client steps:
  1. Phone number ID and Messaging Account ID
  2. Permanent token
  3. Webhook: paste the callback URL and verify token shown by the wizard,
     subscribe the messages field, then press the check button
Verify: every client step is green, except the manual ones.

Step 7. Prove the cycle end to end
  python3 scripts/e2e_full.py https://<your-domain>
Verify: the script prints "TODO PASA".

Step 8. Record the result
Write docs/qa/signoffs/<date>-<commit>.md with the QA block from
docs/qa/qa-verifier-agent.md: commit, gate result, pytest count, failures.

If any verification fails, fix that step and re-run it. Do not skip ahead.
```

## What the operator provides

| Item | Where it comes from |
|---|---|
| Public HTTPS URL | Their DNS and reverse proxy |
| App ID and App Secret | Meta for Developers, app settings, basic |
| Phone number ID and Messaging Account ID | Meta app, use case, production configuration |
| Permanent token | Meta app, send message, generate token |

## Why a prompt instead of a shell script

A script cannot ask a human to paste a token it cannot see, nor explain why Meta
rejected a number. The prompt carries the order, the verifications and the stop
conditions; the assistant does the typing.
