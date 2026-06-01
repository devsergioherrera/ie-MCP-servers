<div align="center">
  <img src="./mcp-ui/public/assets/logo.png" alt="Integral de Empaques" width="300" />
</div>

# IE-MCP-Servers

> Monorepo de MCP Servers para Integral de Empaques: acceso seguro y de solo lectura a las BDs corporativas (SQL Server, MySQL GLPI, PostgreSQL OpenProject) + un MCP de documentacion viva (markdowns editables).

---

## Stack Tecnologico

| Capa                   | Tecnologia                                                         |
| ---------------------- | ------------------------------------------------------------------ |
| **MCP de BDs**         | Microsoft Data API Builder (DAB) v1.7+ — `data-api-builder:1.7.93` |
| **MCP de docs**        | Python 3.12 + `mcp` SDK oficial (FastMCP, streamable-http)         |
| **Orquestacion**       | Docker Compose                                                     |
| **Reverse proxy**      | Nginx **nativo en linux.ie** (no contenerizado)                    |
| **Host de despliegue** | linux.ie — Ubuntu 24.04                                            |

---

## UI estatica (Astro)

Landing page para `http://mcp.ie` con estetica minimalista tipo Apple, animacion de entropia en canvas (p5.js) y espacio listo para integrar agentes de IA.

**Colores corporativos**:

| Variable             | Color     |
| -------------------- | --------- |
| `--color-dark-blue`  | `#011480` |
| `--color-light-blue` | `#239bd8` |
| `--color-green`      | `#029f4c` |
| `--color-gray`       | `#c0c0c2` |

**Rutas**:

- UI: `http://mcp.ie/` y `http://mcp.ie/docs`
- MCP docs: `http://mcp.ie/docs/mcp`

---

## Responsabilidades por servicio

| Servicio | Para quién | Qué sirve |
| -------- | ---------- | --------- |
| `mcp-mssql-*` | Agentes IA | Tools para administrar las bases de datos |
| `mcp-ie-docs` | Agentes IA | Documentación interna de negocio (los `.md`) |
| `mcp-docs-api` | El sitio web `/docs` | Metadata de los MCP servers desde los configs |
| `mcp-ui` | Desarrolladores humanos | La interfaz visual en `http://mcp.ie` |

---

## Que expone

| MCP Server       | Motor / Origen                 | Ruta publica (Nginx)            | Estado       |
| ---------------- | ------------------------------ | ------------------------------- | ------------ |
| `mcp-mssql`      | SQL Server (SIE + EMPAQUE(PR)) | `http://mcp.ie/mssql/mcp`       | Implementado |
| `mcp-ie-docs`    | Filesystem (`/docs/*.md`)      | `http://mcp.ie/docs/mcp`        | Implementado |
| `mcp-mysql-glpi` | MySQL GLPI                     | `http://mcp.ie/glpi/mcp`        | Scaffolding  |
| `mcp-pg-op`      | PostgreSQL OpenProject         | `http://mcp.ie/openproject/mcp` | Scaffolding  |

**Primera iteracion (MSSQL)** — entidades expuestas:

- `CamionXDia` → `SIE.dbo.CAMION_X_DIA` (programacion de despachos)
- `veb` → `[EMPAQUE(PR)].dbo.vw_EtiquetasBI` (vista BI de etiquetas)

---

## Modelo de seguridad

- **Solo lectura** en los 3 MCP de BDs, endurecido en 3 capas:
  1. Usuario `mcp_reader` en la BD con permisos solo de `SELECT` sobre objetos listados.
  2. DAB con `create/update/delete/execute` desactivados via `runtime.mcp.dml-tools`.
  3. Permissions por entidad solo con `read` (rol `anonymous`).
- **REST y GraphQL desactivados** en DAB — solo expone el endpoint MCP.
- **Whitelist explicita** de entidades — nunca se expone el esquema completo.
- Puertos de contenedores solo en `127.0.0.1` — la LAN solo accede via Nginx.
- Connection strings en `.env` (gitignored), nunca en codigo.

**Pendiente**: autenticacion en Nginx (hoy es solo LAN-trust). Ver `TASKS.md` #1.

---

## Requisitos

- Docker y Docker Compose en linux.ie
- Nginx instalado en linux.ie (ya esta)
- Usuario `mcp_reader` creado en cada motor de BD (ver abajo)
- SQL Server accesible desde linux.ie (puerto 1433)

### Crear usuarios `mcp_reader` (manual, una vez por BD)

**SQL Server**:

```sql
CREATE LOGIN mcp_reader WITH PASSWORD = '<PASSWORD>';

USE SIE;
CREATE USER mcp_reader FOR LOGIN mcp_reader;
GRANT SELECT ON dbo.CAMION_X_DIA TO mcp_reader;

USE [EMPAQUE(PR)];
CREATE USER mcp_reader FOR LOGIN mcp_reader;
GRANT SELECT ON dbo.vw_EtiquetasBI TO mcp_reader;
```

