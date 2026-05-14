# AGENTS.md

## Project overview

- **Nombre**: IE-MCP-Servers
- **Tipo**: Monorepo de MCP Servers (BDs y docs) desplegado con Docker Compose
- **Empresa**: Integral de Empaques S.A.S.
- **Stack**:
  - **MCP de BDs**: Microsoft Data API Builder (DAB) v1.7+ — `mcr.microsoft.com/azure-databases/data-api-builder:1.7-latest`. Cubre SQL Server, MySQL y PostgreSQL con la misma tecnologia.
  - **MCP de docs**: Python 3.12 + `mcp` SDK oficial (FastMCP) sobre transporte streamable-http.
  - **Despliegue**: linux.ie (Ubuntu 24.04) con Docker Compose. Nginx **instalado nativo en el host** (no contenerizado), siguiendo el patron `conf.d/<servicio>.ie.conf`.

## Commands

### Desarrollo local

```powershell
# Levantar la primera iteracion (MCP MSSQL + MCP IE Docs)
cd deploy
cp .env.example .env             # completar MSSQL_CONN con creds reales
docker compose build mcp-mssql mcp-ie-docs
docker compose up -d mcp-mssql mcp-ie-docs
docker compose ps
docker compose logs -f mcp-mssql
```

### Smoke test

```powershell
# Inspector MCP — descubrir tools del MCP MSSQL
npx @modelcontextprotocol/inspector http://127.0.0.1:5001/mcp

# Inspector MCP — MCP de docs
npx @modelcontextprotocol/inspector http://127.0.0.1:5004/mcp
```

### Despliegue en linux.ie

```bash
# (En el servidor) tras git pull en /proyectos/ie-MCP-servers
cd deploy
docker compose up -d --build
# Copiar Nginx conf como root (primera vez o tras cambios)
sudo cp nginx/mcp.ie.conf /etc/nginx/conf.d/mcp.ie.conf
sudo nginx -t && sudo nginx -s reload
```

## Project structure

```
ie-MCP-servers/
|-- data-mcp-servers/             # MCP que tocan BDs (todos con DAB)
|   |-- mssql/                    # SQL Server produccion (SIE + EMPAQUE(PR))
|   |-- mysql-glpi/               # GLPI (scaffolding sin entidades)
|   `-- postgres-openproject/     # OpenProject (scaffolding sin entidades)
|-- docs-mcp-servers/
|   `-- ie-docs/                  # Python MCP — sirve y edita /docs
|-- docs/                         # Markdowns fuente del MCP de docs
|-- deploy/
|   |-- docker-compose.yml
|   |-- .env.example
|   `-- nginx/mcp.ie.conf         # Plantilla — copiar a /etc/nginx/conf.d/
|-- TASKS.md                      # Pendientes (auth, MySQL/PG, etc.)
`-- AGENTS.md / CLAUDE.md / GEMINI.md / .cursorrules
```

## Decisiones clave

- **DAB para los 3 motores**: una sola tecnologia, mismo formato de config, mismo modelo de RBAC. Sin NL2SQL (queries deterministas), sin DDL (no toca esquema).
- **Solo lectura** en los 3 MCP de BDs, endurecido en 3 capas:
  1. **Motor**: usuario `mcp_reader` con solo `SELECT` sobre vistas/tablas listadas.
  2. **Runtime DAB**: `dml-tools` con `create_record`/`update_record`/`delete_record`/`execute_entity` en `false` — ni siquiera aparecen en `tools/list`.
  3. **Entidad**: `permissions` solo con `read` y rol `anonymous`.
- **REST y GraphQL desactivados** en DAB — solo expone MCP.
- **Whitelist explicita** de entidades — nunca se expone el esquema completo.
- **Nginx en el host, no contenerizado** — sigue patron existente en linux.ie.
- **Puertos solo en `127.0.0.1`** — los contenedores no son alcanzables desde la LAN sin pasar por Nginx.
- **MCP de docs separado** del MCP de datos (responsabilidades distintas: documentacion org vs. datos vivos).
- **Sin RAG/embeddings** en el MCP de docs — acceso directo al filesystem por `list/read/search/write`.
- **MCP de docs en modo rw** — permite que los agentes editen markdowns (con path traversal guard y backups `.md.bak`).

## Code style

- **DAB**: descripciones detalladas en `description` por entidad y campo — son el unico contexto semantico que reciben los agentes via `describe_entities`. Tablas en SQL Server siempre con three-part naming `[BD].dbo.<obj>` por cross-database.
- **Python MCP**: tipado fuerte, sin frameworks pesados, sin shell-out. Path traversal guard obligatorio en cualquier tool que tome un nombre de archivo.
- Variables sensibles solo en `.env` (gitignored). Nunca commitear connection strings.

## Git workflow

- Commits: prefijo convencional (`feat:`, `fix:`, `docs:`, `refactor:`)
- Hook `post-commit` crea tarea automatica en OpenProject
- Configurar con `setup.bat` y editar `.openproject.conf`

## Boundaries

### Siempre

- Whitelist explicita de entidades en `dab-config.json` — no exponer schemas enteros.
- Anadir `description` a cada entidad y campo nuevo.
- Probar con MCP Inspector antes de pushear cambios al config.
- Usar `[BD(con espacios o parentesis)].dbo.<obj>` con corchetes para BDs con caracteres especiales.

### Preguntar primero

- Habilitar cualquier tool de escritura (`create_record`, `update_record`, `delete_record`, `execute_entity`).
- Cambiar la conexion a un usuario con mas privilegios que `mcp_reader`.
- Exponer entidades con datos sensibles (nominas, costos, info personal de empleados).

### Nunca

- Commitear `.env`, connection strings, ni passwords.
- Tocar tablas del ERP Siesa (linked server `[192.168.50.86].REPLICA`) — solo lectura desde sistemas propios.
- Modificar `KARDEX_BODEGA` desde un MCP.
- Habilitar `rest` o `graphql` en `dab-config.json` (solo MCP).
- Exponer puertos de los contenedores fuera de `127.0.0.1` (debe pasar por Nginx).
