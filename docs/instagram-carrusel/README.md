# Instagram carruseles — fuente corregida

**Video:** https://www.youtube.com/watch?v=y2AvADj37q0  
**Título:** 5 sistemas increíbles que puedes montar con el nuevo ChatGPT Work (Nico / nicocmw)

## Contenido

| Archivo | Uso |
| --- | --- |
| [CONTENIDO-EXTRAIDO.md](./CONTENIDO-EXTRAIDO.md) | Extracción completa del video |
| [IMPLEMENTACION-CARRUSELES.md](./IMPLEMENTACION-CARRUSELES.md) | Checklist paso a paso |
| [prompts/](./prompts/) | Prompts para Desktop |
| [slides/carrusel-5-sistemas-nico.html](./slides/carrusel-5-sistemas-nico.html) | Carrusel IG listo (8 slides) |

## Exportar PNG

```bash
cd docs/instagram-carrusel
python3 scripts/export_carousel_png.py
```

Requiere Playwright + Chromium (`python3 -m playwright install chromium`).

## Nota

La carpeta `frames/` corresponde a una grabación local incorrecta (otro evento). Ignorar.