**MySQL** (cuando se implemente):

```sql
CREATE USER 'mcp_reader'@'%' IDENTIFIED BY '<PASSWORD>';
GRANT SELECT ON glpi.* TO 'mcp_reader'@'%';
FLUSH PRIVILEGES;
```

**PostgreSQL** (cuando se implemente):

```sql
CREATE USER mcp_reader WITH PASSWORD '<PASSWORD>';
GRANT CONNECT ON DATABASE openproject TO mcp_reader;
GRANT USAGE ON SCHEMA public TO mcp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_reader;
```

---

## Instalacion y Ejecucion

### 1. Clonar y configurar hooks

```bash
git clone <repo-url> ie-MCP-servers
cd ie-MCP-servers
# Windows
setup.bat
# Linux
git config core.hooksPath .githooks
```

### 2. Configurar variables de entorno

```bash
cd deploy
cp .env.example .env
# Editar .env con la connection string real de SQL Server
```

### 3. Build y levantar

```bash
docker compose build mcp-mssql mcp-ie-docs mcp-ui
docker compose up -d mcp-mssql mcp-ie-docs mcp-ui
docker compose ps
```

### 4. Configurar Nginx en linux.ie (primera vez)

```bash
sudo cp deploy/nginx/mcp.ie.conf /etc/nginx/conf.d/mcp.ie.conf
sudo nginx -t
sudo nginx -s reload
```

Anadir `mcp.ie` al DNS interno (o `/etc/hosts` de los clientes) apuntando a la IP de `linux.ie`.

### 5. Probar

```bash
# Smoke test con MCP Inspector
npx @modelcontextprotocol/inspector http://mcp.ie/mssql/mcp
npx @modelcontextprotocol/inspector http://mcp.ie/docs/mcp
```

### 6. Configurar cliente MCP (Claude Desktop / Claude Code / etc.)

```json
{
  "mcpServers": {
    "ie-mssql": { "url": "http://mcp.ie/mssql/mcp" },
    "ie-docs": { "url": "http://mcp.ie/docs/mcp" }
  }
}
```

---

## Estructura del Proyecto

```
ie-MCP-servers/
├── mcp-ui/                       # UI estatica (Astro + p5.js)
├── data-mcp-servers/             # MCP que tocan BDs (todos con DAB)
│   ├── mssql/                    # SQL Server produccion (SIE + EMPAQUE)
│   ├── mysql-glpi/               # Scaffolding GLPI
│   └── postgres-openproject/     # Scaffolding OpenProject
├── docs-mcp-servers/
│   └── ie-docs/                  # Python MCP, sirve y edita /docs
├── docs/                         # Markdowns fuente (volumen rw del MCP)
├── deploy/
│   ├── docker-compose.yml
│   ├── .env.example              # plantilla sin secretos
│   └── nginx/
│       └── mcp.ie.conf           # copiar a /etc/nginx/conf.d/
├── TASKS.md                      # pendientes (auth, MySQL/PG, etc.)
├── AGENTS.md                     # contexto completo para agentes de IA
├── CLAUDE.md / GEMINI.md / .cursorrules / .github/copilot-instructions.md
└── README.md
```

---

## Desarrollo UI (Astro)

```bash
cd mcp-ui
npm install
npm run dev
```

**Build/preview**:

```bash
npm run build
npm run preview
```

**Typecheck**:

```bash
npm run typecheck
```

**Docker**:

```bash
cd mcp-ui
docker build -t ie-mcp-ui .
docker run --rm -p 8080:80 ie-mcp-ui
```

---

## Configuracion OpenProject (hook post-commit)

Editar `.openproject.conf`:

```
PROJECT_ID=<id>
TYPE_ID=10
```

IDs de proyectos disponibles:

| ID  | Proyecto                       |
| --- | ------------------------------ |
| 16  | DESPACHO EN LINEA              |
| 15  | ETIQUETADO PRODUCTO EN PROCESO |
| 14  | GESTION HUMANA                 |
| 13  | GENERACION IPT                 |
| 12  | DESBLOQUEO DE ORDENES          |
| 11  | KARDEX                         |
| 10  | Procesos Disciplinarios        |
| 9   | ALISTAMIENTO                   |
| 8   | Daily Sistemas                 |

Configurar API key:

```powershell
[Environment]::SetEnvironmentVariable("OPENPROJECT_API_KEY","<KEY>","User")
```

---

## Desarrollo asistido por IA

Toda la configuracion para agentes esta en **`AGENTS.md`**. Los demas archivos (`CLAUDE.md`, `GEMINI.md`, `.cursorrules`, `.github/copilot-instructions.md`) apuntan ahi.

---

## Licencia

Software propietario de **Integral de Empaques S.A.S.** — Uso interno exclusivo.
