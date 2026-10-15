# Diseño — Carruseles tipo Pomelli (Fast Livery)

Fecha: 2026-08-24  
Fuente de referencia UX: Google Pomelli (generar → revisar → decidir → publicar)

## Decisiones de producto

| Tema | Decisión |
| --- | --- |
| Aprobación | Por slide **y** set final |
| Roles | Agencia genera → cliente aprueba (portal) |
| Generación | Texto + imágenes + DNA de marca |
| Publicación | Programar vía Instagram (Meta) — fase 2 si canal no listo |
| i18n | Todo el front vía `t()` ES/EN (default ES) |
| Auth | Email/clave **OR** Google (independientes; cualquiera basta) |
| Recuperar clave | Siempre por email; si solo Google → Continuar con Google **o** crear clave tras verificar email |

## Flujo

```
Agencia: DNA → brief → generate → agency approve slides → submit review
Cliente portal: approve/reject slides + comment → approve/reject set
Agencia: schedule IG → published | failed
```

Estados carrusel: `draft` → `in_review` → `approved` | `rejected` → `scheduled` → `published` | `failed`  
Estados slide: `pending` → `agency_ok` → `client_ok` | `rejected`

## Modelo (resumen)

- `clients`: brand DNA (colores, voz, logo binario)
- `portal_users`: N usuarios por cliente; password y/o Google
- `oauth_accounts`: vínculo Google independiente
- `password_reset_tokens`: forgot / set-password
- `carousels` + `carousel_slides` + `carousel_events`

## Fases de implementación

1. **MVP auth + portal multi-user** — Google OR password, forgot/set password, i18n auth
2. **MVP carousels** — DNA, generate (layout+copy+image), agency/portal approval, export
3. **Schedule IG** — endpoint + UI; Meta API cuando canal Instagram esté disponible (stub seguro si no)

## Estado de implementación (2026-08-25)

Entregado en código:

- Migración `0018_carousels_pomelli`
- Auth agencia/portal: password OR Google, forgot/set password
- DNA de marca en cliente + portal users invitados
- API carousels + aprobación slide/set + schedule stub IG
- UI agencia `/carousels`, portal `/portal/[slug]/carousels`
- i18n ES/EN (`dicts/carousels.ts` + auth keys)
- Tests: `tests/test_carousels.py` (2 passed)

Pendiente operativo:

- Configurar `GOOGLE_OAUTH_CLIENT_ID` en `.env.docker`
- SMTP real para forgot-password (hoy token expuesto solo si `AUTH_EXPOSE_RESET_TOKEN=true`)
- Conectar Meta Instagram para publicar de verdad (hoy `scheduled` con nota pending)
