# Changelog

Registro de cambios funcionales en el alcance de los MCP servers de este repo (entidades expuestas, BDs nuevas, integraciones, etc).

El formato sigue **un evento por línea**, con fecha ISO 8601 al inicio.
Para cambios de código/infra menores, ver `git log`.

## Changes

- 2026-05-15 — Expuestas 5 tablas de la BD `IE_MONITOR` del servidor `192.168.50.86` via MCP: `BIOMETRICOS`, `BIOMETRICOS_DESTINATARIOS`, `MONITOREO_ALERTAS_LOG`, `MONITOREO_CONFIG`, `MONITOREO_ESTADO_CHECKER`. Acceso read-only con `mcp_reader` + `db_datareader`. Descripciones marcadas como TODO — pendiente refinar con el usuario.
- 2026-05-15 — Skill `expose-data-entity` creada en `.claude/skills/` (proyecto). Documenta el flujo para agregar BDs/tablas/vistas a los MCP de mssql/mysql/postgres con generacion de GRANT scripts, actualizacion de .env, docker-compose y CHANGELOG. Refuerza que las passwords reales NO van en los .sql commiteados (solo en `.env`).
- 2026-05-15 — Trazabilidad activada: logs JSON estructurados en mcp-ie-docs (`logs/ie-docs.jsonl`) y Nginx access log JSON en `/var/log/nginx/mcp.ie.access.log`. Sin auth (LAN-trust).
- 2026-05-15 — Expuestas 16 tablas del sistema logístico del servidor `192.168.50.252` (BDs `SIE` + `EMPAQUE(PR)`). Read-only con `mcp_reader`. Relationships intra-BD declaradas.
- 2026-05-14 — Inicialización del proyecto: 4 contenedores MCP (1 implementado: `mcp-mssql` + `mcp-ie-docs`), DAB 1.7.93, MCP de docs en Python. Nginx en linux.ie.
