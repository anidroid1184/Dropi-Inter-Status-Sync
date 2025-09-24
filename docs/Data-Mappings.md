# Data Mappings / Mapeos de Datos

This document explains how raw statuses are mapped to normalized statuses, and how to extend the catalog.

Este documento explica cómo los estados en bruto se mapean a estados normalizados y cómo extender el catálogo.

## Sources / Fuentes
- `dropi_map.json` (repo root) — optional
- `interrapidisimo_traking_map.json` (repo root)
- Env overrides: `DROPI_MAP_PATH`, `INTER_MAP_PATH`

Format:
```json
{
  "ENTREGADO": ["entregado", "finalizado"],
  "EN_TRANSITO": ["transito", "tránsito", "ruta", "camino"],
  "PENDIENTE": ["pendiente", "por admitir"]
}
```

## Precedence / Precedencia
1. Overrides (phrases) — highest priority
2. JSON mappings (both files merged)
3. Heuristics fallback (built-in keywords)

1) Overrides (frases) — prioridad más alta
2) Mapeos JSON (ambos archivos combinados)
3) Heurísticas (palabras clave internas)

## How to extend / Cómo extender
- Add new keywords to the JSON file corresponding to the target status.
- Keep keywords lowercase and without trailing spaces.
- Validate JSON syntax.
- Restart the process; mappings are loaded at runtime.

Agrega nuevas palabras clave al JSON del estado objetivo, en minúsculas, valida la sintaxis y reinicia el proceso. Los mapeos se cargan en tiempo de ejecución.

## Diagnostics / Diagnóstico
- Use `TrackerService.explain_normalization(raw)` to see which rule matched (`via: override | mapping | heuristic | fallback`).
- Check `logs/status_catalog.json` for inventory of observed raw statuses and last-seen timestamps.
