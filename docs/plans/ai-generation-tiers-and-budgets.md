# Estudio: generación AI libre / BYO, niveles y presupuestos

**Repo:** `htrejos-clanr3/fast-livery` (privado, independiente)  
**Rama:** `connect-study`  
**Fecha:** 2026-10-04  
**Alcance:** estudio y verificación. No cambia seguridad, OAuth, diseño ni UI/UX de conexión existentes.

## 1. Principio de no alteración

Todo lo siguiente se monta **encima** del modelo actual:

| Conservar intacto | Cómo se respeta |
|---|---|
| Seguridad / tokens cifrados | Solo BYO keys de agencia (Settings → Providers), cifrado ya existente |
| Conexión de canales | WA / IG / (futuro YT) siguen con health + guía + mock; no se mete n8n ni scrapers |
| Diseño / UI de conexión | Reutilizar accordions, health, quotes de imagen; no rediseñar el hub |
| Contabilidad | Extender `usage.py` / `UsageRecord` (ya hay `estimated_usd` por modelo) |

**No se propone:** automatizar login de redes, cookies, scraping de perfiles, ni publicar sin aprobación humana.

## 2. Qué ya existe en Fast Livery / OpenLivery

- Imagen: `IMAGE_PROVIDER=openai|flux|ollama|placeholder` (`apps/api/app/services/image_generation.py`)
- Flux Schnell local (sidecar HTTP, $0 marginal de API)
- Usage + estimación USD por modelo (`apps/api/app/services/usage.py`)
- Quote de costo antes de generar carrusel (`test_image_quote.py`)
- Proveedores de texto BYO: OpenAI, Anthropic, DeepSeek, etc.

Hueco: no hay aún **presupuesto max/min por cliente**, ni **nivel de generación** (economy → premium) unificado para texto + imagen + video.

## 3. Alternativas libres o tokens del cliente

### 3.1 Texto (guion, caption, prompts)

| Opción | Costo marginal | Quién paga | Notas |
|---|---|---|---|
| DeepSeek / Kimi / Qwen (BYO) | Bajo (~$0.0003–0.003 / 1k tokens) | Cliente / agencia | Ya contemplado en rates |
| OpenAI / Anthropic (BYO) | Medio–alto | Cliente / agencia | Validar al guardar |
| Ollama local | $0 API | Operador (electricidad/GPU) | Sin salir de la red |
| HF Inference Providers (token HF del cliente) | Créditos mensuales HF + pay-as-you-go | Cuenta HF del cliente | Free: ~$0.10/mes créditos; PRO: ~$2/mes; sin markup HF |

### 3.2 Imagen

| Opción | Costo / imagen (orden) | Quién paga | Encaje |
|---|---|---|---|
| `placeholder` | $0 | — | Solo pruebas UI |
| Flux Schnell local | $0 API | GPU/CPU operador | Ya integrado |
| Ollama `x/flux2-klein` | $0 API | GPU local | Experimental |
| HF FLUX / SD (token HF o provider key) | ~$0.001–0.04 | Token del cliente | Añadir backend `hf` sin tocar OAuth canales |
| OpenAI gpt-image-* (BYO) | ~$0.02–0.20 | Key cliente | Actual default pago |

### 3.3 Video (Shorts / Reels) — Wan y similares

| Opción | Costo / clip ~5s | Quién paga | Viabilidad |
|---|---|---|---|
| **Wan2.1 1.3B self-host** (Apache-2.0) | $0 API; ~8 GB VRAM | GPU operador | Buena para lab; lento en CPU |
| **Wan2.1 14B self-host** | $0 API; GPU fuerte | Operador | Calidad alta; no apto Mac Intel 4 GB |
| **Wan vía fal.ai** (BYO key) | ~$0.20 (480p) / ~$0.40 (720p) | Key cliente | API simple; 9:16 soportado |
| **Wan vía Replicate** (BYO) | ~$0.05–0.35 (Wan 2.2) o ~$0.35–1.25 (Wan 2.1 14B) | Key cliente | HF InferenceClient puede enrutar a Replicate |
| **HF Inference Providers** | Pasa costo del provider; créditos HF si routed | Token HF cliente | Ideal para “una key, varios modelos” |
| Runway / Creatomate (guía n8n) | Alto (~$0.25+/clip + montaje) | Key cliente | Evitar como default; solo nivel Premium |

