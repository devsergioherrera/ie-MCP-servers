"""MCP Server para EXPLORAR el SQL Server de IE (read-only) — capa de
extension que DAB no alcanza.

DAB (mcp-mssql-main) cubre la lectura generica (read_records, filtros,
paginacion) pero es una imagen cerrada: no se le pueden agregar tools
propias. Este server permite al agente EXPLORAR y ENTENDER la BD antes de
consultarla: introspeccion de esquema, valores posibles, y (a futuro)
cross-database, busquedas y logica de negocio que DAB no puede expresar.

Tools actuales (la estructura esta lista para sumar mas):
  - describe_entity_schema(entity): columnas, tipos, nullability, PK,
    identity y conteo aproximado de filas (DAB devuelve fields=[]).
  - get_distinct_values(entity, column): catalogo de valores con frecuencia.

Seguridad:
  - Whitelist: la lista de entidades se carga del mismo dab-config.json del
    MCP de datos. Una entidad fuera de la whitelist se rechaza.
  - Las columnas se validan contra INFORMATION_SCHEMA antes de usarse como
    identificador; nunca se concatena input crudo como valor.
  - Conexiones por env var (mismas creds read-only mcp_reader que DAB).
  - Timeout de query duro y caps de resultado.
"""

import json
import logging
import os
import re
import time
from functools import wraps
from pathlib import Path
from typing import Any

import pyodbc
from mcp.server.fastmcp import FastMCP

CONFIG_DIR = Path(os.environ.get("DAB_CONFIG_DIR", "/dab-configs"))
ODBC_DRIVER = os.environ.get("ODBC_DRIVER", "ODBC Driver 18 for SQL Server")
QUERY_TIMEOUT = int(os.environ.get("QUERY_TIMEOUT", "10"))   # segundos
CONNECT_TIMEOUT = int(os.environ.get("CONNECT_TIMEOUT", "5"))
DISTINCT_HARD_CAP = 500

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("mssql-explorer")


# ---------------------------------------------------------------------------
# Carga de whitelist desde los dab-config.json del MCP de datos
# ---------------------------------------------------------------------------
def _env_name(conn_ref: str | None) -> str | None:
    """Extrae MSSQL_SIE_CONN de "@env('MSSQL_SIE_CONN')"."""
    m = re.match(r"@env\('([^']+)'\)", conn_ref or "")
    return m.group(1) if m else None


def load_entities() -> dict[str, dict]:
    """Parsea dab-config.json (+ data-source-files) y mapea entidad -> tabla/BD."""
    mapping: dict[str, dict] = {}
    main_path = CONFIG_DIR / "dab-config.json"
    main = json.loads(main_path.read_text(encoding="utf-8"))
    files = ["dab-config.json"] + main.get("data-source-files", [])

    for fname in files:
        cfg = json.loads((CONFIG_DIR / fname).read_text(encoding="utf-8"))
        conn_env = _env_name(cfg.get("data-source", {}).get("connection-string"))
        for name, ent in cfg.get("entities", {}).items():
            src = ent.get("source", {})
            obj = src.get("object", "")
            schema, _, table = obj.partition(".")
            if not table:                       # sin schema explicito -> dbo
                schema, table = "dbo", obj
            mapping[name] = {
                "schema": schema,
                "table": table,
                "type": src.get("type", "table"),
                "key_fields": src.get("key-fields", []),
                "conn_env": conn_env,
            }
    logger.info("Whitelist cargada: %d entidades", len(mapping))
    return mapping


ENTITIES = load_entities()


