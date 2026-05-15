# TASKS — IE-MCP-Servers

Pendientes ordenados por prioridad. Marcar `[x]` al cerrar.

---

## Seguridad

- [ ] **#1 Auth (futuro: IdP central)** — Hoy todo es LAN sin autenticacion. La trazabilidad existente (remote_addr + user_agent del access log de Nginx + request_id) sirve para saber "desde donde". Cuando se quiera saber "quien" con identidad federada, NO improvisar bearer estatico — montar un IdP central (probablemente Keycloak federado contra el AD de IE) en un repo separado `ie-auth/` y reemplazar este bloque por validacion JWT via `auth_request` en Nginx y `runtime.host.authentication` en DAB. Diseno deliberadamente diferido para no atar este proyecto a un mecanismo que va a cambiar.
- [ ] **#2 Ejecutar GRANTs en SQL Server** (manual como `sa`) — script consolidado e idempotente en `data-mcp-servers/mssql/grants.sql`. Cubre las 16 entidades del sistema logistico (5 SIE + 11 EMPAQUE(PR)). El script crea el USER si falta y otorga SELECT a las tablas/vistas listadas. Incluye query de verificacion al final.
- [ ] **#3 TLS en Nginx** — habilitar HTTPS para `mcp.ie`. Decidir: cert interno IE o Let's Encrypt (requiere DNS publico). Por ahora solo escucha en `:80`.
- [x] **#4 Validar PK real de `vw_EtiquetasBI`** — corregido a `Etiqueta` (NCHAR). Pero ver #15.
- [ ] **#15 PK de `vw_EtiquetasBI` no es estrictamente unica** — los registros con `Desde='ETIQUETA_LINER'` pueden tener `Etiqueta` como cadena de espacios (NCHAR sin trimear y sin codigo). Eso rompe la garantia de unicidad que asume DAB con `key-fields: ["Etiqueta"]`: si hay >1 LINER sin codigo, la paginacion por cursor puede colisionar. Opciones:
  - (a) Filtrar la vista para excluir filas con `Etiqueta` vacia/null.
  - (b) Cambiar a PK compuesta `["Etiqueta", "Desde"]` (requiere que el par sea unico — validar).
  - (c) Generar un `Id` sinteticco en la vista (`ROW_NUMBER()` no sirve por estabilidad — mejor un hash determinista o un identity en una tabla materializada).
  Decidir con el usuario antes de modificar la vista en produccion.

## Funcional — MCP de BDs (segunda iteracion)

- [ ] **#5 MCP MySQL GLPI** — poblar `data-mcp-servers/mysql-glpi/dab-config.json` con entidades:
  - `glpi_tickets`, `glpi_users`, `glpi_groups`, `glpi_entities`, `glpi_ticketcategories`, `glpi_ticket_users`.
  - Anadir descripciones por entidad/campo.
  - Descomentar bloque `mcp-mysql-glpi` en `deploy/docker-compose.yml`.
  - Anadir `location /glpi/` en `deploy/nginx/mcp.ie.conf`.
- [ ] **#6 MCP PostgreSQL OpenProject** — analogo a #5 con tablas:
  - `work_packages`, `projects`, `users`, `types`, `statuses`, `time_entries`, `members`.
- [ ] **#7 Confirmar version final de DAB** — hoy se usa `1.7-latest`. Cuando salga `2.0` GA (hoy en RC), evaluar upgrade.

## Funcional — MCP de Docs

- [ ] **#8 Ampliar `/docs/`** con markdowns de otros sistemas:
  - `ALISTAMIENTO_IE.md` (flujo de cargue masivo + picking)
  - `DESPACHOS_IE.md` (DIA_DESPACHO, TEMP_DETALLE_DIA_X_DESPACHO)
  - `KARDEX_IE.md`
  - `PIPELINE_BI_IE.md` (vistas, GoogleSheets, Looker)
  - `SIRA_IE.md` (proyecto C++/TFLite extrusion)
- [ ] **#9 Healthcheck en `mcp-ie-docs`** — anadir endpoint `/health` en `server.py` o un mini handler HTTP separado.

## Observabilidad

- [x] **Trazabilidad basica** — `mcp-ie-docs` emite logs JSON estructurados a `logs/ie-docs.jsonl` (rotacion automatica 10MB x5). Nginx emite access log JSON a `/var/log/nginx/mcp.ie.access.log` con remote_addr, user_agent, path, status, request_time, request_id. DAB persiste via Docker logging driver json-file (10MB x5).
- [ ] **#10 OpenTelemetry de DAB** — conectar exporter a colector local (Jaeger/Tempo en linux.ie) si se decide trazar. Util cuando haya >2 backends y se necesite correlacion end-to-end.
- [ ] **#16 Log shipping a un sink central** — opcional, si en el futuro se quiere consultar logs desde un lugar (no entrar a linux.ie). Opciones: Loki + Grafana, Elastic, Seq.
- [x] **#11 Healthchecks en docker-compose** — `mcp-ie-docs` tiene healthcheck via socket TCP. `mcp-mssql` sin healthcheck (imagen DAB chiseled sin shell); confiamos en `restart: unless-stopped`.

## Operacion

- [ ] **#12 Script de deploy** — `deploy/deploy.sh` que haga `git pull && docker compose pull && docker compose up -d --build && copia nginx conf && nginx -s reload`.
- [ ] **#13 Backup de markdowns** — los `.md.bak` que crea `write_doc` se acumulan. Definir politica de retencion (cron de limpieza > 30 dias).
- [ ] **#14 Hook OpenProject** — validar que `setup.bat` (Windows) tenga equivalente `setup.sh` en linux.ie si se va a hacer `git commit` en el servidor.
