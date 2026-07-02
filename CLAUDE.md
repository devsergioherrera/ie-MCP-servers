# CLAUDE.md

Lee AGENTS.md para el contexto completo del proyecto.

Los pendientes de implementación están en **TASKS.md** (seguridad, funcional, observabilidad, operación). Consultarlo antes de proponer cambios que puedan solaparse con tareas ya planificadas.

> ⚠️ Este repo es público en GitHub. **Nunca** commitear secretos, passwords, connection strings ni datos personales. Los secretos viven solo en `deploy/.env` (gitignored).

## Onboarding / continuación (leer antes de trabajar)

Facts operativos que un agente necesita para continuar tras un `git clone` limpio:

- **Secretos no viajan en git**: `deploy/.env` está en `.gitignore`. Un clone da el código, no las credenciales. Para levantar el stack: `cp deploy/.env.example deploy/.env` y rellenar los connection strings (las claves ya están en el template; los valores reales solo los tiene el admin).
- **El proxy es un contenedor** (`ie-proxy`, en `/proyectos/ie-proxy/`), **no** nginx del host. Reload: `docker exec ie-proxy nginx -t && docker exec ie-proxy nginx -s reload`. (AGENTS.md aún describe la fase inicial con nginx nativo; lo vigente es el proxy containerizado.)
- **Deploy**: push a `master` → en el servidor `git pull` en `/proyectos/ie-MCP-servers` → `cd deploy && docker compose up -d --build <servicio>`.
- **Usuario del servidor** (`claude-agent`): **sin sudo**, pero está en el grupo `docker` y tiene ACL de escritura en `/proyectos/`. El proxy y los contenedores se gestionan sin sudo.
- **SQL nunca lo ejecuta el agente**: los GRANT/REVOKE los corre un admin en SSMS. No usar `sqlcmd` ni herramientas CLI de SQL. Los `.sql` commiteados llevan placeholders, nunca passwords reales.
- **BD INTRANET**: no editar `data-mcp-servers/mssql-intranet/dab-config.json` a mano — es **generado**. Editar `gen-config.py` y regenerar.
- **BDs de MCP = solo lectura** (usuario `mcp_reader`, `db_datareader`). Endurecido en 3 capas (motor / runtime DAB / entidad). Ver AGENTS.md > Boundaries.

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
