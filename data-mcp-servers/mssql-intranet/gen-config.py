"""Generador del dab-config.json para la BD INTRANET (192.168.50.86).

DAB no expone "todas las tablas" con un wildcard: cada entidad debe declararse.
Este script introspecta INFORMATION_SCHEMA y emite un dab-config.json read-only
con una entidad por tabla/vista del schema dbo. Re-ejecutar cuando cambie el
esquema (se agregan/quitan tablas).

Uso (con MSSQL_INTRANET_CONN en el entorno, mismo formato ADO.NET que DAB):
    MSSQL_INTRANET_CONN="Server=...;Database=INTRANET;..." python gen-config.py > dab-config.json

O dentro del contenedor explorer (que ya tiene pyodbc + driver ODBC):
    docker exec -e MSSQL_INTRANET_CONN="..." mcp-mssql-explorer \
        python /tmp/gen-config.py > data-mcp-servers/mssql-intranet/dab-config.json
"""

import json
import os
import re
import sys

import pyodbc

ODBC_DRIVER = os.environ.get("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
CONN_ENV = "MSSQL_INTRANET_CONN"

# Tablas que NUNCA se exponen via MCP (comparacion case-insensitive por nombre):
#  - __EFMigrationsHistory / sysdiagrams: basura de sistema (EF Core / SSMS).
EXCLUDE_TABLES = {"__efmigrationshistory", "sysdiagrams"}

# Columnas sensibles a OCULTAR por tabla (case-insensitive en la key de tabla).
# La tabla SI se expone (read-only) pero estas columnas nunca salen por el MCP,
# usando field-level exclude de DAB. Critico: credenciales (Ley 1273).
#  - Usuarios: ContrasenaHash + Salt permitirian cracking offline.
SENSITIVE_FIELDS = {"usuarios": ["ContrasenaHash", "Salt"]}


def ado_to_odbc(ado: str) -> str:
    parts = {}
    for seg in ado.split(";"):
        if "=" in seg:
            k, v = seg.split("=", 1)
            parts[k.strip().lower()] = v.strip()

    def yn(v, d="yes"):
        if v is None:
            return d
        return "yes" if str(v).lower() in ("true", "yes", "1") else "no"

    return (
        f"DRIVER={{{ODBC_DRIVER}}};SERVER={parts.get('server')};"
        f"DATABASE={{{parts.get('database')}}};"
        f"UID={parts.get('user id') or parts.get('uid')};"
        f"PWD={parts.get('password') or parts.get('pwd')};"
        f"Encrypt={yn(parts.get('encrypt'))};"
        f"TrustServerCertificate={yn(parts.get('trustservercertificate'))};"
    )


def pascal(name: str) -> str:
    """USUARIOS -> Usuarios ; TBL_DOC_X -> TblDocX."""
    parts = re.split(r"[^A-Za-z0-9]+", name)
    out = "".join(p[:1].upper() + p[1:].lower() for p in parts if p)
    if out and out[0].isdigit():
        out = "T" + out
    return out or name


def main() -> None:
    ado = os.environ.get(CONN_ENV)
    if not ado:
        sys.exit(f"ERROR: falta la variable de entorno {CONN_ENV}")

    cn = pyodbc.connect(ado_to_odbc(ado), timeout=10)
    cur = cn.cursor()

    # Tablas y vistas del schema dbo
    cur.execute(
        "SELECT TABLE_NAME, TABLE_TYPE FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = 'dbo' ORDER BY TABLE_NAME"
    )
    objects = cur.fetchall()

    # Descripciones MS_Description (si existen)
    descriptions: dict[str, str] = {}
    try:
        cur.execute(
            "SELECT o.name, CAST(ep.value AS NVARCHAR(MAX)) "
            "FROM sys.objects o "
            "JOIN sys.extended_properties ep "
            "  ON ep.major_id = o.object_id AND ep.minor_id = 0 "
            " AND ep.name = 'MS_Description' "
            "WHERE o.type IN ('U','V')"
        )
        descriptions = {r[0]: r[1] for r in cur.fetchall() if r[1]}
    except Exception:
        pass

    entities: dict[str, dict] = {}
    used_aliases: set[str] = set()

    for table_name, table_type in objects:
        if table_name.lower() in EXCLUDE_TABLES:
            sys.stderr.write(f"Excluida (denylist): {table_name}\n")
            continue
        alias = pascal(table_name)
        base = alias
        i = 2
        while alias in used_aliases:           # evitar colisiones de alias
            alias = f"{base}{i}"
            i += 1
        used_aliases.add(alias)

        is_view = table_type.upper() == "VIEW"
        source = {"type": "view" if is_view else "table", "object": f"dbo.{table_name}"}

        if is_view:
            # DAB no infiere PK de vistas: usar la primera columna como key-field.
            cur.execute(
                "SELECT TOP 1 COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME=? ORDER BY ORDINAL_POSITION",
                table_name,
            )
            first = cur.fetchone()
            if first:
                source["key-fields"] = [first[0]]

        # Permiso de lectura: si la tabla tiene columnas sensibles, usar la
        # forma detallada con field-level exclude; si no, el "read" simple.
        sensitive = SENSITIVE_FIELDS.get(table_name.lower())
        if sensitive:
            read_action = {"action": "read", "fields": {"exclude": sensitive}}
        else:
            read_action = "read"

        entities[alias] = {
            "source": source,
            "permissions": [{"role": "anonymous", "actions": [read_action]}],
            "description": descriptions.get(
                table_name,
                f"BD INTRANET (192.168.50.86), {table_type.lower()} dbo.{table_name}. "
                "SOLO LECTURA. TODO: refinar descripcion de negocio.",
            ),
        }

    config = {
        "$schema": "https://github.com/Azure/data-api-builder/releases/latest/download/dab.draft.schema.json",
        "data-source": {
            "database-type": "mssql",
            "connection-string": f"@env('{CONN_ENV}')",
            "options": {"set-session-context": False},
        },
        "runtime": {
            "host": {"mode": "production", "cors": {"origins": [], "allow-credentials": False}},
            "rest": {"enabled": False},
            "graphql": {"enabled": False},
            "mcp": {
                "enabled": True,
                "path": "/mcp",
                "dml-tools": {
                    "describe-entities": True,
                    "read-records": True,
                    "aggregate-records": True,
                    "create-record": False,
                    "update-record": False,
                    "delete-record": False,
                    "execute-entity": False,
                },
                "description": (
                    "MCP de SOLO LECTURA sobre la BD INTRANET de Integral de Empaques "
                    "(192.168.50.86). Expone todas las tablas y vistas del schema dbo. "
                    f"{len(entities)} entidades. Generado automaticamente por gen-config.py."
                ),
            },
        },
        "entities": entities,
    }

    print(json.dumps(config, indent=2, ensure_ascii=False))
    sys.stderr.write(f"Generadas {len(entities)} entidades.\n")


if __name__ == "__main__":
    main()
