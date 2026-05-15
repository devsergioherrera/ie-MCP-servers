---
name: expose-data-entity
description: Expose one or more SQL Server / MySQL / PostgreSQL database objects (tables, views, or full databases) through the existing DAB-based MCP servers in this project. Use this when the user wants to add a new database, schema, table or view to be reachable via the MCP. Handles connection wiring, generates GRANT scripts, updates dab-config files, .env, docker-compose, and appends a dated entry to CHANGELOG.md.
---

# expose-data-entity

## When to invoke this skill

The user wants to make a new database object (table, view, or whole DB) available through the MCP servers in this repository. Typical triggers:

- "Expose the table X from server Y"
- "Add the IE_MONITOR database to the MCP"
- "I want the agent to read view Z"
- "Connect MCP to a new server"

## Scope by engine

| Engine | Target container | Config file | Notes |
|---|---|---|---|
| SQL Server | `mcp-mssql-<dbname>` | `data-mcp-servers/mssql-<dbname>/dab-config.json` | **Un contenedor por base de datos.** NUNCA usar `data-source-files` — las operaciones de escritura fallan con `KeyNotFoundException` sobre entidades en data sources secundarios (bug DAB 1.7.93, probablemente no corregido en 2.x). Ejemplos existentes: `mcp-mssql-main` (SIE+EMPAQUE), `mcp-mssql-monitor` (IE_MONITOR). |
| MySQL | `mcp-mysql-<purpose>` | `data-mcp-servers/mysql-<purpose>/dab-config.json` | Un contenedor por BD. Hoy solo GLPI (`mcp-mysql-glpi`). |
| PostgreSQL | `mcp-pg-<purpose>` | `data-mcp-servers/postgres-<purpose>/dab-config.json` | Un contenedor por BD. Hoy solo OpenProject (`mcp-pg-op`). |

## Required inputs (ask the user upfront)

1. **Engine**: mssql / mysql / postgres.
2. **Server / host**: IP or FQDN (ex: `192.168.50.86`).
3. **Database name** (ex: `IE_MONITOR`).
4. **Scope**: one of
   - single table or view (ask for exact `schema.object`)
   - list of tables/views (ask the user to paste a list)
   - **whole database** (you will need the user to run a discovery query and paste the result)
5. **User SQL** to use (default: `mcp_reader`). If the server is **new** (no prior connection from this project), the LOGIN must be created — ask for a password for that new login. If the password the user chooses overlaps with credentials already committed elsewhere, **suggest a fresh one**.
6. **Reuse existing connection?**: if the server already appears in `.env` (e.g. another DB on the same host), the connection string can be reused with `Database=<newDb>` swapped. Detect this and avoid asking twice.

## Connection-string format reference

| Engine | Format |
|---|---|
| mssql | `Server=<host>,1433;Database=<db>;User ID=<user>;Password=<pwd>;Encrypt=true;TrustServerCertificate=true` |
| mysql | `Server=<host>;Database=<db>;UserID=<user>;Password=<pwd>;SslMode=Preferred` |
| postgres | `Host=<host>;Port=5432;Database=<db>;Username=<user>;Password=<pwd>` |

Each new server/DB gets its own env var with a descriptive name. Convention: `<ENGINE>_<DBNAME>_CONN`. Example: `MSSQL_IE_MONITOR_CONN`, `MYSQL_GLPI_CONN`.

## Steps

### 1. Crear o identificar la carpeta del contenedor

- SQL Server: cada base de datos tiene su propia carpeta `data-mcp-servers/mssql-<dbname-lower>/` con su propio `Dockerfile` y `dab-config.json`. **NUNCA** agregar la BD a un contenedor existente vía `data-source-files` — ese patrón rompe las operaciones de escritura (bug confirmado en DAB 1.7.93).
  - Nueva BD → crear `data-mcp-servers/mssql-<dbname-lower>/` desde cero.
  - BD ya existente → editar `data-mcp-servers/mssql-<dbname-lower>/dab-config.json` directamente.
- MySQL / PostgreSQL: edit `data-mcp-servers/<engine>-<purpose>/dab-config.json` directly. Si la BD es en un servidor diferente al ya existente, crear nueva carpeta de contenedor también.

### 2. Crear o actualizar el dab-config.json del contenedor

Skeleton para un contenedor nuevo `data-mcp-servers/mssql-<dbname-lower>/dab-config.json` (mssql):

