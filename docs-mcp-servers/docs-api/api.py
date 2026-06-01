"""API de metadata de MCP servers para el sitio web mcp.ie/docs.

Lee los dab-config.json de /dab-configs (volumen ro montado desde data-mcp-servers/)
y devuelve SOLO campos seguros: nunca connection-string, source.object ni opciones internas.

Endpoints:
  GET /servers  -> lista de servers con entidades y permisos
  GET /health   -> {"ok": true}
"""

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

DAB_CONFIGS_DIR = Path(os.environ.get("DAB_CONFIGS_DIR", "/dab-configs"))

app = FastAPI(title="IE MCP Docs API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Helpers de extraccion segura
# ---------------------------------------------------------------------------

def _safe_entities(entities: dict[str, Any]) -> list[dict]:
    """Extrae campos publicos de cada entidad. Nunca source.object ni relationship.fields."""
    result = []
    for name, entity in entities.items():
        source = entity.get("source", {})
        permissions = entity.get("permissions", [])
        roles = [p.get("role", "anonymous") for p in permissions]

        result.append({
            "name": name,
            "description": entity.get("description", ""),
            "type": source.get("type", "table"),  # "table" o "view"
            "permissions": roles,
        })
    return result


def _safe_tools(dml_tools: dict[str, bool]) -> dict[str, bool]:
    """Mapea los flags dml-tools a nombres de tools MCP equivalentes."""
    return {
        "describe_entities": dml_tools.get("describe-entities", True),
        "read_records": dml_tools.get("read-records", True),
        "aggregate_records": dml_tools.get("aggregate-records", False),
        "create_record": dml_tools.get("create-record", False),
        "update_record": dml_tools.get("update-record", False),
        "delete_record": dml_tools.get("delete-record", False),
        "execute_entity": dml_tools.get("execute-entity", False),
    }


def _load_config(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _parse_server(server_id: str, config_dir: Path) -> dict | None:
    """Parsea un dab-config.json y devuelve un dict seguro para la API."""
    main_path = config_dir / "dab-config.json"
    if not main_path.exists():
        return None

    config = _load_config(main_path)
    if config is None:
        return None

    data_source = config.get("data-source", {})
    runtime = config.get("runtime", {})
    mcp = runtime.get("mcp", {})
    dml_tools = mcp.get("dml-tools", {})

    # Determinar si es solo lectura: create/update/delete todos en false
    readonly = not any([
        dml_tools.get("create-record", False),
        dml_tools.get("update-record", False),
        dml_tools.get("delete-record", False),
    ])

    # Entidades del config principal
    all_entities: dict[str, Any] = dict(config.get("entities", {}))

    # Merge de configs secundarios (data-source-files)
    for secondary_file in config.get("data-source-files", []):
        secondary_path = config_dir / secondary_file
        secondary = _load_config(secondary_path)
        if secondary:
            all_entities.update(secondary.get("entities", {}))

    # Derivar label legible desde el id
    label_parts = server_id.replace("-", " ").replace("_", " ").title()

    return {
        "id": server_id,
        "label": label_parts,
        "database_type": data_source.get("database-type", "mssql"),
        "description": mcp.get("description", ""),
        "readonly": readonly,
        "tools": _safe_tools(dml_tools),
        "entities": _safe_entities(all_entities),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/servers")
def list_servers() -> dict:
    """Devuelve metadata publica de todos los MCP servers en /dab-configs."""
    servers: list[dict] = []

    if not DAB_CONFIGS_DIR.exists():
        return {"servers": [], "schema_version": "1", "error": "DAB_CONFIGS_DIR not found"}

    for config_dir in sorted(DAB_CONFIGS_DIR.iterdir()):
        if not config_dir.is_dir():
            continue
        server = _parse_server(config_dir.name, config_dir)
        if server is not None:
            servers.append(server)

    return {"servers": servers, "schema_version": "1"}
