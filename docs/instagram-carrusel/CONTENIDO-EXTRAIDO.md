# Carruseles Instagram — extracción del video (corregido)

**Fuente:** [5 sistemas increíbles que puedes montar con el nuevo ChatGPT Work](https://www.youtube.com/watch?v=y2AvADj37q0)  
**Autor:** Nico (nicocmw) · ~17 min  
**Documento de casos de uso:** [Google Doc](https://docs.google.com/document/d/1TPGPIvcXebQAgj7YXkq9IhrCL3SXDYzem7wiBhWGsnc/edit?usp=sharing)

> **Corrección:** La versión anterior usaba por error una grabación local de otra sesión (PROPULSA). Todo lo de abajo sale del YouTube indicado.

---

## Resumen ejecutivo

El video enseña **5 sistemas** con **ChatGPT Desktop** o **Claude Desktop** (suscripción **Pro** mínima) + extensión **Chrome**. Dos casos aplican directamente a **carruseles de Instagram**:

| # | Sistema | Relación con carruseles IG |
| --- | --- | --- |
| 1 | Chrome → scrapear referencias | Descargar slides de un creador (ej. Yunu) como JPG en carpetas |
| 4 | Generación masiva multihilo | Mismo flujo para carruseles, lead magnets, PDFs, presentaciones |
| 5 | App local + MCP | Máquina de miniaturas **y carruseles** con preview estilo Instagram |

Los casos 2 (facturas) y 3 (correo) no son de carruseles pero comparten el mismo stack (Chrome + conectores).

---

## Requisitos comunes

1. **ChatGPT Desktop** o **Claude Desktop** instalado.
2. Suscripción **Pro** (funciones vetadas en plan free).
3. Extensión **Chrome** de ChatGPT o Claude activada.
4. Sesión iniciada en Chrome en las webs que quieras automatizar.

### Instalación rápida

| Herramienta | Dónde |
| --- | --- |
| ChatGPT Desktop | Buscar “GPT desktop” → descarga oficial |
| Claude Desktop | Buscar “Claude Desktop” |
| Extensión Chrome | Complementos → **Chrome** (ChatGPT) o Configuración → **Claude in Chrome** |

---

## Caso 1 — Scrapear carruseles de referencia (Instagram)

**Objetivo:** Tener en local todos los slides de un perfil para que la IA analice estilo, estructura y copy.

### Flujo (como en el video)

1. Elige un perfil de referencia (en el video: **Yunu** — carruseles que le gustan a Nico).
2. Prompt a Codex/Claude Desktop, por ejemplo:

```
Usa Chrome para entrar en el perfil de Instagram de [usuario].
Por cada carrusel:
  - Crea una carpeta raíz con el nombre del creador (ej. yunu/)
  - Dentro, una subcarpeta por carrusel
  - Guarda cada slide como JPG (captura con la extensión)
Ságame los primeros 30 carruseles que encuentres.
```

3. **Resultado en disco:**

```
yunu/
  carousel-01/
    slide-01.jpg
    slide-02.jpg
    ...
  carousel-02/
    ...
```

4. La IA puede sacar **headers**, layouts y patrones visuales slide a slide.

### Para qué sirve después

- Dataset de referencia para prompts de generación de imágenes.
- Análisis de hooks (slide 1), estructura (problema → tips → CTA).
- Entrenar tu propio “sistema de carruseles” con ejemplos reales.

---

## Caso 4 — Generación masiva (carruseles incluidos)

**Objetivo:** Producir muchos activos (presentaciones, **carruseles**, lead magnets, ebooks) con calidad, no solo volumen.

### Stack adicional

- **Chrome** (interactuar con Gemini, ChatGPT web, etc.).
- **Generación de imágenes** (Codex).
- **Multihilos:** un hilo principal crea chats hijos; cada uno trabaja una pieza.

### Flujo

1. Defines el lote: *“Quiero N carruseles sobre [tema], 8 slides cada uno, estilo [referencia].”*
2. El agente abre hilos paralelos (uno por carrusel o por slide batch).
3. Usa Chrome para capturas, ejercicios, pruebas en herramientas externas.
4. Genera imágenes y compone slides.
5. Iteras prompts hasta calidad deseada.

### Aplicable a carruseles

> *“Lo puedes aplicar a lead magnets, **carruseles**, ebooks… cualquier cosa que genere PDFs o documentos de forma masiva.”*

**Prompt base:**

```
Crea [N] carruseles de Instagram (1080×1350, 4:5).
Tema: [X]. Audiencia: [Y].
Slide 1: hook. Slides 2–7: valor. Slide 8: CTA.
Usa las referencias en ./yunu/ como guía de estilo.
Genera imágenes con el generador integrado y exporta JPG por slide.
```

---

## Caso 5 — App local + MCP (carruseles + preview IG)

**Objetivo:** Herramienta **propia**, en local, conectada a Codex vía **MCP**, para miniaturas YouTube **y carruseles**.

### Capacidades (video)

- Chat con IA dentro de la app.
- Seleccionar imágenes + logo → *“genera composición con X así y Y asá”* → imagen en la app.
- **Preview carrusel:** ver cómo quedarían 3+ slides en Instagram antes de publicar.
- Todo local → sin preocupación de hackeo; coste API casi nulo (usa suscripción desktop).
- Código **open source** en GitHub (enlace en el Google Doc de la descripción del video).

### Arquitectura

```
Codex Desktop  ←→  MCP local  ←→  App local (UI)
                      ↑
              Chrome extension (enriquecer referencias)
```

### Extensión del sistema (idea del video)

Combinar **Caso 1 + Caso 5**:

1. Chrome detecta diariamente mejores miniaturas/carruseles de N creadores.
2. Las mete en carpeta `mejores-referencias/`.
3. La app local + MCP las usa para enriquecer generación.
4. Tú iteras en preview carrusel hasta publicar.

### Nivel recomendado

- Casos 1–4: cualquier usuario Pro.
- Caso 5: requiere tocar código/MCP; el repo del doc acelera el setup.

---

## Carrusel IG listo para publicar (contenido del video)

Se generó **`slides/carrusel-5-sistemas-nico.html`** — 8 slides resumiendo el video para promocionar el método en Instagram.

### Estructura sugerida

| Slide | Contenido |
| --- | --- |
| 1 | Hook: «5 sistemas que me ahorran horas con ChatGPT Work» |
| 2 | Requisito: Desktop Pro + extensión Chrome |
| 3 | Sistema 1: Scrapea carruseles de referencia |
| 4 | Sistema 2: Facturas automáticas (Gmail + Drive) |
| 5 | Sistema 3: Correo clasificado + borradores |
| 6 | Sistema 4: Carruseles/PDFs en masa (multihilo) |
| 7 | Sistema 5: App local + preview carrusel IG |
| 8 | CTA: Doc en descripción · Comenta «SISTEMA» |

**Caption:**

```
Dejé de hacer carruseles a mano cuando entendí estos 5 sistemas.

El 1 y el 5 son oro para Instagram:
→ Descargar carruseles de referencia con Chrome
→ Generar y previsualizar en local con MCP

Video completo: [tu link]
Instrucciones: Google Doc en la descripción del video de @nico.cmw

¿Cuál montas primero? 1–5 👇
```

---

## Prompts copy-paste

### Scrape referencias (Caso 1)

Ver bloque en sección Caso 1.

### Generar carrusel desde referencias (Caso 4)

```
Tengo referencias en ./referencias/[creador]/.
Analiza hooks, paleta y estructura de los primeros 5 carruseles.
Genera 1 carrusel original de 8 slides (1080×1350) sobre [TEMA].
No copies texto literal; mantén el patrón visual.
Exporta cada slide como PNG numerado.
```

### Preview + iteración (Caso 5)

```
En la app local, carga slide-01.png, slide-02.png, slide-03.png.
Modo preview carrusel Instagram.
Ajusta slide 2: más contraste en el título y CTA más corto.
Regenera solo slide 2 manteniendo coherencia con slide 1.
```

---

## Timestamps del video

| Momento | Tema |
| --- | --- |
| 0:00 | Intro — 5 sistemas, de simple a avanzado |
| 1:10 | Caso 1 — Chrome + scrape carruseles IG |
| 3:42 | Caso 2 — Facturas (Gmail + Chrome + Drive) |
| 6:50 | Caso 3 — Gestión correo (etiquetas + borradores) |
| 8:49 | Caso 4 — Presentaciones/carruseles masivos |
| 13:03 | Caso 5 — App local MCP + preview carrusel |

---

## Archivos en este repo

| Archivo | Descripción |
| --- | --- |
| `CONTENIDO-EXTRAIDO.md` | Este documento |
| `IMPLEMENTACION-CARRUSELES.md` | Checklist paso a paso |
| `prompts/` | Prompts listos para Desktop |
| `slides/carrusel-5-sistemas-nico.html` | Carrusel IG sobre el video |
| `frames/` | *(obsoleto — era otro video; ignorar)* |

---

## Próximo paso recomendado

1. Abre el [Google Doc de casos de uso](https://docs.google.com/document/d/1TPGPIvcXebQAgj7YXkq9IhrCL3SXDYzem7wiBhWGsnc/edit?usp=sharing) y el **GitHub del Caso 5**.
2. Monta **Caso 1** con un perfil de referencia tuyo (no solo Yunu).
3. Pasa esas JPG a **Caso 4** para generar tu primer carrusel original.
4. Si quieres preview IG, avanza a **Caso 5** con el repo del doc.
