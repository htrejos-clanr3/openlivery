# Conexiones transparentes (plataforma) + validación legal por paso

**Repo:** `htrejos-clanr3/fast-livery`  
**Rama:** `connect-study`  
**Fecha:** 2026-10-04  
**Relacionado:** [`ai-generation-tiers-and-budgets.md`](./ai-generation-tiers-and-budgets.md)

## 1. Modelo de producto (lo que pedimos)

| Idea | Significado técnico | Lo que NO es |
|---|---|---|
| Conexión **transparente** para el usuario | Un botón “Conectar Instagram / YouTube / …”; el usuario autoriza en la pantalla oficial del proveedor | Pedirle al usuario crear apps, Client ID, secrets o pegar tokens |
| Usar **nuestras** conexiones | Fast Livery opera **una** Meta App / Google Cloud project / (opcional) HF org propios | Pedir BYO Meta App a cada cliente como camino principal |
| Tokens del usuario | Tras OAuth, el **access token del cliente** queda cifrado y aislado por tenant | Reutilizar el token de un cliente para otro |

**BYO (avanzado)** se mantiene solo como escape para agencias técnicas o entornos sin App Review; no es el camino por defecto.

## 2. Separación crítica: “nuestra app” ≠ “nuestro token de cuenta”

```text
[Fast Livery]  →  App/proyecto de plataforma (META_APP_ID, Google OAuth client, …)
       ↓ OAuth (pantalla Meta/Google, términos del proveedor)
[Usuario/Cliente] autoriza permisos sobre SU cuenta/canal/página
       ↓
[Token del usuario] cifrado en DB, scope agency→client
```

Legalmente válido en Meta/Google/YouTube: la plataforma aporta la aplicación; el usuario aporta el consentimiento.  
**Ilegal / incumplidor:** operar la cuenta del usuario sin OAuth, con cookies, o con un token compartido entre tenants.

## 3. Gates legales por paso (checklist operativo)

Cada paso debe quedar bloqueado en producto hasta cumplirse. Copy en UI + registro de aceptación (timestamp, versión, user_id, client_id, IP opcional).

### Paso A — Alta en Fast Livery

| Gate | Requisito | Evidencia |
|---|---|---|
| A1 | Aceptar **Términos de uso** Fast Livery | Checkbox + versión ToS |
| A2 | Aceptar **Política de privacidad** | Checkbox + versión |
| A3 | Rol (agencia / cliente portal) claro | Contrato o invite |
| A4 | (Si aplica) DPA / encargado de tratamiento | Doc firmado o clickwrap B2B |

**No avanzar a canales sin A1+A2.**

### Paso B — Antes de “Conectar [canal]”

| Gate | Requisito | Evidencia |
|---|---|---|
| B1 | Explicar en lenguaje claro: qué datos se leen, qué se puede publicar, que **no** se guarda la contraseña | Pantalla pre-OAuth (modal) |
| B2 | Enlace a políticas del proveedor (Meta / Google / LinkedIn) | Links oficiales |
| B3 | Confirmar que el usuario tiene derecho a administrar esa cuenta/página/canal | Checkbox “soy admin / tengo autorización” |
| B4 | Confirmar presupuesto AI / nivel de generación si el canal implica generar contenido | Cap min/max + tier |

### Paso C — OAuth del proveedor (pantalla de ellos)

| Canal | Quién muestra términos | Qué debe pasar |
|---|---|---|
| Instagram / WhatsApp Cloud | Meta Login / Embedded Signup | Usuario otorga scopes; App en Advanced Access |
| YouTube | Google OAuth consent | Scope `youtube.upload` (mínimo); cuenta con canal verificado |
| LinkedIn (cuando se active) | LinkedIn OAuth | `openid` `profile` `w_member_social` + productos aprobados |
| Google login (agencia) | Google Identity | Solo identidad; no es canal social |

**No simular ni embeber usuario/clave propios** para “aprobar” OAuth del proveedor: incumpliría ToS y seguridad.

### Paso D — Tras conectar (antes de publicar)

| Gate | Requisito |
|---|---|
| D1 | Mostrar scopes concedidos y cuenta/canal conectado |
| D2 | Health check (token válido, permisos, límites) |
| D3 | Botón Desconectar / revocar |
| D4 | Aviso: publicar requiere aprobación humana explícita |

### Paso E — Generar contenido con AI (HF / Wan / LLMs)

