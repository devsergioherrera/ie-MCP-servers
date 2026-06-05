# Changelog

Registro de cambios funcionales en el alcance de los MCP servers de este repo (entidades expuestas, BDs nuevas, integraciones, etc).

El formato sigue **un evento por línea**, con fecha ISO 8601 al inicio.
Para cambios de código/infra menores, ver `git log`.

## Changes

- 2026-06-05 — Nuevo MCP server `ie-mssql-explorer` (contenedor `mcp-mssql-explorer`, puerto 5004, ruta `/explorer/mcp`). Server custom en Python (FastMCP + pyodbc, imagen con `msodbcsql18`) que extiende lo que DAB no alcanza: expone `describe_entity_schema` (columnas, tipos, nullability, PK, identity y conteo aproximado vía `sys.dm_db_partition_stats`) y `get_distinct_values` (dominio de valores con frecuencia, cap 500). Motivo: DAB es imagen cerrada y `describe_entities` devuelve `fields=[]`. Read-only con las mismas creds `mcp_reader`; whitelist de entidades reutilizada del `dab-config.json` del MCP de datos (sin duplicar fuente de verdad). Columnas validadas contra `INFORMATION_SCHEMA` antes de usarse como identificador; timeouts y caps duros. Estructura lista para sumar cross-database, búsqueda y lógica de negocio. `mcp-docs-api` ahora detecta servers custom (`server-meta.json`) también bajo `data-mcp-servers/`, así aparece en la UI `/info`.

- 2026-05-25 — Landing UI estatica en Astro (mcp-ui) para `http://mcp.ie/` y `/docs`. MCP de docs queda en `/docs/mcp` via Nginx; nuevo contenedor `mcp-ui` (puerto 5010).

- 2026-05-15 — Fix escritura IE_MONITOR: movidas las 5 entidades de IE_MONITOR a contenedor DAB dedicado `mcp-mssql-monitor` (puerto 5005, ruta /monitor/mcp). Causa raiz: bug en DAB 1.7.93 donde las operaciones de escritura (create/update/delete) fallan con KeyNotFoundException sobre entidades definidas en data-source-files secundarios. Como data source primario del nuevo contenedor, el bug no aplica. `mcp-mssql` queda solo con SIE + EMPAQUE(PR) y DML tools deshabilitadas (read-only estricto). Nginx actualizado con location /monitor/. .mcp.json actualizado con servidor `ie-mssql-monitor`.

- 2026-05-15 — Habilitada escritura (INSERT/UPDATE/DELETE) sobre las 5 entidades de `IE_MONITOR`. Nuevo LOGIN `mcp_writer` con `db_datareader + db_datawriter` sobre IE_MONITOR; `MSSQL_MONITOR_CONN` ahora usa este user. Tools `create_record`, `update_record`, `delete_record` habilitadas globalmente en DAB runtime. SIE y EMPAQUE(PR) siguen read-only por `permissions=["read"]` a nivel entidad (defense-in-depth: la tool aparece en tools/list pero DAB devuelve 403 al intentar escribir).
- 2026-05-15 — Expuestas 5 tablas de la BD `IE_MONITOR` del servidor `192.168.50.86` via MCP: `BIOMETRICOS`, `BIOMETRICOS_DESTINATARIOS`, `MONITOREO_ALERTAS_LOG`, `MONITOREO_CONFIG`, `MONITOREO_ESTADO_CHECKER`. Acceso read-only con `mcp_reader` + `db_datareader`. Descripciones marcadas como TODO — pendiente refinar con el usuario.
- 2026-05-15 — Skill `expose-data-entity` creada en `.claude/skills/` (proyecto). Documenta el flujo para agregar BDs/tablas/vistas a los MCP de mssql/mysql/postgres con generacion de GRANT scripts, actualizacion de .env, docker-compose y CHANGELOG. Refuerza que las passwords reales NO van en los .sql commiteados (solo en `.env`).
- 2026-05-15 — Trazabilidad activada: logs JSON estructurados en mcp-ie-docs (`logs/ie-docs.jsonl`) y Nginx access log JSON en `/var/log/nginx/mcp.ie.access.log`. Sin auth (LAN-trust).
- 2026-05-15 — Expuestas 16 tablas del sistema logístico del servidor `192.168.50.252` (BDs `SIE` + `EMPAQUE(PR)`). Read-only con `mcp_reader`. Relationships intra-BD declaradas.
- 2026-05-14 — Inicialización del proyecto: 4 contenedores MCP (1 implementado: `mcp-mssql` + `mcp-ie-docs`), DAB 1.7.93, MCP de docs en Python. Nginx en linux.ie.
