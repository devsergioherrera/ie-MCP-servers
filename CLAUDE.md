# CLAUDE.md

Lee AGENTS.md para el contexto completo del proyecto.

Los pendientes de implementación están en **TASKS.md** (seguridad, funcional, observabilidad, operación). Consultarlo antes de proponer cambios que puedan solaparse con tareas ya planificadas.

## Frontend — Estándares de Styling

### Font

Todos los aplicativos web (Astro, React, Next.js, etc.) **deben usar Inter como font principal**:

```css
:root {
  --font: "Inter", system-ui, -apple-system, sans-serif;
}

body {
  font-family: var(--font);
}
```

**Por qué Inter:**
- Diseño minimalista y limpio (Apple-style)
- Excelente legibilidad en pantalla
- Variable font: soporta pesos desde 100 a 900
- Código abierto y ampliamente disponible
- Carga rápida desde Google Fonts o localmente

**Fallback chain:**
1. `"Inter"` — la fuente principal
2. `system-ui` — fonts del sistema según SO
3. `-apple-system` — San Francisco en macOS
4. `sans-serif` — fallback genérico

Esto asegura consistencia visual en toda la plataforma web de IE.