| Gate | Requisito |
|---|---|
| E1 | Divulgar que el contenido puede enviarse a proveedores de inferencia (lista: HF, fal, Replicate, OpenAI, …) |
| E2 | Si el modelo es gated: la **cuenta que paga** debe haber aceptado la licencia del modelo |
| E3 | Quote de costo + nivel Economy/Standard/Premium + presupuesto cliente |
| E4 | No usar un único HF token de plataforma para redistribuir acceso gated entre clientes sin aceptación individual (preferir org HF Team con `bill_to` + política interna, o BYO token) |
| E5 | Contenido generado: responsabilidad del cliente (marcas, claims, derechos de imagen) |

### Paso F — Publicar

| Gate | Requisito |
|---|---|
| F1 | Revisar texto/media exactos |
| F2 | Checkbox “autorizo publicar este contenido en [cuenta]” |
| F3 | Preferir `private` / borrador en primera publicación YouTube hasta auditoría de cumplimiento |
| F4 | Auditoría: quién aprobó, cuándo, id externo del post |
| F5 | Idempotencia: no republicar el mismo draft sin intención |

## 4. Validación por proveedor (estado legal)

### 4.1 Meta (Instagram publish + WhatsApp Cloud)

| Tema | Validación | Implicación Fast Livery |
|---|---|---|
| App de plataforma para **otros negocios** | Requiere **App Review** + **Advanced Access** | Obligatorio para “Conectar con Meta” sin BYO |
| Business verification / **Tech Provider** | Meta exige verificación Tech Provider para apps claimed por un business que sirven a terceros con permisos como `instagram_content_publish`, `whatsapp_business_management`, etc. | Clan R3 / entidad legal debe completar Access Verification |
| Consentimiento | Cada negocio autoriza vía Login; token app-scoped | Flujo transparente OK |
| Standard Access | Solo cuentas propias / roles en la app | Insuficiente para clientes externos |
| Contraseña del usuario | Prohibido almacenarla; solo OAuth | UI nunca pide clave de Instagram/Facebook |

