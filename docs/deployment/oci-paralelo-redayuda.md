# OpenLivery en OCI (paralelo a Red Ayuda / Yarumo)

## Veredicto

| Pregunta | Respuesta |
|---|---|
| ¿Mismo **servidor** OCI que Red Ayuda? | **Sí** (`149.130.189.239`) |
| ¿Misma **carpeta** `/opt/red-ayuda`? | **No** |
| ¿Cómo sí? | Hermano bajo `/opt/openlivery`, como `/opt/yarumo` |

## Por qué no dentro de `/opt/red-ayuda`

1. Red Ayuda es un checkout Git + Compose propios (`deploy-production.sh`, `.env`, volúmenes MySQL/media). Meter OpenLivery ahí contaminaría el deploy y el `git status` de producción.
2. OpenLivery trae **otro stack** (Postgres + API + web gateway + WhatsApp bridge). Choca con MySQL/nginx internos de Red Ayuda si se mezclan.
3. El patrón ya usado en este host es **una app = un directorio `/opt/<app>` + un puerto localhost + un `server_name` nginx**:

| App | Disco | Proxy local | Dominio |
|---|---|---|---|
| Red Ayuda | `/opt/red-ayuda` | `127.0.0.1:8081` | `redayuda.r3soluciones.com` |
| Calificación proyectos | `/opt/calificacion-proyectos` | `127.0.0.1:8080` | `proyectos.r3soluciones.com` |
| YARUMO | `/opt/yarumo` | `127.0.0.1:3010` | `yarumo.r3soluciones.com` |
| **Fast Livery** | `/opt/fast-livery` | `127.0.0.1:3020` | `fast-livery.r3soluciones.com` |

## Estado de carga (2026-10-13)

- Código subido a `/opt/openlivery` (~13 MB, sin `.env.docker` ni `node_modules`).
- Marcador: `DEPLOY_SOURCE.txt` (rama `youtube-shorts`, commit `2a8e3a5`).
- **Aún no** se construyeron imágenes ni se levantó Compose (falta `.env.docker` + DNS + espacio).

## Riesgo inmediato: disco

El volumen root del OCI estaba ~**81 %** (~5.8 G libres). Construir `api`+`web`+`whatsapp`+Postgres puede no caber sin limpiar imágenes/backups viejos. Liberar espacio **antes** de `docker compose build`.

## Siguiente (cuando digas)

1. Liberar disco o ampliar volumen.
2. Generar `/opt/openlivery/.env.docker` (secretos nuevos; no reutilizar los de Red Ayuda).
3. Puertos host sugeridos: `WEB_PORT=3020`, `API_PORT=8020`, `DB_PORT=5433`, `BIND_HOST=127.0.0.1`.
4. Vhost nginx + DNS A + certbot para el dominio elegido.
5. `docker compose --env-file .env.docker up -d --build` **sin tocar** `/opt/red-ayuda`.