# ---------------------------------------------------------------------------
# Conexion: convierte connection-string ADO.NET (la de DAB) a ODBC (pyodbc)
# ---------------------------------------------------------------------------
def _ado_to_odbc(ado: str) -> str:
    parts: dict[str, str] = {}
    for seg in ado.split(";"):
        if "=" in seg:
            k, v = seg.split("=", 1)
            parts[k.strip().lower()] = v.strip()

    def yn(v: str | None, default: str = "yes") -> str:
        if v is None:
            return default
        return "yes" if str(v).lower() in ("true", "yes", "1") else "no"

    server = parts.get("server")
    database = parts.get("database")
    uid = parts.get("user id") or parts.get("uid")
    pwd = parts.get("password") or parts.get("pwd")
    return (
        f"DRIVER={{{ODBC_DRIVER}}};SERVER={server};DATABASE={{{database}}};"
        f"UID={uid};PWD={pwd};"
        f"Encrypt={yn(parts.get('encrypt'))};"
        f"TrustServerCertificate={yn(parts.get('trustservercertificate'))};"
    )


def _connect(conn_env: str | None) -> pyodbc.Connection:
    if not conn_env:
        raise ValueError("La entidad no tiene connection-string asociada en el config")
    ado = os.environ.get(conn_env)
    if not ado:
        raise ValueError(f"Variable de entorno {conn_env} no esta definida")
    cn = pyodbc.connect(_ado_to_odbc(ado), timeout=CONNECT_TIMEOUT)
    cn.timeout = QUERY_TIMEOUT
    return cn


def _coerce(v: Any) -> Any:
    """Hace JSON-serializable un valor (datetime, Decimal, bytes...)."""
    if isinstance(v, (int, float, str, bool)) or v is None:
        return v
    return str(v)


def _require_entity(entity: str) -> dict:
    meta = ENTITIES.get(entity)
    if not meta:
        raise ValueError(
            f"Entidad '{entity}' no esta en la whitelist. "
            f"Disponibles: {', '.join(sorted(ENTITIES))}"
        )
    return meta


def _real_columns(cur: pyodbc.Cursor, schema: str, table: str) -> set[str]:
    cur.execute(
        "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?",
        schema, table,
    )
    return {r[0] for r in cur.fetchall()}


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------
mcp = FastMCP(
    "ie-mssql-explorer",
    instructions=(
        "Explora y entiende el SQL Server de IE (solo lectura), complementario "
        "al MCP de datos en /mssql/mcp. Usalo ANTES de consultar datos para "
        "conocer la estructura: describe_entity_schema da columnas, tipos, PK y "
        "conteo aproximado de una entidad; get_distinct_values revela los valores "
        "posibles de una columna (estados, tipos, areas). "
        "Cubre lo que DAB no puede (introspeccion de esquema; a futuro "
        "cross-database y logica de negocio). Mismas entidades del MCP de datos."
    ),
    host="0.0.0.0",
    port=8000,
    streamable_http_path="/mcp",
)