Fuentes: [Instagram Platform overview](https://developers.facebook.com/docs/instagram-platform/overview), [App Review](https://developers.facebook.com/documentation/instagram-platform/app-review), [Tech Providers](https://developers.facebook.com/docs/development/release/tech-providers/).

**Veredicto:** el modelo “nuestra Meta App + OAuth transparente” es el correcto y **es el que Meta exige** para multi-negocio. BYO es workaround de desarrollo, no producto final.

### 4.2 YouTube Data API

| Tema | Validación | Implicación |
|---|---|---|
| OAuth usuario | Obligatorio para subir al canal del cliente | Botón Conectar YouTube |
| Proyecto Google de plataforma | Un OAuth client de Fast Livery | “Nuestra conexión” |
| Uploads públicos | Proyectos no auditados (post 2020) → videos **solo private** hasta compliance audit | Gate F3 + plan de auditoría API |
| Cuota | 10k units/día default; upload cuesta cuota | Presupuesto + cola |
| Políticas Developer | No ocultar uso de API; permitir auditoría de YouTube | Cuentas de prueba, docs honestas |

Fuentes: [YouTube Developer Policies](https://developers.google.com/youtube/terms/developer-policies), [Quota and Compliance Audits](https://developers.google.com/youtube/v3/guides/quota_and_compliance_audits), [videos.insert](https://developers.google.com/youtube/v3/docs/videos/insert).

**Veredicto:** plataforma + OAuth OK; publicación pública exige auditoría de cumplimiento del proyecto.

### 4.3 LinkedIn

| Tema | Validación |
|---|---|
| App + productos Share / Sign In | Ya alineado en trabajo previo |
| Página Company asociada a la app | Irreversible; no perfil personal |
| Publicar perfil personal | `w_member_social` + aprobación humana |
| Páginas empresa | Community Management (aprobación aparte) |

**Veredicto:** mismo patrón plataforma + OAuth; no scrapers.

### 4.4 Hugging Face / Wan / inferencia

| Tema | Validación | Implicación |
|---|---|---|
| HF ToS | Acceso limitado a Services; no transferir derechos | Plataforma no “revende” HF como si fuera suyo sin cuenta/org |
| Inference Providers | Facturación HF o provider key; créditos mensuales bajos en free | Producción: HF PRO/Team o keys fal/Replicate |
| Modelos gated / Apache Wan | Wan2.1 Apache-2.0 (pesos); otros modelos pueden ser gated | Aceptación de licencia por la cuenta que descarga/infiere |
| Multi-tenant | Evitar un token personal compartido entre clientes | Org HF Team + spend limits + atribución por cliente en Fast Livery, o BYO |

Fuentes: [HF Terms](https://huggingface.co/terms-of-service), [Inference Providers pricing](https://huggingface.co/docs/inference-providers/pricing), [Wan2.1](https://github.com/Wan-Video/Wan2.1).

**Veredicto:** “nuestras conexiones” de AI = **cuenta/org de plataforma con presupuesto y ToS Fast Livery que cubran retiro de costos al cliente**, más divulgación E1–E5. No sustituye el consentimiento del canal social.

### 4.5 n8n / automatizaciones de terceros

Usar el JSON de la guía Shorts **dentro** de n8n Cloud del cliente es su responsabilidad.  
Embebido como dependencia del producto Fast Livery: evita acoplar ToS de n8n + 6 vendors al núcleo. Preferir pipeline nativo con gates F/E.

## 5. UX transparente (sin rediseñar el sistema de seguridad)

Reutilizar patrones actuales (accordions, health, mock):

1. **Default:** botón primario “Conectar con [proveedor]” (OAuth plataforma).
2. **Pre-modal legal** (B1–B4) antes del redirect.
3. **Advanced / BYO** colapsado (como hoy en Instagram), no recomendado.
4. Tras conectar: chip de cuenta + health + “Desconectar”.
5. Publicar: misma gate humana que LinkedIn/Instagram drafts.
6. AI: selector de nivel + quote + progreso de presupuesto (no cambia pantallas OAuth).

No pedir usuario/clave de redes en formularios propios.

## 6. Matriz “quién paga / quién autoriza”

| Recurso | Quién posee la App/proyecto | Quién autoriza la cuenta | Quién paga inferencia | Contable en Fast Livery |
|---|---|---|---|---|
| Instagram publish | Fast Livery Meta App | Cliente (OAuth) | N/A (API Meta) | Token cliente |
| WhatsApp Cloud | Fast Livery Meta App (+ WABA) | Cliente / Embedded Signup | Conversaciones Meta | Por número/cliente |
| YouTube Shorts | Google Cloud Fast Livery | Cliente (OAuth) | N/A | Cuota proyecto + caps |
| Texto/imagen/video AI | Org HF / keys plataforma o BYO | Aceptación ToS Fast Livery + licencias modelo | Plataforma → se repercute al cliente vía presupuesto | `UsageRecord` + cap cliente |

## 7. Riesgos legales a bloquear en producto

| Riesgo | Mitigación |
|---|---|
| Publicar sin consentimiento | Gate F1–F2 obligatorio |
| App Meta sin Tech Provider / Review | OAuth plataforma deshabilitado hasta verificación; mensaje claro |
| YouTube public sin audit | Forzar `private` + banner |
| Token cruzado entre clientes | Aislamiento tenant (ya en arquitectura) |
| Redistribuir modelos gated con un solo HF user token | Org + políticas o BYO; nunca cache compartido de pesos gated |
| Prometer “autopilot total” sin aprobación | Copy: siempre “tú apruebas” |
| Jurisdicción (CO / LatAm) | Privacidad + DPA; no sustituye abogado local |

> Este documento es análisis de ingeniería alineado a políticas públicas de desarrolladores. **No es dictamen legal.** Antes de producción multi-cliente, revisión con asesoría jurídica y compliance Meta/Google.

## 8. Orden de habilitación recomendado

1. Entidad legal + ToS/Privacy/DPA Fast Livery (Paso A).
2. Meta Business Verification + Tech Provider + App Review (IG + WA scopes).
3. Google Cloud OAuth + YouTube API; arrancar uploads `private`; solicitar compliance audit.
4. UI: OAuth primario + pre-modal legal; BYO secundario.
5. Presupuestos AI + tiers (doc de costos).
6. Wan/HF bajo org plataforma con caps por cliente + divulgación E1–E5.
7. Solo entonces: autopost programado tras aprobación.

## 9. Criterios de aceptación

- [x] Modelo “nuestra app + OAuth del usuario” validado frente a Meta/YouTube
- [x] Gates legales A–F definidos por paso
- [x] Tech Provider / App Review / YouTube audit identificados como bloqueantes
- [x] AI plataforma con repercusión de costo y divulgación; sin alterar OAuth de canales
- [ ] Implementación de pre-modales y acceptance log (pendiente de autorización de código)
- [ ] Dictamen legal externo (pendiente negocio)
