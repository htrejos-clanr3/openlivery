# ClanR3 × Fast Livery — Manual de configuración y publicación

Fecha: 2026-10-13  
Audience: operador ClanR3 / Hernando  
Stack local actual: Docker Compose en `openlivery/` (API `:8000`, web gateway `:3001`)

Este documento lista **cada paquete/funcionalidad**, qué hay que configurar, dónde se guarda, y qué datos debes aportar antes de activar publicación real (sin mocks).

---

## 0. Estado actual del entorno (lectura)

| Ítem | Valor hoy |
|---|---|
| Stack | Activo (api/web/db/whatsapp/proxy healthy) |
| Rama | `youtube-shorts` |
| `META_MOCK_MODE` | `true` |
| `INSTAGRAM_PUBLISHING_MOCK_MODE` | `true` |
| `LINKEDIN_MOCK_MODE` | `true` |
| `IMAGE_PROVIDER` | `huggingface` (+ `HF_TOKEN` presente) |
| `LINKEDIN_CLIENT_ID` / `SECRET` | no configurados |
| `META_APP_SECRET` | no configurado |
| Publicación real IG/LI/WA | **bloqueada por mocks** (correcto para demos locales) |

Para publicar de verdad hay que: apagar mocks, completar credenciales de proveedor, URL pública (HTTPS) y OAuth callbacks.

---

## 1. Mapa de “paquetes” Fast Livery

Cada fila es un paquete que ClanR3 puede activar. “Listo en código” ≠ “listo en producción”.

| # | Paquete | Qué publica / hace | Listo en código | Requiere para producción |
|---|---|---|---|---|
| P1 | **Núcleo plataforma** | Agencia, clientes, agentes, inbox, portal | Sí | Secretos de sesión + DB |
| P2 | **IA (BYO keys)** | Chat, copy de carrusel, tools | Sí | Claves OpenAI/DeepSeek/etc. en Settings UI |
| P3 | **Imágenes de carrusel** | Genera slides 4:5 | Sí | `IMAGE_PROVIDER` + token/sidecar |
| P4 | **Carruseles + aprobación** | Agencia → portal cliente → aprobado | Sí | Cliente + portal user |
| P5 | **Instagram Content Publishing** | Imagen / carrusel / Reels a IG profesional | Sí (+ mock) | Meta App + OAuth + cuenta pro + URL pública media |
| P6 | **LinkedIn personal MultiImage/texto** | Post personal (texto o multi-imagen) | Sí (+ mock) | LinkedIn App + OAuth + `w_member_social` |
| P7 | **POC A: Carrusel → IG + LI** | Un carrusel a redes seleccionadas | Sí (+ mock) | P5 + P6 reales + gates legales |
| P8 | **WhatsApp Cloud (inbox)** | Mensajes oficiales Meta | Sí | WABA + phone id + token + webhook |
| P9 | **WhatsApp QR (Baileys)** | Vinculación no oficial por QR | Sí | Bridge token; **no** es Cloud API |
| P10 | **WhatsApp campaña / broadcast** (POC B) | Plantillas MARKETING a contactos | **No** (documentado) | Opt-in + templates Meta |
| P11 | **Lead capture / flujos** | Captura y pipelines | Sí | Config por cliente |
| P12 | **Automatizaciones** | Reglas / DeepSeek automations | Sí | Provider keys |
| P13 | **Meta DevTools MCP** | Diagnóstico Graph (no mensajería) | Sí | Token / mock |
| P14 | **Google login** | Login agencia con Google | Opcional | `GOOGLE_OAUTH_CLIENT_ID` |
| P15 | **YouTube Shorts** (Fase 2) | Video privado | **Solo diseño** | Google OAuth YouTube + fal/Replicate |
| P16 | **Imágenes Docker (GHCR)** | Publicar `api`/`web`/`whatsapp` | CI en `main`/tags | Permisos `packages:write` en GitHub |

---

## 2. Dónde se guarda cada cosa

| Tipo de dato | Dónde | Notas |
|---|---|---|
| Secretos de plataforma (DB, cookies, Meta App, LinkedIn App, HF) | `.env.docker` (host) → env del contenedor | **Nunca** al repo. Respaldo en gestor de secretos |
| Claves de IA por agencia | UI **Configuración** (cifradas con `ENCRYPTION_KEY`) | Si cambias `ENCRYPTION_KEY`, se invalidan |
| Canales por cliente (IG/LI/WA tokens) | PostgreSQL cifrado | Por tenant/cliente |
| Consentimientos legales A/B/F | Tabla `legal_acceptances` | Auditoría |
| Carruseles / publicaciones | PostgreSQL + media | IDs de proveedor en `publish_results` |
| Imágenes de contenedor | `ghcr.io/<owner>/openlivery-{api,web,whatsapp}` | Workflow `publish-images.yml` |

