---
name: evaluacion-campana
description: "Evalúa una campaña de marketing de FastLivery con sus datos reales: oferta, público, canal, creatividad, landing, medición y economía (CPL, CAC, activación). Entrega nota por dimensión, CPL/CAC, veredicto escalar/ajustar/cortar y próximos pasos. Úsala al cerrar o revisar cualquier campaña."
---

# Evaluación de campaña (FastLivery)

Cada campaña deja su ficha en `campaigns/<slug>.json` y su evaluación en `campaigns/<slug>-evaluacion.md`.

## Entrada mínima

`campaigns/<slug>.json`:

```json
{
  "name": "Instagram carrusel — agencias PY",
  "channel": "instagram",
  "audience": "agencias de marketing 3-15 personas, Paraguay",
  "offer": "piloto white-label 30 días",
  "budget": 300,
  "currency": "USD",
  "from": "2026-11-01",
  "to": "2026-11-21",
  "metrics": {
    "impressions": 0, "clicks": 0, "leads": 0, "demos": 0,
    "activations": 0, "spend": 0, "revenue": 0
  }
}
```

Sin métricas, la evaluación es un plan: dilo y no inventes números.

## Rúbrica (0-5 o s/d)

| Dimensión | Peso | Qué mira |
|---|---|---|
| Oferta | 25 | promesa concreta, precio, riesgo bajo para probar |
| Público | 20 | segmento definido y alcanzable; no «pymes» |
| Canal | 15 | donde está ese público y coste de entrada |
| Mensaje/creatividad | 15 | primera línea, prueba, llamada a la acción |
| Landing y captura | 15 | UTM, formulario, token de lead capture, respuesta |
| Medición y economía | 10 | CPL, CAC, activación, payback; datos, no opiniones |

## Cálculos

- CPL = spend / leads; CAC = spend / activations; tasa lead→demo y demo→activación.
- Compara contra el objetivo de la campaña; si no hay objetivo, propón uno antes de juzgar.

## Veredicto

- Escalar: CAC por debajo del objetivo y activación sostenida.
- Ajustar: hay leads pero no activación, o CPL alto con buena calidad.
- Cortar: sin leads, o CAC por encima del doble del objetivo.

## Salida

`campaigns/<slug>-evaluacion.md` con tabla, CPL/CAC, veredicto y tres acciones. Resume en el chat en cinco líneas.