```json
{
  "$schema": "https://github.com/Azure/data-api-builder/releases/latest/download/dab.draft.schema.json",
  "data-source": {
    "database-type": "mssql",
    "connection-string": "@env('MSSQL_<DBNAME>_CONN')",
    "options": { "set-session-context": false }
  },
  "entities": {
    "<EntityAlias>": {
      "source": { "type": "table", "object": "dbo.<TableName>" },
      "permissions": [{ "role": "anonymous", "actions": ["read"] }],
      "description": "<one-line semantic description — explain WHAT this object represents in the business domain, not just its columns>"
    }
  }
}
```

For **views**, add `"key-fields": ["<pk_column>"]`. DAB cannot infer a PK for views. If the user does not know the PK, ask them to run `SELECT TOP 0 * FROM <view>` to inspect columns and pick a candidate.

### 3. Discovery queries (when scope = whole database)

Ask the user to run these (with the new user already granted SELECT) and paste the results:

**MSSQL — list of tables/views**:
```sql
USE <DBNAME>;
SELECT s.name AS schema_name, o.name AS object_name, o.type_desc
FROM sys.objects o
JOIN sys.schemas s ON o.schema_id = s.schema_id
WHERE o.type IN ('U','V')      -- U=table, V=view
ORDER BY s.name, o.name;
```

**MSSQL — descriptions if available** (optional but recommended):
```sql
USE <DBNAME>;
SELECT s.name AS schema_name, o.name AS object_name,
       CAST(ep.value AS NVARCHAR(MAX)) AS description
FROM sys.objects o
JOIN sys.schemas s ON o.schema_id = s.schema_id
LEFT JOIN sys.extended_properties ep
  ON ep.major_id = o.object_id AND ep.minor_id = 0 AND ep.name = 'MS_Description'
WHERE o.type IN ('U','V');
```

**MySQL — list**:
```sql
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_schema = '<DBNAME>'
ORDER BY table_name;
```

**PostgreSQL — list**:
```sql
SELECT table_schema, table_name, table_type
FROM information_schema.tables
WHERE table_catalog = '<DBNAME>'
  AND table_schema NOT IN ('pg_catalog','information_schema');
```

For each row in the result, generate one entity block in the config file. Entity aliases should be PascalCase derived from the object name (`CAMION_X_DIA` → `CamionXDia`). If the object is a view, the user must provide the PK column for `key-fields`. If unknown, leave a `TODO: key-fields` comment near the entity and ask for it before deploying.

### 4. Generate the GRANT script

Path: `data-mcp-servers/<engine-folder>/grants-<dbname-lower>.sql`. Always idempotent.

**MSSQL** template:
```sql
-- Generated by skill expose-data-entity on <YYYY-MM-DD>
-- Target server: <HOST>
-- Target database: <DBNAME>

-- 1. LOGIN (server level) — only if this is the first time mcp_reader is used on this server
USE master;
GO
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'mcp_reader')
    CREATE LOGIN mcp_reader WITH PASSWORD = '<PASSWORD>';
GO

-- 2. USER (database level)
USE <DBNAME>;
GO
IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'mcp_reader')
    CREATE USER mcp_reader FOR LOGIN mcp_reader;
GO

-- 3. Permissions — pick ONE of the two blocks:

-- 3a. Whitelist explicit (recommended for principle of least privilege):
GRANT SELECT ON dbo.<Object1> TO mcp_reader;
GRANT SELECT ON dbo.<Object2> TO mcp_reader;
-- ...

-- 3b. Read-everything (use when scope = whole database):
EXEC sp_addrolemember 'db_datareader', 'mcp_reader';
GO

-- 4. Verification
SELECT
    DB_NAME() AS db, pr.name AS user_name,
    o.name AS object_name, p.permission_name, p.state_desc
FROM sys.database_permissions p
JOIN sys.database_principals pr ON p.grantee_principal_id = pr.principal_id
JOIN sys.objects o ON p.major_id = o.object_id
WHERE pr.name = 'mcp_reader';
```

**MySQL** template:
```sql
-- Generated by skill expose-data-entity on <YYYY-MM-DD>
CREATE USER IF NOT EXISTS 'mcp_reader'@'%' IDENTIFIED BY '<PASSWORD>';
GRANT SELECT ON <DBNAME>.* TO 'mcp_reader'@'%';
FLUSH PRIVILEGES;
```

**PostgreSQL** template:
```sql
-- Generated by skill expose-data-entity on <YYYY-MM-DD>
DO $$
BEGIN
   IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcp_reader') THEN
       CREATE USER mcp_reader WITH PASSWORD '<PASSWORD>';
   END IF;
END$$;
GRANT CONNECT ON DATABASE <DBNAME> TO mcp_reader;
\connect <DBNAME>
GRANT USAGE ON SCHEMA public TO mcp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mcp_reader;
```

