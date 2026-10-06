# Content Studio — visión faseada

Date: 2026-10-05  
Branch: `youtube-shorts`  
Status: product direction (validated)

## Norte del producto

```text
Cliente → Conectar redes (OAuth por canal)
       → Crear contenido (tipo: carrusel / video / post / imagen)
       → Preview adaptado por red
       → Aprobación humana
       → Publicar en las redes seleccionadas
```

Un **contenido canónico** + **adaptadores por red**.  
No un escritorio/skill distinto por plataforma como centro de UX.

## Qué no cambia

- App de plataforma + OAuth del usuario (sin passwords)  
- Tokens cifrados por agency → client  
- Gates legales A/B/F  
- BYO keys de IA donde aplique  
- APIs oficiales (Meta / LinkedIn / Google); sin scraping  

## Fases

### Fase 1 — Unificar lo que ya existe (prioridad)

Objetivo: “crear + elegir redes” sin inventar un CMS gigante.

| Pieza canónica | Destinos MVP |
|---|---|
| Carrusel (Pomelli / bridge actual) | Instagram (ya), opcional export/copy |
| Post texto | LinkedIn (publish OAuth), copy-paste fallback |
| Imagen / post IG | Instagram compose existente |

Trabajo concreto:

1. **Hub de publicación** por cliente: lista de piezas + “Publicar en…” con checkboxes de redes **ya conectadas**.  
2. Reordenar LinkedIn: Conectar → Generar → Aprobar → Publicar primero; voz/perfil secundario.  
3. Modal legal B en LinkedIn OAuth (paridad con IG/WA).  
4. Preview/límites por adaptador (texto LinkedIn vs caption IG).  
5. Una aprobación humana por destino (o una global + confirmación por red si falla).  

Fuera de Fase 1: editor multi-red sofisticado, scheduling cross-network, YouTube.

### Fase 2 — Video como tipo de contenido

- Tipo canónico: **video vertical Short/Reel**  
- Generación BYO (fal/Replicate) + wrap FFmpeg (logo)  
- Destino primario: **YouTube (`private`)**  
- Destino siguiente: Instagram Reels (mismo asset adaptado) cuando el adaptador esté listo  

Diseño técnico detallado: [`2026-10-05-youtube-shorts-design.md`](./2026-10-05-youtube-shorts-design.md)  
Interpretación: YouTube es **destino + pipeline de video**, no un tercer “desk” paralelo al Studio.

### Fase 3 — Studio completo

- Un solo compose por tipo de contenido  
- Multi-selección de redes con cola de publicación  
- Presupuestos AI / tiers  
- Scheduling unificado  

## Implicación para LinkedIn (revisión actual)

LinkedIn deja de ser “el producto”. Es:

1. Canal conectable (OAuth)  
2. Adaptador de **post texto**  
3. Herramientas de voz/hooks como ayuda al generador, no home  

## Implicación para YouTube

Implementar bajo Fase 2, reutilizando el hub/aprobación de Fase 1.  
No construir una UX de copy-desk al estilo LinkedIn skill.

## Criterio de éxito Fase 1

Desde un cliente con IG y LinkedIn conectados:

1. Crear o elegir un carrusel / post texto  
2. Marcar redes destino  
3. Aprobar  
4. Ver resultado por red (publicado / error / copy-paste) sin salir a un desk distinto por cada red  

## Orden de implementación sugerido

1. Doc + ajuste LinkedIn (orden UI + legal B + guía)  
2. Hub mínimo “Publicar en…” (carrusel→IG + texto→LinkedIn)  
3. Luego pipeline video → YouTube (Fase 2)
