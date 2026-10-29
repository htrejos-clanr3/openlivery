# Weekly recurrence check

Incident: a `RUN` that downloaded and executed a binary from `43.228.157.68` was
injected into `apps/api/Dockerfile` in commit `4af80dc` (28 Aug 2026), pushed to
the remote's `main` from a git client authenticated with an OAuth app token.
It was never executed on the server and never reached the deployed tree.

## Every week, run

```
./scripts/security_check.sh
```

Exit code 0 and `SIN INDICIOS DE REINCIDENCIA` means nothing reappeared.

## What it checks

1. The known markers (`43.228.157.68`, `/tmp/.svc`, `ipscan --source`) are absent
   from the whole fetched history.
2. No Dockerfile downloads and executes a remote binary.
3. Local `main` and remote `main` are the same commit.
4. How many commits in the last 30 days are unsigned, which is the signature of
   an agent pushing with an OAuth token.

## If it fails

1. Do not pull, do not build. The tree is contaminated.
2. Identify the branch and the author of the offending commit.
3. Revoke the OAuth app that could have pushed it (see Settings > Applications).
4. Re-run the check after rewriting the branch.

## Manual steps that the script cannot cover

- Rotating the token stored in the macOS Keychain.
- Reviewing installed GitHub Apps and their scopes.
- Deleting container images published from a contaminated commit.
- Keeping branch protection on `main` with no bypass.

## Limits, stated plainly

The script detects the known payload and the known technique. It does not prove
the absence of a different backdoor. The real control is branch protection plus
apps with read-only access; the script only catches a repeat of this one.
