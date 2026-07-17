"""Generador del dab-config.json para la BD GLPI (MySQL, intempserv8).

DAB no expone "todas las tablas" con un wildcard: cada entidad debe declararse.
Este script introspecta INFORMATION_SCHEMA y emite un dab-config.json read-only
con una entidad por tabla del schema, generado a partir de todo lo que el
usuario `mcp_reader` pueda ver (GRANT SELECT ON glpi-ie.* alcanza para todo).
Re-ejecutar cuando cambie el esquema (plugins de GLPI agregan/quitan tablas).

Uso (con MYSQL_GLPI_CONN en el entorno, mismo formato ADO-like que usa DAB):
    MYSQL_GLPI_CONN="Server=intempserv8;Database=glpi-ie;UserID=mcp_reader;Password=..." \
        python gen-config.py > dab-config.json

O sin instalar nada local, con un contenedor Python descartable:
    docker run --rm --network mcp_net \
        -e MYSQL_GLPI_CONN="Server=intempserv8;Database=glpi-ie;UserID=mcp_reader;Password=..." \
        -v "$(pwd):/app" -w /app python:3.12-slim \
        bash -c "pip install -q pymysql && python gen-config.py > dab-config.json"
"""

import json
import os
import re
import sys

import pymysql

CONN_ENV = "MYSQL_GLPI_CONN"

# Tablas que nunca se exponen via MCP (case-insensitive):
#  - glpi_config / glpi_crontasklogs / glpi_logs: contienen secretos operativos
#    (tokens, claves de proxy/LDAP/smtp) o son ruido de auditoria interna, no
#    datos de negocio (tickets/activos/usuarios).
EXCLUDE_TABLES = {"glpi_config", "glpi_crontasklogs", "glpi_logs"}


def parse_conn(ado: str) -> dict:
    parts = {}
    for seg in ado.split(";"):
        if "=" in seg:
            k, v = seg.split("=", 1)
            parts[k.strip().lower()] = v.strip()
    return parts


def pascal(name: str) -> str:
    """glpi_tickets -> GlpiTickets ; glpi_ticket_users -> GlpiTicketUsers."""
    parts = re.split(r"[^A-Za-z0-9]+", name)
    out = "".join(p[:1].upper() + p[1:].lower() for p in parts if p)
    if out and out[0].isdigit():
        out = "T" + out
    return out or name


def main() -> None:
    ado = os.environ.get(CONN_ENV)
    if not ado:
        sys.exit(f"ERROR: falta la variable de entorno {CONN_ENV}")

    p = parse_conn(ado)
    db = p.get("database")
    cn = pymysql.connect(
        host=p.get("server"),
        port=int(p.get("port", 3306)),
        db=db,
        user=p.get("userid") or p.get("uid") or p.get("user"),
        password=p.get("password") or p.get("pwd"),
        connect_timeout=10,
    )
    cur = cn.cursor()

    cur.execute(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME",
        (db,),
    )
    tables = [r[0] for r in cur.fetchall()]

    entities: dict[str, dict] = {}
    used_aliases: set[str] = set()

    for table_name in tables:
        if table_name.lower() in EXCLUDE_TABLES:
            sys.stderr.write(f"Excluida (denylist): {table_name}\n")
            continue

        alias = pascal(table_name)
        base = alias
        i = 2
        while alias in used_aliases:
            alias = f"{base}{i}"
            i += 1
        used_aliases.add(alias)

        entities[alias] = {
            "source": {"type": "table", "object": table_name},
            "permissions": [{"role": "anonymous", "actions": ["read"]}],
            "description": (
                f"BD GLPI (intempserv8), tabla {table_name}. SOLO LECTURA. "
                "Generado automaticamente por gen-config.py — sin descripcion de negocio refinada."
            ),
        }

    config = {
        "$schema": "https://github.com/Azure/data-api-builder/releases/latest/download/dab.draft.schema.json",
        "data-source": {
            "database-type": "mysql",
            "connection-string": f"@env('{CONN_ENV}')",
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
                    "MCP de SOLO LECTURA sobre MySQL de GLPI (sistema de tickets/activos de "
                    "Integral de Empaques, intempserv8). Expone todas las tablas del schema "
                    f"glpi-ie salvo config/logs internos. {len(entities)} entidades. "
                    "Generado automaticamente por gen-config.py."
                ),
            },
        },
        "entities": entities,
    }

    print(json.dumps(config, indent=2, ensure_ascii=False))
    sys.stderr.write(f"Generadas {len(entities)} entidades.\n")


if __name__ == "__main__":
    main()