def traced(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            logger.info(
                "%s ok %dms %s",
                fn.__name__, int((time.perf_counter() - start) * 1000), kwargs,
            )
            return result
        except Exception as e:
            logger.error(
                "%s err %dms %s: %s",
                fn.__name__, int((time.perf_counter() - start) * 1000),
                kwargs, e,
            )
            raise
    return wrapper


@mcp.tool()
@traced
def describe_entity_schema(entity: str) -> dict:
    """Devuelve el esquema real de una entidad: columnas (nombre, tipo SQL,
    longitud, precision/escala, nullability), clave primaria, columnas identity
    y conteo aproximado de filas. Lee INFORMATION_SCHEMA — no expone datos."""
    meta = _require_entity(entity)
    schema, table = meta["schema"], meta["table"]
    full = f"{schema}.{table}"

    with _connect(meta["conn_env"]) as cn:
        cur = cn.cursor()

        cur.execute(
            "SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, "
            "NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE, ORDINAL_POSITION "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ? "
            "ORDER BY ORDINAL_POSITION",
            schema, table,
        )
        rows = cur.fetchall()
        if not rows:
            raise ValueError(f"No se encontraron columnas para {full} "
                             "(verifica permisos de mcp_reader o el nombre)")

        # Primary key (de constraint; fallback a key-fields del config p/ vistas)
        cur.execute(
            "SELECT kcu.COLUMN_NAME "
            "FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc "
            "JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu "
            "  ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME "
            " AND tc.TABLE_SCHEMA   = kcu.TABLE_SCHEMA "
            "WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' "
            "  AND tc.TABLE_SCHEMA = ? AND tc.TABLE_NAME = ?",
            schema, table,
        )
        pk = {r[0] for r in cur.fetchall()}
        if not pk and meta["key_fields"]:
            pk = set(meta["key_fields"])

        # Identity + conteo aproximado: solo aplica a tablas
        ident: set[str] = set()
        row_count: int | None = None
        if meta["type"] == "table":
            try:
                cur.execute(
                    "SELECT c.name FROM sys.columns c "
                    "WHERE c.object_id = OBJECT_ID(?) AND c.is_identity = 1",
                    full,
                )
                ident = {r[0] for r in cur.fetchall()}
                cur.execute(
                    "SELECT SUM(p.row_count) FROM sys.dm_db_partition_stats p "
                    "WHERE p.object_id = OBJECT_ID(?) AND p.index_id IN (0, 1)",
                    full,
                )
                got = cur.fetchone()
                row_count = int(got[0]) if got and got[0] is not None else None
            except Exception as e:           # vistas / permisos sys.*
                logger.warning("identity/rowcount no disponible para %s: %s", full, e)

        columns = [
            {
                "name": r[0],
                "sql_type": r[1],
                "max_length": r[2],
                "numeric_precision": r[3],
                "numeric_scale": r[4],
                "is_nullable": r[5] == "YES",
                "is_pk": r[0] in pk,
                "is_identity": r[0] in ident,
                "ordinal": r[6],
            }
            for r in rows
        ]

    return {
        "entity": entity,
        "object": full,
        "source_type": meta["type"],
        "row_count_approx": row_count,
        "primary_key": sorted(pk),
        "column_count": len(columns),
        "columns": columns,
    }


@mcp.tool()
@traced
def get_distinct_values(entity: str, column: str, max_values: int = 200) -> dict:
    """Lista los valores distintos de una columna con su frecuencia, ordenados
    de mayor a menor. Util para descubrir el dominio real de una columna
    (ej. estados, tipos, areas) antes de filtrar. Cap duro de 500 valores."""
    meta = _require_entity(entity)
    schema, table = meta["schema"], meta["table"]
    n = max(1, min(int(max_values), DISTINCT_HARD_CAP))

    with _connect(meta["conn_env"]) as cn:
        cur = cn.cursor()

        valid = _real_columns(cur, schema, table)
        if column not in valid:
            raise ValueError(
                f"Columna '{column}' no existe en {schema}.{table}. "
                f"Validas: {', '.join(sorted(valid))}"
            )

        # column/schema/table ya validados -> seguro como identificador.
        # Escape de ']' por robustez (SQL Server duplica el corchete de cierre).
        col_q = column.replace("]", "]]")
        sch_q = schema.replace("]", "]]")
        tbl_q = table.replace("]", "]]")
        query = (
            f"SELECT TOP (?) [{col_q}] AS val, COUNT(*) AS freq "
            f"FROM [{sch_q}].[{tbl_q}] WITH (NOLOCK) "
            f"GROUP BY [{col_q}] ORDER BY COUNT(*) DESC"
        )
        cur.execute(query, n)
        values = [{"value": _coerce(r[0]), "frequency": r[1]} for r in cur.fetchall()]

    return {
        "entity": entity,
        "column": column,
        "returned": len(values),
        "is_truncated": len(values) >= n,
        "values": values,
    }


if __name__ == "__main__":
    logger.info("ie-mssql-explorer starting (%d entidades)", len(ENTITIES))
    mcp.run(transport="streamable-http")
