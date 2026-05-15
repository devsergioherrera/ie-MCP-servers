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
| SQL Server | `mcp-mssql` | `data-mcp-servers/mssql/dab-config.<dbname>.json` referenced from `dab-config.json` via `data-source-files` | One config file per database. The principal `dab-config.json` is for BD `SIE`. |
| MySQL | `mcp-mysql-glpi` | `data-mcp-servers/mysql-glpi/dab-config.json` | Today only GLPI. Add another container if a new MySQL server appears. |
| PostgreSQL | `mcp-pg-op` | `data-mcp-servers/postgres-openproject/dab-config.json` | Today only OpenProject. Add another container if a new PG server appears. |

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

### 1. Identify the target config file

- SQL Server: if the database is **new** for this project, create `data-mcp-servers/mssql/dab-config.<dbname-lower>.json` and add the filename to `data-source-files[]` in the principal `dab-config.json`. If the database is **already there**, edit the existing file.
- MySQL / PostgreSQL: edit `data-mcp-servers/<engine>-<purpose>/dab-config.json` directly.

### 2. Create the secondary config (mssql multi-db only) or update the existing one

Skeleton for a brand-new `dab-config.<dbname-lower>.json` (mssql):

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
- **`deploy/docker-compose.yml`**: add the env var to the corresponding service's `environment:` block. The container won't see it otherwise.
- **`data-mcp-servers/<engine>/Dockerfile`** (CRITICAL when creating a new dab-config.*.json): add a `COPY dab-config.<dbname-lower>.json /App/dab-config.<dbname-lower>.json` line. Without this, DAB cannot find the file at runtime and the new entities silently don't load. This is the most common pitfall. Editing only the config file and the `data-source-files` array is NOT enough — the image must be rebuilt with `--build` and the file must be present in the build context.

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

### Ask first
- Before granting `db_datareader` (broad). Confirm the user really wants full-DB read access vs whitelist.
- Before reusing an existing password across servers — recommend a fresh one.
- Before pushing the commit.

### Never
- Commit `.env` to the repo (it is gitignored — verify before commit).
- **Embed the real password in the generated `grants-*.sql` script** — the script is committed to the repo. Use a placeholder like `<REEMPLAZAR_POR_PASSWORD_REAL>` and explicitly tell the user to substitute it locally before running. The real password only lives in `deploy/.env` (gitignored).
- Suggest INSERT/UPDATE/DELETE grants — this project is strictly read-only via MCP.
- Auto-execute the SQL grants — those run on the SQL Server, not from this agent.
- Skip the CHANGELOG entry.
