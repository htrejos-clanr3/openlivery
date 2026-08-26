# Implementación — carruseles Instagram (video Nico)

Checklist basada en [y2AvADj37q0](https://www.youtube.com/watch?v=y2AvADj37q0).

---

## Fase 0 — Setup (30 min)

- [ ] Instalar **ChatGPT Desktop** o **Claude Desktop**
- [ ] Activar plan **Pro**
- [ ] Instalar extensión **Chrome** (ChatGPT o Claude)
- [ ] Iniciar sesión en Instagram en Chrome
- [ ] Crear carpeta de trabajo: `~/carruseles-ig/`

---

## Fase 1 — Referencias (Caso 1)

- [ ] Elegir 1–3 perfiles de referencia (carruseles que te gusten)
- [ ] Ejecutar prompt de `prompts/01-scrape-referencias.txt`
- [ ] Verificar estructura:

```
~/carruseles-ig/referencias/
  creador-a/
    carrusel-001/
      01.jpg … 08.jpg
```

- [ ] Revisar manualmente: slide 1 (hook), slide final (CTA), tipografía, colores

---

## Fase 2 — Análisis + brief

- [ ] Prompt: *“Analiza referencias/ y devuélveme: hooks top 5, estructura típica, paleta, longitud de texto por slide.”*
- [ ] Definir **tu** carrusel:
  - Tema
  - Audiencia
  - 8 slides (hook → valor → CTA)
  - CTA (comentario, DM, link bio)

---

## Fase 3 — Producción (Caso 4)

- [ ] Prompt de `prompts/02-generar-carrusel.txt` con tu brief
- [ ] Formato: **1080 × 1350** (4:5)
- [ ] Exportar JPG/PNG numerados en `~/carruseles-ig/salida/carrusel-001/`
- [ ] Revisar slide a slide; iterar solo los que fallen

---

## Fase 4 — Preview (Caso 5, opcional)

- [ ] Clonar repo del Google Doc (MCP + app local)
- [ ] Conectar Codex ↔ MCP
- [ ] Cargar slides en modo **preview carrusel Instagram**
- [ ] Ajustar composición antes de subir a Meta Business Suite / app IG

---

## Fase 5 — Publicación

- [ ] Orden correcto de imágenes (01 → 08)
- [ ] Caption + hashtags
- [ ] Primera línea del caption = hook (visible sin “ver más”)
- [ ] CTA en slide final **y** en caption

---

## Errores comunes (del video)

| Problema | Solución |
| --- | --- |
| Chrome no entra a IG | Sesión iniciada en el mismo Chrome de la extensión |
| Funciones vetadas | Suscripción Pro activa |
| Slides borrosos | Iterar generación de imágenes; no publicar v1 |
| Caso 5 muy pronto | Dominar Caso 1 + 4 antes de MCP |

---

## Automatización avanzada (idea final del video)

```
Diario (Chrome) → detectar mejores carruseles/miniaturas
       ↓
Carpeta mejores-referencias/
       ↓
Codex + MCP → generar borrador carrusel
       ↓
Preview IG → publicar
```

Implementar cuando Casos 1–4 estén estables.
