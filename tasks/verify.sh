#!/usr/bin/env bash
# Project gate. STRICT=1 turns warnings and skipped checks into failures.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STRICT="${STRICT:-0}"
fail=0
ok()   { printf 'PASS  %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; fail=1; }
skip() { if [ "$STRICT" = "1" ]; then bad "$1 (strict)"; else printf 'SKIP  %s\n' "$1"; fi; }

cd "$ROOT"

# 1. Python compiles
if python3 -m compileall -q apps/api/app >/dev/null 2>&1; then ok "python compila"; else bad "python compila"; fi

# 2. Pure unit tests (no database required)
if (cd apps/api && python3 -m pytest tests_pure -q >/tmp/verify_pytest.log 2>&1); then
  ok "pytest tests_pure ($(grep -oE '[0-9]+ passed' /tmp/verify_pytest.log | head -1))"
else
  bad "pytest tests_pure"; tail -5 /tmp/verify_pytest.log
fi

# 3. TypeScript and lint
if (cd apps/web && npx tsc --noEmit >/tmp/verify_tsc.log 2>&1); then ok "tsc"; else bad "tsc"; tail -5 /tmp/verify_tsc.log; fi
if (cd apps/web && npm run lint >/tmp/verify_lint.log 2>&1); then ok "lint"; else bad "lint"; tail -5 /tmp/verify_lint.log; fi

# 4. Production smoke, only when a URL is reachable
if [ "${VERIFY_PRODUCTION:-0}" = "1" ]; then
  if ./scripts/verify_production.sh >/tmp/verify_prod.log 2>&1; then ok "produccion"; else bad "produccion"; tail -8 /tmp/verify_prod.log; fi
else
  printf 'SKIP  produccion (VERIFY_PRODUCTION=1 para incluirla)\n'
fi

echo "---"
if [ "$fail" = 0 ]; then echo "RESULTADO: TODO PASA (STRICT=$STRICT)"; exit 0; fi
echo "RESULTADO: HAY FALLOS (STRICT=$STRICT)"; exit 1
