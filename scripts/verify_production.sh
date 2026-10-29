#!/usr/bin/env bash
# Production smoke gate. Exit 0 only when every check passes.
# Usage: ./scripts/verify_production.sh [base_url]
set -uo pipefail
BASE="${1:-https://fast-livery.r3soluciones.com}"
KEY="${OCI_KEY:-/Users/user/Documents/R3/WyV/OCI-OpenClaw/ssh-key-2026-05-19.key}"
HOST="${OCI_HOST:-opc@149.130.189.239}"
fail=0
ok()   { printf 'PASS  %s\n' "$1"; }
bad()  { printf 'FAIL  %s\n' "$1"; fail=1; }

code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "$BASE/")
[ "$code" = 200 ] && ok "web / -> $code" || bad "web / -> $code"

for path in /login /manual; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "$BASE$path")
  [ "$code" = 200 ] && ok "$path -> $code" || bad "$path -> $code"
done

code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "$BASE/api/health")
[ "$code" = 200 ] && ok "api /api/health -> 200" || bad "api /api/health -> $code"

code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "$BASE/api/clients")
[ "$code" = 401 ] && ok "api sin sesion -> 401 (aislamiento)" || bad "api sin sesion -> $code"

running=$(ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes "$HOST" \
  'sudo docker ps --format "{{.Names}} {{.Status}}" | grep -c healthy' 2>/dev/null)
[ "${running:-0}" -ge 4 ] && ok "contenedores healthy: $running" || bad "contenedores healthy: ${running:-0}"

head=$(ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes "$HOST" \
  'sudo docker exec openlivery_db psql -U openlivery -d openlivery -tAc "select version_num from alembic_version"' 2>/dev/null | tr -d '[:space:]')
[ -n "$head" ] && ok "alembic head: $head" || bad "alembic head: vacio"

rows=$(ssh -i "$KEY" -o BatchMode=yes -o IdentitiesOnly=yes "$HOST" \
  'sudo docker exec openlivery_db psql -U openlivery -d openlivery -tAc "select count(*) from clients"' 2>/dev/null | tr -d '[:space:]')
[ "${rows:-0}" -ge 1 ] && ok "clientes en base: $rows" || bad "clientes en base: ${rows:-0}"

echo "---"
[ "$fail" = 0 ] && { echo "RESULTADO: TODO PASA"; exit 0; } || { echo "RESULTADO: HAY FALLOS"; exit 1; }