Regla: **no pegues secretos en este markdown**. Rellena el cuestionario (sección 8) por canal privado / 1Password / `.env.docker` local.

---

## 3. Opciones por paquete (detalle)

### P1 — Núcleo plataforma

| Variable / dato | Obligatoriedad | Valores / opciones | Efecto |
|---|---|---|---|
| `POSTGRES_*` | Obligatoria | user/db/password alfanumérico | DB principal |
| `SECRET_KEY` | Obligatoria | ≥32 chars aleatorios | Sesiones |
| `ENCRYPTION_KEY` | Obligatoria | ≥32 chars; **no rotar a la ligera** | Cifrado de tokens |
| `FRONTEND_URL` | Obligatoria | Origen público del gateway | CORS + redirects OAuth |
| `COOKIE_SECURE` | Prod HTTPS | `true` / `false` | Cookie solo TLS |
| `COOKIE_SAMESITE` | Según topología | `lax` \| `none` | Cross-site necesita `none`+secure |
| `ACCESS_TOKEN_MINUTES` | Opcional | default ~7 días | Vida de sesión |
| `API_PORT` / `WEB_PORT` / `DB_PORT` | Local | hoy `8000` / `3001` / `5432` | Puertos host |
| `BIND_HOST` | Local/servidor | `127.0.0.1` \| `0.0.0.0` | Exposición |

**Datos a guardar:** host público definitivo de ClanR3 (ej. `https://app.clanr3.com`), política de cookies, backup de `.env.docker`.

---

### P2 — IA (por agencia, en UI)

No van en `.env.docker` (salvo providers de imagen globales).

| Dato | Dónde se pega | Opciones |
|---|---|---|
| OpenAI API key | Configuración → proveedores | Modelos chat / (si `IMAGE_PROVIDER=openai`) imágenes |
| DeepSeek / Moonshot / otros OpenAI-compatible | Mismo sitio | Base URL + model |
| Modelo por agente | Ficha del agente | Debe coincidir con un proveedor configurado |

**Datos a guardar:** qué proveedores usará ClanR3 en producción y límites de presupuesto.

---

### P3 — Imágenes de carrusel

| Variable | Opciones | Cuándo |
|---|---|---|
| `IMAGE_PROVIDER` | `openai` \| `huggingface` \| `flux` \| `ollama` \| `placeholder` | Producción real: `openai` o `huggingface`; demos: `placeholder` |
| `IMAGE_SIZE` | p.ej. `1024x1536` | Ratio 4:5 IG |
| `HF_TOKEN` | token HF | Si provider = huggingface |
| `HF_IMAGE_MODEL` | default FLUX.1-schnell | Modelo Hub |
| `HF_IMAGE_PROVIDER` | vacío o pin (`fal-ai`, …) | Opcional |
| `FLUX_BASE_URL` / `OLLAMA_BASE_URL` | sidecar local | Solo si provider local |

Hoy ClanR3 local: `huggingface`.

---

### P4 — Carruseles + portal

| Dato | Dónde |
|---|---|
| Cliente ClanR3 (nombre, industria, contexto, brand) | Clientes |
| Usuario portal (email/password del dueño del cliente) | Portal users |
| Brief / slide count / playbook | Carrusel |

Gates: aprobación agencia → review portal → `approved` → publicar.

---

### P5 — Instagram Content Publishing

| Variable / dato | Obligatoriedad producción | Notas |
|---|---|---|
| `META_APP_ID` | Obligatoria | App Meta de la plataforma |
| `META_APP_SECRET` | Obligatoria | App settings → Basic |
| `META_GRAPH_BASE_URL` | Opcional | default `v23.0` |
| `INSTAGRAM_PUBLISHING_MOCK_MODE` | `false` en prod | Hoy `true` |
| `INSTAGRAM_OAUTH_REDIRECT_PATH` | default | Registrar callback exacto |
| `BACKEND_URL` / origen público | Obligatoria | Meta descarga media firmada |
| Cuenta IG Professional + Page | Por cliente | OAuth en UI del cliente |
| Scopes | App Review en prod | `instagram_content_publish`, etc. |

Callback típico:

```text
{FRONTEND_URL}/api/instagram/oauth/callback
```

Doc: [`instagram-publishing.md`](./instagram-publishing.md).

---

### P6 — LinkedIn personal

