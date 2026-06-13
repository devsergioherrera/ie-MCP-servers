# HANDOFF — ie-MCP-servers (vacaciones Sergio)

> Estado al 2026-06-13. El código está 100% en `master` y pusheado.
> Lo único pendiente es **operativo** (un paso SQL + redeploy). Léelo completo.

## TL;DR — qué falta

Exponer la tabla `Usuarios` de la BD **INTRANET** quedó a medias. Hoy el
contenedor `mcp-mssql-intranet` está **en crash-loop** porque hay un `DENY` a
nivel de columna en SQL Server que rompe a DAB al arrancar. Hay que decidir:

- **Opción A (lo que pidió Sergio): exponer Usuarios COMPLETO** (incluye
  ContrasenaHash + Salt). Requiere quitar el DENY y redesplegar.
- **Opción B (recomendada por seguridad): NO exponer Usuarios** (o solo
  columnas no sensibles). Estabiliza el contenedor sin exponer credenciales.

> ⚠️ Nota de seguridad: `mcp.ie` no tiene autenticación (confianza-LAN).
> Exponer `Usuarios` completo publica hashes+salt de credenciales a cualquiera
> en la red interna (roza Ley 1273). Confirmar con Sergio antes de Opción A.

## Estado actual de los MCP servers (todos en `mcp.ie` vía proxy `ie-proxy`)

| Server | Ruta | Estado |
|---|---|---|
| `mcp-mssql-main` (DAB) | `/mssql/mcp` | ✅ OK (SIE + EMPAQUE, read-only) |
| `mcp-mssql-monitor` (DAB) | `/monitor/mcp` | ✅ OK (IE_MONITOR, read+write) |
| `mcp-ie-docs` (Python) | `/docs/mcp` | ✅ OK |
| `mcp-mssql-explorer` (Python) | `/explorer/mcp` | ✅ OK (introspección de esquema) |
| `mcp-mssql-intranet` (DAB) | `/intranet/mcp` | ⚠️ CRASH-LOOP (ver arriba) |
| `mcp-docs-api` + `mcp-ui` | `/info`, `/` | ✅ OK |

## Arquitectura clave (para no romper nada)

- **DAB** (`mcr.microsoft.com/azure-databases/data-api-builder`) es imagen
  cerrada: solo expone tablas/vistas/SPs declaradas en `dab-config.json`. No se
  le agregan tools custom. Para lógica custom está `mcp-mssql-explorer` (Python).
- **INTRANET expone "todas las tablas" vía un generador**:
  `data-mcp-servers/mssql-intranet/gen-config.py` introspecta INFORMATION_SCHEMA
  y regenera `dab-config.json`. NO editar el config a mano: editar el generador
  y regenerar.
- **Proxy = contenedor `ie-proxy`** en `/proyectos/ie-proxy/` (NO es nginx del
  host). Config de mcp.ie: `config/conf.d/mcp.ie.conf`. Reload:
  `docker exec ie-proxy nginx -t && docker exec ie-proxy nginx -s reload`.
- **Deploy** = push a master → `git pull` en el server → `docker compose up -d --build <servicio>`.
- `claude-agent` en el server NO tiene sudo, pero SÍ está en grupo `docker` y
  tiene ACL de escritura sobre `/proyectos/`. El proxy se gestiona sin sudo.
- Secretos solo en `/proyectos/ie-MCP-servers/deploy/.env` (gitignored).

## Cómo terminar la tarea pendiente

### Si se va por Opción A (exponer Usuarios completo)
1. En SSMS contra `192.168.50.86`:
   ```sql
   USE INTRANET;
   GO
   REVOKE SELECT ON dbo.Usuarios(ContrasenaHash, Salt) TO mcp_reader;
   GO
   ```
2. Regenerar + redesplegar (el generador ya está en modo "exponer todo"):
   ```bash
   ssh ie-linux "cd /proyectos/ie-MCP-servers && git pull && \
     cat data-mcp-servers/mssql-intranet/gen-config.py | \
     docker exec -i -e MSSQL_INTRANET_CONN=\"\$(grep '^MSSQL_INTRANET_CONN=' deploy/.env | cut -d= -f2-)\" \
     mcp-mssql-explorer python - > data-mcp-servers/mssql-intranet/dab-config.json && \
     cd deploy && docker compose up -d --build mcp-mssql-intranet"
   ```
3. Commitear el `dab-config.json` generado y push.

### Si se va por Opción B (estabilizar sin exponer Usuarios)
1. En `gen-config.py`, agregar `"usuarios"` al set `EXCLUDE_TABLES`.
2. Mismo bloque de regenerar + redeploy del paso 2 de arriba.
3. (Opcional) revertir el `REVOKE`/dejar el `DENY` como está — Usuarios no se
   expone de todos modos.

## Verificación final
```bash
ssh ie-linux "curl -s http://mcp.ie/docs/api/servers | python3 -c 'import sys,json;print([s[\"id\"] for s in json.load(sys.stdin)[\"servers\"]])'"
ssh ie-linux "docker ps --filter name=mcp-mssql-intranet --format '{{.Status}}'"  # debe decir Up, no Restarting
```

---

## PROMPT para tu agente de IA (Claude Code) — copiar/pegar tal cual

```
Trabajo en el repo ie-MCP-servers (monorepo de MCP servers de Integral de
Empaques, desplegado en linux.ie con Docker Compose detrás del proxy
containerizado ie-proxy). Lee primero AGENTS.md, CLAUDE.md y HANDOFF.md del
repo para el contexto completo.

Contexto del problema: el contenedor `mcp-mssql-intranet` (DAB, ruta
/intranet/mcp, BD INTRANET en 192.168.50.86) está en crash-loop. Causa: se
intentó exponer la tabla dbo.Usuarios pero hay un DENY a nivel de columna sobre
ContrasenaHash/Salt en SQL Server que rompe a DAB al leer el esquema (error 230
en FillSchema). El generador gen-config.py (que regenera el dab-config.json
introspeccionando INFORMATION_SCHEMA) ya está en modo "exponer todo".

Tarea: deja el contenedor mcp-mssql-intranet sano (estado Up, no Restarting).
Hay dos caminos, sigue las instrucciones de HANDOFF.md > "Cómo terminar la
tarea pendiente":
  - Opción A: exponer Usuarios completo (requiere que un admin corra el REVOKE
    del DENY en SSMS; yo NO puedo ejecutar SQL — escalar a Sergio/TI).
  - Opción B (recomendada): excluir Usuarios agregándola a EXCLUDE_TABLES en
    gen-config.py, regenerar y redesplegar.
  ⚠️ Antes de elegir A, confirma con quien corresponda: expone hashes de
  credenciales y mcp.ie no tiene auth. Si nadie puede correr el REVOKE ahora,
  ve por Opción B para dejar el sistema estable.

Reglas operativas (de la skill ie-linux-server):
- Deploy = push a master → ssh ie-linux "cd /proyectos/ie-MCP-servers && git
  pull && cd deploy && docker compose up -d --build <servicio>".
- El proxy es el contenedor ie-proxy (/proyectos/ie-proxy/), NO nginx del host.
  Reload: docker exec ie-proxy nginx -t && docker exec ie-proxy nginx -s reload.
- claude-agent NO tiene sudo; sí tiene docker y ACL en /proyectos. Nunca uses
  sqlcmd: el SQL lo corre un admin desde SSMS.
- No edites dab-config.json a mano: edita gen-config.py y regenera.

Al terminar: verifica con los comandos de HANDOFF.md > "Verificación final" y
confírmame el estado.
```