### 5. Update infra files

- **`deploy/.env`** and **`deploy/.env.example`**: add a new env var with the connection string. `.env` gets the real value, `.env.example` gets the placeholder template.
- **`deploy/docker-compose.yml`**: add a **new service block** for the new container. Asignar el siguiente puerto disponible en loopback (5001=mssql-main, 5002=mysql-glpi planned, 5003=pg-op planned, 5004=ie-docs, 5005=mssql-monitor). Incluir el env var en el `environment:` block.
- **`data-mcp-servers/mssql-<dbname-lower>/Dockerfile`** (CRÍTICO para SQL Server): el Dockerfile solo necesita copiar un archivo — `COPY dab-config.json /App/dab-config.json`. Un contenedor = un dab-config.json. Sin `data-source-files`, sin múltiples COPY.
- **`deploy/nginx/mcp.ie.conf`**: agregar un bloque `location /<dbname>/` que apunte al nuevo puerto del contenedor.
- **`.mcp.json`** (proyecto) y **`~/.claude.json`** (global): agregar el nuevo servidor con la URL `http://mcp.ie/<dbname>/mcp`.

### 6. Append to CHANGELOG.md

Append a dated entry under `## Changes` with format:

```
- YYYY-MM-DD — Exposed <scope> from <engine>://<host>/<DBNAME> via MCP. <count> entities added. Driven by user request.
```

Date format: ISO 8601 (`YYYY-MM-DD`), use **today's date in the user's timezone** (do not invent — read from system context or ask).

### 7. Commit and report

- Commit message: `feat(<engine>): expose <scope> from <DBNAME>` (or `fix:` / `refactor:` as appropriate).
- Include the Co-Authored-By line as configured in the repo.
- Do NOT push automatically. Ask the user before pushing.
- After committing, hand the user the **manual steps** that remain:
  1. The path to the generated GRANT script and a clear "run this in your SQL client as sa/admin".
  2. Confirm the `.env` value matches the password they actually used.
  3. The deploy command: `ssh ie-linux "cd /proyectos/ie-MCP-servers && git pull && cd deploy && docker compose up -d --build mcp-<engine>"`.

## Boundaries

### Always
- Use parameterized connection strings via `@env('...')` — never embed credentials in JSON.
- Generate idempotent SQL scripts (use `IF NOT EXISTS` guards).
- Append to CHANGELOG.md with the **real date**.
- Write descriptions in the entity blocks that explain business meaning, not just column lists.
- For views: require `key-fields` to be set (or ask the user before deploying).

### Read-only vs read-write
- The runtime `dml-tools` toggles are **global to the container** — once you enable `create-record`/`update-record`/`delete-record`, they appear in `tools/list` for every entity. You cannot restrict tool visibility per data-source-file.
- The **per-entity defense** is the `permissions.actions` array. Entities with `["read"]` reject writes with 403 at runtime even if the tool exists. Use this as the primary guardrail.
- Different SQL users per scope: if a BD allows writes, the connection string for that data-source-file must use a SQL user with INSERT/UPDATE/DELETE privileges. Read-only BDs continue using a strictly read-only SQL user. Naming convention: `mcp_reader` for read-only, `mcp_writer` for read+write. One LOGIN per role per server. Use distinct passwords per role (do not reuse the reader password for the writer).
- When enabling writes, prefer `db_datareader + db_datawriter` if scope = whole DB, or explicit `GRANT INSERT, UPDATE, DELETE ON dbo.<Table>` if whitelisting.

### Ask first
- Before granting `db_datareader` (broad). Confirm the user really wants full-DB read access vs whitelist.
- Before reusing an existing password across servers — recommend a fresh one.
- Before pushing the commit.

### Never
- Commit `.env` to the repo (it is gitignored — verify before commit).
- **Embed the real password in the generated `grants-*.sql` script** — the script is committed to the repo. Use a placeholder like `<REEMPLAZAR_POR_PASSWORD_REAL>` and explicitly tell the user to substitute it locally before running. The real password only lives in `deploy/.env` (gitignored).
- **Usar `data-source-files`** para agregar una BD a un contenedor existente. Bug confirmado en DAB 1.7.93: `create_record`/`update_record`/`delete_record` fallan con `KeyNotFoundException` sobre entidades de data sources secundarios. Siempre crear un contenedor nuevo.
- Suggest INSERT/UPDATE/DELETE grants — this project is strictly read-only via MCP (excepto BDs explícitamente habilitadas para escritura como IE_MONITOR).
- Auto-execute the SQL grants — those run on the SQL Server, not from this agent.
- Skip the CHANGELOG entry.