| Variable / dato | Obligatoriedad producción | Notas |
|---|---|---|
| `LINKEDIN_CLIENT_ID` | Obligatoria | App LinkedIn Developers |
| `LINKEDIN_CLIENT_SECRET` | Obligatoria | |
| `LINKEDIN_OAUTH_REDIRECT_PATH` | default | Exact match |
| `LINKEDIN_API_VERSION` | default `202601` | Header API |
| `LINKEDIN_MOCK_MODE` | `false` en prod | Hoy `true` |
| Productos en la app | Obligatorios | OpenID Connect + Share on LinkedIn |
| Scope | `w_member_social` | Perfiles personales |

Callback:

```text
{FRONTEND_URL}/api/linkedin/oauth/callback
```

Doc: [`linkedin.md`](./linkedin.md).  
Gate B: modal legal antes de OAuth (ya en código).

---

### P7 — POC A multi-red (carrusel → IG + LI)

| Opción | Comportamiento |
|---|---|
| Destinos | Lista no vacía; `[]` → error |
| `human_approved` + `reviewed_exact_content` | Deben ser `true` explícitos (default `false`) |
| Fallo parcial | Conserva éxitos; estado reintentable; UI por red |
| Mock | Con mocks ON publica IDs `mock_*` / `urn:li:share:mock-*` |

Requiere P4 + P5 + P6.

---

### P8 — WhatsApp Cloud (inbox / servicio)

| Dato | Ámbito | Notas |
|---|---|---|
| Phone Number ID | Por cliente (Advanced) | No es el `+57…` |
| WABA ID | Por cliente | |
| Access token permanente | Por cliente | System user |
| App Secret | Por cliente o plataforma | |
| Webhook URL + verify token | Por canal | Únicos por cliente |
| `META_APP_ID/SECRET` + `META_WHATSAPP_CONFIG_ID` | Solo Embedded Signup plataforma | Opcional |
| `META_MOCK_MODE` | `false` en prod | Hoy `true` |

Doc: [`whatsapp-meta-setup.md`](./whatsapp-meta-setup.md).

---

### P9 — WhatsApp QR (Baileys)

| Variable | Notas |
|---|---|
| `WHATSAPP_BRIDGE_TOKEN` | Mismo valor API ↔ bridge |
| `WHATSAPP_LOG_LEVEL` | `silent` recomendado |

No sustituye Cloud API. No sirve para plantillas MARKETING oficiales.

---

### P10 — WhatsApp campaña (POC B) — aún no implementar

Requiere lista de contactos + opt-in + template Meta carousel. **Fuera del alcance de activación inmediata.**

---

### P11–P14 — Lead capture, automations, Meta MCP, Google

| Paquete | Claves / opciones |
|---|---|
| Lead capture | Flags/settings por cliente (ver `docs/lead-capture.md`) |
| Automatizaciones | Provider AI + reglas UI |
| Meta DevTools MCP | `META_DEVTOOLS_MCP_*` (diagnóstico) |
| Google login | `GOOGLE_OAUTH_CLIENT_ID` |

---

### P15 — YouTube Shorts

Solo diseño (`docs/plans/2026-10-05-youtube-shorts-design.md`). No hay env productiva aún (`YOUTUBE_MOCK_MODE`, Google OAuth YouTube).

---

### P16 — Publicar imágenes Docker (paquetes GHCR)

Workflow: `.github/workflows/publish-images.yml`

| Trigger | Qué publica |
|---|---|
| Push a `main` | `ghcr.io/<owner>/openlivery-{api,web,whatsapp}:latest` |
| Tag `v*` | Imágenes versionadas |
| `workflow_dispatch` | Manual |

**Datos a guardar:** owner GHCR (`htrejos-clanr3`), si ClanR3 despliega desde `fast-livery` o fork, y si el servidor hace `docker compose pull`.

Para publicar paquetes hace falta merge a `main` (o tag) con CI verde — hoy el trabajo vive en `youtube-shorts` / PR #1.

---

## 4. Legal (obligatorio en todo publish)

| Gate | Cuándo | Qué se guarda |
|---|---|---|
| A — Platform ToS/Privacy | Registro / antes de canales | Versiones `legal_*` |
| B — Channel connect | Antes de OAuth IG/LI/WA | Admin + no-password (+ AI disclosure IG) |
| F — Human publish | Antes de publicar | `human_approved` + `reviewed_exact_content` |

URLs actuales: `LEGAL_TOS_URL` / `LEGAL_PRIVACY_URL` (defaults apuntan al repo).

---

## 5. Checklist de activación producción (orden)

1. Definir dominio HTTPS ClanR3 → `FRONTEND_URL`, `COOKIE_SECURE=true`.
2. Completar Meta App (ID + Secret) y callbacks IG/WA.
3. Completar LinkedIn App (ID + Secret) y callback.
4. Poner `*_MOCK_MODE=false` (Meta/IG/LI).
5. Elegir `IMAGE_PROVIDER` real y token.
6. Rebuild: `docker compose --env-file .env.docker up -d --build`.
7. Crear agencia ClanR3 + cliente(s) + agentes + claves IA en UI.
8. Conectar IG + LI (consent B) por cliente.
9. Carrusel → portal aprueba → publish con destinos + gate F.
10. (Opcional) WA Cloud BYO por cliente.
11. Merge PR → `main` si se quieren imágenes GHCR actualizadas.

