# Product catalog, feed generation and carousel integration

Addendum to the UCP and ChatGPT Ads design. The point: a client's products enter
once — by file or by API — get validated, and feed every destination we support,
including Instagram carousels.

## Flow

1. **Ingest** — upload a file (CSV, XLSX or JSON) or pull from the client's API
   (URL, method, headers, JSON path, field mapping).
2. **Validate** — map to the canonical product, run the rules below, and show a
   per-row report before saving anything.
3. **Store** — canonical products per client, with a source and a version.
4. **Generate feeds** — one artifact per destination, regenerated on change.
5. **Use** — UCP and ChatGPT Ads ingest the feed; carousels and channels use the
   same products for creative and product cards.

## Canonical product

| Field | Required | Notes |
|---|---|---|
| `sku` | yes | unique per client |
| `title` | yes | max 150 chars, no all caps |
| `description` | yes | plain text |
| `price` | yes | decimal, with `currency` (ISO 4217) |
| `availability` | yes | `in_stock`, `out_of_stock`, `preorder`, `backorder` |
| `image_url` | yes | HTTPS, reachable, at least 800x800 |
| `url` | yes | product page, HTTPS |
| `gtin` | destination-dependent | required by Google when it exists |
| `brand`, `category` | recommended | category mapped to the destination taxonomy |
| `condition` | default `new` | |
| `variants` | optional | size/colour with their own sku, price, stock |

Stored alongside: `source` (`file` or `api`), `raw` (original row), `status`
(`valid`, `warning`, `error`), `messages` (list).

## Validation rules

- Missing required fields, non-numeric price, unknown currency, bad availability.
- Duplicate `sku` inside the file and against what is already stored.
- Image URL not HTTPS, unreachable, or too small (HEAD request, cached result).
- Title over 150 characters; description with HTML.
- Google-specific: GTIN checksum when present, category in the taxonomy.
- Per-destination summary: "120 products, 112 ready for Google, 3 missing GTIN,
  5 broken images".

Validation never blocks import: rows are saved with their status so the client
can fix and re-import only the failures.

## Feeds

One endpoint per destination, public but signed and revocable:

| Destination | Format | Contents |
|---|---|---|
| Google (UCP / Merchant Center) | XML or TSV | id, title, description, link, image_link, availability, price, gtin, brand, condition |
| ChatGPT Ads | JSON | product id, title, price, image, landing url, category |
| Instagram shopping | catalog via Meta | id, title, price, availability, image, url |

Endpoints: `GET /feeds/{token}/{destination}.{format}`. Regeneration is triggered
by import, by manual edit, and by a nightly job. Each feed has a status card:
last generated, item count, rejected items and reasons.

## Products in carousels and channels

Once products exist:

- **Carousel from products.** Pick N products (or a filter such as "category =
  new arrivals"), and generate one slide per product using the brand DNA
  already stored per client: product image, title, price, one CTA.
- **Product cards in channels.** The agent can answer with a product card
  (image, title, price, link) in WhatsApp or the widget, read from the same
  catalog instead of the knowledge base.
- **Product-aware ICP.** A lead's conversation mentioning a SKU links to the
  product, so qualification and reporting can speak in terms of products.

## Screens

1. **Products list.** Table with search, source badge, status, price and actions;
   filters by status and category.
2. **Import wizard.** Choose file or API; for a file, drop zone and column
   mapping; for an API, URL, auth, sample request and JSON path mapping.
3. **Validation report.** Summary tiles and a table of rows with status and
   message, plus "re-import only the failures".
4. **Feed status.** One card per destination with last generation, item count and
   a copyable signed URL.
5. **Carousel from products.** Product picker on the left, slide preview with
   brand styling on the right, CTA and publish.

## Mockup prompts (Spanish)

**1. Listado de productos**
"Pantalla de catálogo de productos en un panel SaaS en español: tabla con columnas Producto (miniatura, título y SKU), Precio, Moneda, Disponibilidad, Origen (archivo/API), Estado (badge verde válido, ámbar con avisos, rojo con error) y Acciones. Arriba, buscador, filtros por estado y categoría, y dos botones: 'Importar archivo' e 'Importar desde API'. A la derecha, un panel de resumen con cuatro cifras: productos totales, listos para feed, con avisos y con errores."

**2. Asistente de importación**
"Wizard de importación en dos pestañas: 'Archivo' con zona de arrastre y tabla de mapeo de columnas (columna del archivo a la izquierda, campo del sistema a la derecha con selectores), y 'API' con campos de URL, método, cabeceras de autenticación, un botón 'Probar' y una vista previa del JSON con el mapeo de rutas. Al pie, 'Validar sin importar' y 'Importar'."

**3. Reporte de validación**
"Pantalla de resultados de validación: tres tarjetas superiores con cifras (filas listas, con avisos, con errores) y debajo una tabla con fila, SKU, campo afectado, mensaje y una acción 'Corregir'. Cabecera con un botón 'Reimportar solo los fallidos'. Los errores en rojo suave, los avisos en ámbar, ambas filas con fondo tenue y no con texto de color solamente."

**4. Estado de feeds**
"Tres tarjetas horizontales tituladas 'Google UCP', 'ChatGPT Ads' e 'Instagram shopping'. Cada una muestra un badge de estado, la fecha de última generación, el número de productos incluidos y rechazados, y una URL firmada en tipografía monoespaciada con botón de copiar. Debajo de cada tarjeta, un enlace 'Ver rechazados'."

**5. Carrusel desde productos**
"Editor de carrusel en dos columnas: a la izquierda un selector de productos con casillas y filtros por categoría, mostrando miniatura, título y precio; a la derecha una vista previa de la lámina con la identidad de marca del cliente (color primario, tipografía, logo), imagen del producto, título, precio y una única llamada a la acción. Arriba, un selector de número de láminas y un botón primario 'Generar carrusel'."

## Phasing

1. Canonical products, file import with validation report, products list.
2. API import with mapping and test call.
3. Feed generation with signed URLs and status cards.
4. Carousel from products and product cards in channels.

## Risks

- API pulls need SSRF protection and retry limits; reuse the guard already used
  by agent HTTP tools.
- Feeds expose prices and stock publicly: signed, revocable tokens only.
- Image checks are network calls; cache the result and cap concurrency.
- Destination taxonomies change; keep the mapping table versioned per feed.