Referencias: [Wan2.1](https://github.com/Wan-Video/Wan2.1), [HF Inference Providers pricing](https://huggingface.co/docs/inference-providers/pricing), fal Wan T2V, Replicate Wan.

**Conclusión Wan:** sí se puede usar. Camino recomendado sin alterar el sistema:

1. Nivel bajo: sin video, o upload manual del MP4 ya renderizado.
2. Nivel medio: Wan 480p I2V/T2V con **key fal/Replicate/HF del cliente**.
3. Nivel alto: Wan 720p o Runway solo si el presupuesto del cliente lo permite.
4. Self-host Wan 1.3B solo en despliegues con GPU dedicada (sidecar, igual que Flux).

## 4. Niveles de generación (subir / bajar)

Un único selector por cliente (o por job): `economy | standard | premium`.  
No cambia pantallas de conexión; solo el backend de generación y el quote.

| Dimensión | Economy | Standard | Premium |
|---|---|---|---|
| Texto | DeepSeek / local | DeepSeek o GPT-mini | GPT / Claude |
| Imagen slides | Flux local / placeholder | HF FLUX o gpt-image-mini | gpt-image-1 / HF FLUX-dev |
| Video Short | Off o upload manual | Wan 480p BYO (1 clip) | Wan 720p o 2–3 clips + montaje |
| Audio | TTS local / silencio + captions | ElevenLabs free tier BYO | ElevenLabs pago BYO |
| Resolución | 720×1280 o slides 768 | 1080×1920 | 1080×1920 + más steps |
| Escenas por Short | 1–2 | 3 | 4–6 |
| Aprobación humana | Obligatoria | Obligatoria | Obligatoria |

Regla: **bajar de nivel nunca rompe publicación**; solo reduce calidad/costo. Subir exige presupuesto disponible.

## 5. Matriz de gastos AI (USD, referencia oct-2026)

Precios de lista aproximados; siempre cotizar en vivo con `quote` antes de generar. El cliente paga con **su** key o con saldo de agencia contabilizado.

### 5.1 Costo por unidad

| Artefacto | Economy | Standard | Premium |
|---|---|---|---|
| Caption / post texto | $0.000–0.002 | $0.002–0.01 | $0.01–0.05 |
| Carrusel 5 slides (solo copy) | $0.001–0.01 | $0.01–0.05 | $0.05–0.20 |
| Carrusel 5 slides + imágenes | $0 (Flux) – $0.05 | $0.10–0.50 | $0.50–2.00 |
| 1 clip video 5s Wan | $0 (local) | $0.05–0.25 | $0.20–0.50 |
| Short completo (3 clips + audio + montaje simple) | $0–0.10 | $0.20–0.80 | $0.80–3.00 |
| Short pipeline tipo guía n8n (PiAPI+Runway+Creatomate+EL) | — | — | **$1.50–4.00+** |

### 5.2 Presupuesto mensual por cliente (recomendado)

| Plan presupuesto | Mínimo (soft floor) | Máximo (hard cap) | Qué alcanza (Standard) |
|---|---|---|---|
| **Sandbox** | $0 | $2 | Texto + Flux local; sin video pago |
| **Starter** | $5 | $25 | ~40–80 posts texto; ~10–20 carruseles HF/mini; 0–4 Shorts Wan 480p |
| **Growth** | $25 | $100 | Agencia pequeña: posts diarios + ~8–15 Shorts/mes |
| **Scale** | $100 | $400 | Multi-marca o Shorts diarios Wan 480p |
| **Enterprise** | $400 | configurable | Cap custom + alertas; Premium permitido |

- **Mínimo:** avisa si el cliente casi no usa IA (oportunidad / health), no bloquea.
- **Máximo:** hard stop antes de llamar providers caros; UI muestra “sube presupuesto o baja a Economy”.
- Contabilizar por `agency_id` + `client_id` (hoy `UsageRecord` es por agencia; falta dimensión cliente en una fase posterior de implementación).

### 5.3 Optimización automática (sin tocar UX de canales)

1. **Quote previo** (ya hay patrón en imágenes): mostrar USD estimado + nivel.
2. Si `projected + spent > max` → forzar Economy o pedir confirmación.
3. Si quedan &lt; 20% del cap → sugerir bajar video a upload manual.
4. Preferir Flux/Ollama cuando `IMAGE_PROVIDER` local esté healthy.
5. Video: default Wan 480p; 720p solo Premium y con saldo.

## 6. Encaje con Ootto / YouTube Shorts (sin n8n obligatorio)

| Estación guía n8n | Alternativa Fast Livery | Nivel |
|---|---|---|
| Sheet ideas | Cola interna por cliente | todos |
| GPT prompts | BYO DeepSeek/OpenAI | E/S/P |
| PiAPI imágenes | Flux / HF / OpenAI | E/S/P |
| Runway clips | Wan (HF/fal/Replicate BYO) o self-host | S/P |
| ElevenLabs | BYO o captions sin audio IA | S/P |
| Creatomate | Montaje simple FFmpeg local o upload | E/S |
| YouTube upload | OAuth oficial + aprobación (futuro canal) | todos |

Así se evita el “stack de 6 llaves de pago” como default y se mantiene el control humano.

## 7. Hugging Face — qué se puede hacer ya

| Capacidad | ¿Viable? | Cómo sin alterar el sistema |
|---|---|---|
| Texto / chat | Sí | Provider OpenAI-compatible apuntando a HF router |
| Imagen FLUX/SD | Sí | Nuevo `IMAGE_PROVIDER=hf` + `HF_TOKEN` de agencia (BYO) |
| Video Wan | Parcial | HF → provider (Replicate/fal); timeout largo; job async |
| Créditos free | Sí, pero bajos ($0.10) | Solo demos; producción = PRO o key del provider |
| Facturar a org HF | Sí (`bill_to`) | Útil si la agencia tiene Team HF |

**No usar** el token HF del operador compartido entre todos los clientes sin cuota: cada agencia/cliente debe traer su token o saldo contabilizado.

## 8. Roadmap de implementación (cuando se autorice código)

Fase A — solo estudio ✅ (este doc)  
Fase B — presupuestos: `client.ai_budget_min_usd`, `ai_budget_max_usd`, `generation_tier`; hard cap en servicios de generación  
Fase C — `IMAGE_PROVIDER=hf` + quote unificado  
Fase D — video job Wan BYO (fal/Replicate/HF) + cola approve  
Fase E — canal YouTube upload (OAuth) reutilizando gate de aprobación  

Ninguna fase modifica el flujo de conexión Meta/WhatsApp existente.

## 9. Criterios de aceptación del estudio

- [x] Alternativas libres / BYO identificadas (Flux, Ollama, HF, Wan)
- [x] Matriz de costo por artefacto y nivel
- [x] Presupuestos min/max por tipo de cliente
- [x] Reglas para subir/bajar nivel sin romper seguridad ni UX de conexión
- [x] Wan viable como sustituto preferente de Runway en Standard
- [ ] Implementación diferida a aprobación explícita

## 10. Fuentes

- Guía Shorts n8n: `docs/plans/Guia_Shorts_Automaticos_n8n.pdf`
- Código: `image_generation.py`, `usage.py`, Settings images i18n
- [Wan2.1 GitHub](https://github.com/Wan-Video/Wan2.1)
- [HF Inference Providers pricing](https://huggingface.co/docs/inference-providers/pricing)
- fal.ai Wan T2V / Replicate Wan pricing (referencia de mercado)
