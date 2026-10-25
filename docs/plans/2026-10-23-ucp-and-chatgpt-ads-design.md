# Per-client integrations: Google UCP and ChatGPT Ads

Research note and initial design. Nothing here is implemented yet.

## What each one is

**Google UCP (Universal Commerce Protocol).** Google's protocol for agentic
shopping: an AI surface can read a merchant's catalog, build a cart, apply
loyalty and hand off to checkout. Google keeps shipping carts, catalogs and
loyalty support and markets it to retailers as the way to sell inside AI
experiences ([Google Shopping updates](https://blog.google/intl/es-419/actualizaciones-de-producto/informacion/shopping-updates-google-marketing-live/),
[UCP carts/catalogs/loyalty](https://www.searchenginejournal.com/googles-ucp-update-carts-catalogs-and-loyalty-in-ai-shopping/571496/),
[retailer tools](https://business.google.com/us/think/ai-excellence/agentic-commerce-ai-tools-protocol-retailers-platforms/)).

**ChatGPT Ads.** OpenAI's ad product inside ChatGPT, in testing and expanding
country by country — 26 additional countries as of October 2026
([CNBC](https://www.cnbc.com/2026/10/21/openai-chatgpt-ads-26-countries.html),
[OpenAI testing ads](https://openai.com/zh-Hant-HK/index/testing-ads-in-chatgpt/)).

Both are **access-gated programs**, not open APIs. The first deliverable is
therefore a per-client configuration surface plus a requirements checklist, and
only then the connectors. Confirm current availability and API shape in each
official console before writing integration code.

## Why it fits Fast Livery

Both are per-client commercial surfaces, exactly like the WhatsApp or Instagram
channels already modeled. The product already owns the pieces they need: client
profile and brand DNA, content and carousels for creative, leads and ICP for
audience, and an inbox where the resulting conversations land.

## Data model (proposal)

New table `client_integrations` with one row per client and integration:

| Column | Notes |
|---|---|
| `agency_id`, `client_id` | tenant scope, unique on `(client_id, kind)` |
| `kind` | `ucp` or `chatgpt_ads` |
| `status` | `disabled`, `pending`, `connected`, `error` |
| `config` | JSON: identifiers, account ids, currency, country |
| `secrets` | encrypted JSON: tokens, API keys (same Fernet path as channels) |
| `last_sync_at`, `last_error` | health surface for the UI |

UCP additionally needs a catalog to expose:

| Column | Notes |
|---|---|
| `products` | `client_id`, `sku`, `gtin`, `title`, `description`, `price`, `currency`, `availability`, `image_url`, `url` |
| `feed_status` | `ok`, `warning`, `error` with per-item messages |

ChatGPT Ads needs creative and event data: reuse `Carousel`/`MediaAsset` for
creatives and add `ad_events` (`impression`, `click`, `conversion`) keyed by
client and campaign.

## Requirements checklist

**UCP**

- Google Merchant Center account for the client, or a feed Google can ingest.
- Catalog with GTIN where it exists, price, currency, availability and images.
- Public HTTPS endpoints: catalog feed, cart, and the checkout handoff URL.
- Shipping and returns policy published; tax and currency declared.
- Domain verification for the client's store.
- Written confirmation from Google that the account is in the UCP program.

**ChatGPT Ads**

- OpenAI Ads account enabled for the client's country.
- Business verification and billing.
- Creative assets within the ad spec (text, image; video where available).
- Conversion tracking: a pixel or server events with a stable identifier.
- A data-processing basis for the audience used (consent, as with leads).

## Initial configuration

Environment (platform level, not per client):

```
UCP_ENABLED=false
UCP_FEED_BASE_URL=
CHATGPT_ADS_ENABLED=false
CHATGPT_ADS_API_BASE=
```

Per client, through the UI: country, currency, timezone, catalog source
(manual, CSV, or feed URL), checkout URL, and the credentials for each program.
Both integrations stay `disabled` until their checklist is fully green.

## Screens expected

1. **Client > Integrations.** Two cards (UCP, ChatGPT Ads) with status pill,
   requirement checklist, last sync, and a primary action.
2. **UCP setup wizard.** Four steps: merchant identity, catalog source, shipping
   and returns, checkout handoff; then verification with a sample query.
3. **UCP catalog.** Table of products with per-item status, feed freshness,
   import CSV and a "resync" action.
4. **UCP test console.** Type a shopper query, see what an AI surface would
   return, with the reason when nothing matches.
5. **ChatGPT Ads setup.** Account link, country and currency, budget guardrails,
   conversion event mapping.
6. **ChatGPT Ads creatives.** Generate from a carousel, preview, edit, submit for
   review, with approval status per creative.
7. **Ads performance.** Impressions, clicks, spend, conversions and cost per
   conversion, filterable by client and period, reusing the dashboard patterns.
8. **Integration log.** One timeline per integration: every call, error and retry.

## Mockup prompts (Spanish, ready to paste)

**1. Pantalla de integraciones del cliente**
"Diseña una pantalla de configuración dentro de un panel SaaS B2B, en español, estilo limpio con tarjetas blancas sobre fondo gris claro, tipografía Inter, color de acento azul petróleo. Título 'Integraciones' y subtítulo 'Conecta los canales comerciales de este cliente'. Dos tarjetas grandes: 'Google UCP' con icono de bolsa y subtítulo 'Vende dentro de experiencias de IA', y 'ChatGPT Ads' con icono de burbuja y subtítulo 'Anuncia dentro de ChatGPT'. Cada tarjeta muestra un badge de estado ('No configurado', 'Pendiente', 'Conectado', 'Error'), una lista de 3 requisitos con checks verdes o grises, la fecha del último sync y un botón primario 'Configurar'. A la derecha, una columna estrecha con 'Salud de la integración' y una barra de progreso de requisitos."

**2. Asistente UCP de cuatro pasos**
"Mockup de un wizard de configuración de 4 pasos con barra de progreso superior: 'Identidad del comercio', 'Catálogo', 'Envíos y devoluciones', 'Checkout'. En el paso 2 se ve una tabla de productos con columnas SKU, GTIN, título, precio, moneda, disponibilidad y estado (verde/amarillo/rojo), un botón 'Importar CSV' y otro 'Resincronizar'. Incluye un panel lateral con 'Vista previa del feed' mostrando el JSON resultante en tipografía monoespaciada. Al pie, botones 'Atrás' y 'Continuar'."

**3. Consola de prueba UCP**
"Pantalla de prueba de comercio agéntico: arriba un campo grande de búsqueda con el placeholder '¿Qué buscaría un cliente?', debajo una tarjeta de resultado con imagen del producto, título, precio, disponibilidad y un botón 'Añadir al carrito'. A la derecha, un panel 'Qué devuelve el protocolo' con el JSON de la respuesta y un indicador de latencia. Si no hay resultados, un estado vacío que explique por qué (sin stock, sin GTIN, feed desactualizado)."

**4. Configuración de ChatGPT Ads**
"Pantalla de configuración de anuncios con tres secciones apiladas: 'Cuenta' (selector de cuenta vinculada, país, moneda), 'Presupuesto' (campo de gasto diario, límite mensual, un switch 'Pausar si el costo por conversión supera X'), y 'Conversiones' (mapeo de eventos: impresión, clic, conversión, con un selector de fuente). Cada sección en tarjeta blanca con borde suave. Arriba, un banner informativo amarillo que dice 'Programa en acceso anticipado: confirma la disponibilidad de tu país'."

**5. Estudio de creatividades para anuncios**
"Layout de dos columnas: a la izquierda una galería de creatividades generadas desde carruseles, cada una con imagen, título corto, texto y un badge 'Borrador / En revisión / Aprobado / Rechazado'. A la derecha, un editor con campos de título, texto y llamada a la acción, más la vista previa del anuncio tal como se vería dentro de una conversación de chat, en una tarjeta con burbuja redondeada. Botón primario 'Enviar a revisión'."

**6. Rendimiento de anuncios**
"Dashboard de rendimiento con filtros de cliente y rango de fechas: cuatro KPI en tarjetas (impresiones, clics, gasto, conversiones) con variación porcentual y flecha verde o roja, una gráfica de líneas de gasto vs. conversiones por día, y una tabla por campaña con CTR, CPA y estado. Paleta sobria, sin sombras fuertes."

**7. Bitácora de integración**
"Pantalla de log tipo consola: lista cronológica de llamadas con hora, método y endpoint, código de respuesta con color (verde 2xx, ámbar 4xx, rojo 5xx) y un mensaje corto. Arriba, filtros por integración, por nivel y un buscador. Al seleccionar una fila, un panel lateral muestra la petición y la respuesta completas. Botón 'Reintentar' solo en filas fallidas."

## Phasing

1. **Now:** `client_integrations` table, two disabled cards, requirement checklists, log surface. No external calls.
2. **When access is confirmed:** UCP catalog + feed + test console; ChatGPT Ads account link + creatives.
3. **Later:** performance dashboards and conversion tracking.

## Risks

- Both programs are gated and their APIs may change before general availability.
- UCP implies we host commerce endpoints for the client: that is a security and
  availability commitment, not just a UI.
- Ads data means personal data processing; the consent trail already built for
  leads must cover it.
- Do not promise coverage by country until the console confirms it.