---

## 6. Matriz mock vs real

| Modo | Variables | Uso |
|---|---|---|
| Demo / CI local | `META_MOCK_MODE=true`, `INSTAGRAM_PUBLISHING_MOCK_MODE=true`, `LINKEDIN_MOCK_MODE=true` | E2E sin cuentas reales |
| Producción ClanR3 | las tres en `false` + credenciales | Publicación real |

No mezclar: mock ON + credenciales reales engaña al operador (parece conectado pero no llama al proveedor).

---

## 7. Manual operativo corto (UI)

1. **Login** → agencia.
2. **Clientes** → crear “ClanR3” (o cliente final).
3. **Agentes** → instrucciones + modelo + clave en Configuración.
4. **Canales** → Instagram / LinkedIn / WhatsApp Cloud (guía en página si OAuth no está listo).
5. **Carruseles** → generar → aprobar slides → portal → **Publicar en redes**.
6. **Playground → Manual** → lecciones 1–10 del producto.

URL local: http://127.0.0.1:3001/

---

## 8. Cuestionario — información que debes aportar

Copia y responde. Con esto se rellena `.env.docker` y se crean los clientes sin adivinar.

### A. Hosting / dominio

- [ ] URL pública final (HTTPS): _______________________
- [ ] ¿Solo local por ahora? (sí/no): _______
- [ ] ¿Exponer API fuera del gateway? (sí/no): _______

### B. Meta (WhatsApp Cloud + Instagram)

- [ ] Meta App ID: _______
- [ ] Meta App Secret: _(enviar por canal seguro)_
- [ ] ¿Embedded Signup WhatsApp? (sí/no) → Config ID: _______
- [ ] Redirects autorizados en la App (lista): _______
- [ ] ¿App Review listo o solo Development?: _______

### C. Instagram del/los cliente(s)

- [ ] Cuenta IG Professional + Page asociada (handle): _______
- [ ] ¿Quién autoriza OAuth (admin de la Page)?: _______

### D. LinkedIn

- [ ] LinkedIn Client ID: _______
- [ ] LinkedIn Client Secret: _(canal seguro)_
- [ ] Callback registrado exacto: _______
- [ ] Perfil personal a conectar (URL): _______

### E. WhatsApp

- [ ] ¿Cloud API (oficial) o QR (Baileys) o ambos?: _______
- [ ] Si Cloud: Phone Number ID / WABA / token permanente: _(seguro)_
- [ ] Número de prueba: _______

### F. Imágenes / IA

- [ ] `IMAGE_PROVIDER` deseado: openai / huggingface / flux / ollama / placeholder
- [ ] HF token / OpenAI key / otros: _(seguro)_
- [ ] Proveedores de chat para agentes: _______

### G. Agencia ClanR3 en la app

- [ ] Nombre de agencia: _______
- [ ] Admin email / password inicial: _(seguro)_
- [ ] Clientes a crear (nombre, industria, contexto, brand colors/logo): _______
- [ ] Usuarios portal por cliente: _______

### H. Paquetes Docker / deploy

- [ ] ¿Publicar imágenes a GHCR desde `main`? (sí/no): _______
- [ ] Servidor destino (si aplica) y método (`compose pull` / build): _______

### I. Alcance de activación ahora

Marca qué debe quedar **real** en esta pasada:

- [ ] P5 Instagram real  
- [ ] P6 LinkedIn real  
- [ ] P7 Carrusel multi-red real  
- [ ] P8 WhatsApp Cloud  
- [ ] P9 WhatsApp QR  
- [ ] P3 Imágenes no-placeholder  
- [ ] P16 Push imágenes Docker  
- [ ] Solo dejar mocks + manual (sin prod)

---

## 9. Referencias

- Self-hosting: [`self-hosting.md`](./self-hosting.md)
- Instagram: [`instagram-publishing.md`](./instagram-publishing.md)
- LinkedIn: [`linkedin.md`](./linkedin.md)
- WhatsApp Meta: [`whatsapp-meta-setup.md`](./whatsapp-meta-setup.md)
- Studio fases: [`plans/2026-10-05-content-studio-phased.md`](./plans/2026-10-05-content-studio-phased.md)
- Legal: [`legal/`](./legal/)
- E2E smoke: `scripts/run_e2e_system.py`
- PR POC A: https://github.com/htrejos-clanr3/fast-livery/pull/1
