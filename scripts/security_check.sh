#!/usr/bin/env bash
# Recurrence check for the Aug 2026 Dockerfile injection.
# Run weekly: ./scripts/security_check.sh
set -uo pipefail
REMOTE="${REMOTE:-openlivery-fork}"
fail=0
ok()  { printf 'PASS  %s\n' "$1"; }
bad() { printf 'FAIL  %s\n' "$1"; fail=1; }

git fetch -q "$REMOTE" '+refs/heads/*:refs/remotes/'"$REMOTE"'/*' --tags 2>/dev/null

# 1. Known payload markers anywhere in the fetched history.
for marker in "43.228.157.68" "/tmp/.svc" "ipscan --source"; do
  n=$(git log --all -p --format="" 2>/dev/null | grep -c -- "$marker")
  [ "$n" = 0 ] && ok "historial sin '$marker'" || bad "historial contiene '$marker' ($n lineas)"
done

# 2. Dockerfiles must not download and execute remote binaries.
hits=$(git grep -nE "curl .*\|.*(sh|bash)|wget .*-O.*/tmp|chmod \+x /tmp" $(git for-each-ref --format='%(refname)' "refs/remotes/$REMOTE") -- '*Dockerfile*' 2>/dev/null | wc -l | tr -d ' ')
[ "$hits" = 0 ] && ok "Dockerfiles sin descargas ejecutables" || bad "Dockerfiles con descarga+ejecucion ($hits)"

# 3. Main must match the reviewed local commit.
ahead=$(git rev-list --count "refs/remotes/$REMOTE/main..main" 2>/dev/null)
behind=$(git rev-list --count "main..refs/remotes/$REMOTE/main" 2>/dev/null)
[ "$ahead" = 0 ] && [ "$behind" = 0 ] && ok "main sincronizado con el remoto" \
  || bad "main divergente (local adelante: $ahead, remoto adelante: $behind)"

# 4. Unsigned commits on main in the last 30 days.
unsigned=$(git log --since="30 days ago" --format="%G?" "refs/remotes/$REMOTE/main" 2>/dev/null | grep -c "^N$")
ok "commits sin firma en 30 dias: $unsigned (revisar si son de agentes)"

echo "---"
[ "$fail" = 0 ] && { echo "RESULTADO: SIN INDICIOS DE REINCIDENCIA"; exit 0; } || { echo "RESULTADO: REVISAR"; exit 1; }
